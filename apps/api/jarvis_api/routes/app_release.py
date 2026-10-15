"""App-release-vagt — push i stedet for poll.

## Problemet den loeser (Bjoern 20/9-2026)

«hvorfor skal jeg vente en evighed paa appen fanger nye opdateringer?»

electron-updater poller GitHub hvert 15. minut (electron/main.ts), og mobilen
tjekker KUN ved opstart og naar den kommer i forgrunden (apps/mobile/src/App.tsx).
Det er ikke en fejl i vores kode: GitHub kan ikke skubbe til en klient. Der
findes ingen kanal fra et release ned i en app — klienten SKAL selv spoerge, og
saa er ventetiden indbygget i kilden.

## Hvad vi goer i stedet

Vi har vores egen server, og klienterne har allerede en aaben forbindelse til
den (`/ws`, se routes/live.py). Saa serveren opdager releasen selv og laegger et
event paa bussen; `/ws` sender det videre med det samme; klienten kalder sit eget
update-tjek i samme sekund.

    GitHub -> vagten her -> event_bus -> /ws -> klienten -> electron-updater

## To GitHub-kilder med hvert sit ansvar

``releases.atom`` er stadig den billige kilde til ``/latest``. Selve vagten
laeser derimod Actions API'et hvert tredje minut: Atom kan kun se releasen,
mens Actions er den eneste offentlige sandhed om prepare/build/publish og kan
derfor drive en rigtig fremdriftslinje. Tre minutter holder de to API-kald pr.
runde under GitHubs anonyme timekvote.

## Hvorfor fil-state

Vagten skal ogsaa kunne sige «der ER noget nyt» naar API-processen er genstartet
midt i et release-vindue. Ligger den sidst sete tag kun i hukommelsen, mister vi
netop det event der betyder mest.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["app-release"])
logger = logging.getLogger("uvicorn.error")

_REPO = "Nickless-cmd/jarvis-v2"
_ATOM_URL = f"https://github.com/{_REPO}/releases.atom"
_RUNS_URL = f"https://api.github.com/repos/{_REPO}/actions/workflows/desk-release.yml/runs"
_TAG_PRAEFIKS = "jarvis-desktop-v"
_NS = {"a": "http://www.w3.org/2005/Atom"}

# Actions API'et koster to kald pr. runde (run + jobs). Tre minutter giver
# luft under GitHubs anonyme kvote paa 60 kald/time.
_VAGT_INTERVAL_S = 180
_CACHE_TTL_S = 60
_HTTP_TIMEOUT_S = 15


# ── tilstand ────────────────────────────────────────────────────────────
# In-memory cache til /latest (undgaar et GitHub-kald pr. klient-forespoergsel).
_cache: dict[str, Any] = {"data": None, "hentet": 0.0}
_vagt_task: asyncio.Task[None] | None = None


def _state_fil() -> Path:
    home = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(home) / "app-release-state.json"


def _laes_sidste_tag() -> str | None:
    try:
        data = json.loads(_state_fil().read_text(encoding="utf-8"))
        tag = data.get("sidste_tag")
        return str(tag) if tag else None
    except (ValueError, OSError):  # ingen state-fil endnu, eller korrupt JSON → ingen baseline
        return None


def _skriv_sidste_tag(tag: str) -> None:
    _skriv_state({"sidste_tag": tag})


def _laes_state() -> dict[str, Any]:
    try:
        data = json.loads(_state_fil().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):  # manglende/korrupt best-effort state betyder tom baseline
        return {}


def _skriv_state(data: dict[str, Any]) -> None:
    try:
        fil = _state_fil()
        fil.parent.mkdir(parents=True, exist_ok=True)
        fil.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        # Best-effort: kan vi ikke persistere, virker vagten stadig i processen.
        logger.debug("app-release: kunne ikke skrive state-fil", exc_info=True)


# ── hentning ────────────────────────────────────────────────────────────


def _parse_atom(tekst: str) -> dict[str, Any] | None:
    """Nyeste desk-release ud af atom-feedet. None hvis feedet er tomt/ukendt."""
    try:
        root = ET.fromstring(tekst)
    except ET.ParseError:  # feedet svarede ikke med XML (proxy/HTML-fejlside) → intet at læse
        return None
    for entry in root.findall("a:entry", _NS):
        titel = (entry.findtext("a:title", "", _NS) or "").strip()
        if not titel.startswith(_TAG_PRAEFIKS):
            continue
        link_el = entry.find("a:link[@rel='alternate']", _NS)
        return {
            "tag": titel,
            "version": titel[len(_TAG_PRAEFIKS):],
            "url": (link_el.get("href") if link_el is not None else None),
            "published_at": entry.findtext("a:updated", "", _NS) or None,
        }
    return None


def hent_seneste() -> dict[str, Any] | None:
    """Sidste desk-release fra GitHub. Blokerende — kaldes i en traad."""
    try:
        import httpx

        r = httpx.get(
            _ATOM_URL,
            timeout=_HTTP_TIMEOUT_S,
            headers={"Accept": "application/atom+xml", "User-Agent": "jarvis-release-vagt"},
        )
        if r.status_code != 200:
            logger.debug("app-release: atom svarede %s", r.status_code)
            return None
        return _parse_atom(r.text)
    except Exception:  # noqa: BLE001
        logger.debug("app-release: atom-hentning fejlede", exc_info=True)
        return None


def _ci_status_fra_jobs(jobs: list[dict[str, Any]], *, workflow_url: str) -> dict[str, Any]:
    """Omsaet GitHub-jobbenes sandhed til den lille kontrakt Desk viser."""
    relevante = [j for j in jobs if str(j.get("name") or "").lower().startswith(
        ("prepare", "build-", "publish")
    )]
    fejl = {"failure", "cancelled", "timed_out", "action_required", "startup_failure"}
    afsluttede = sum(
        1 for j in relevante
        if str(j.get("status") or "") == "completed" and str(j.get("conclusion") or "") == "success"
    )
    progress = round(100 * afsluttede / max(len(relevante), 5))
    if any(str(j.get("conclusion") or "") in fejl for j in relevante):
        return {"phase": "failed", "progress": min(progress, 99),
                "label": "Build fejlede", "workflow_url": workflow_url}
    publish = next((j for j in relevante if str(j.get("name") or "").lower().startswith("publish")), None)
    if publish and publish.get("status") == "completed" and publish.get("conclusion") == "success":
        return {"phase": "ready", "progress": 100,
                "label": "Klar til installation", "workflow_url": workflow_url}

    platforme = []
    for navn, label in (("build-linux", "Linux"), ("build-mac", "macOS"), ("build-win", "Windows")):
        job = next((j for j in relevante if str(j.get("name") or "").lower().startswith(navn)), None)
        if not job or job.get("status") != "completed":
            platforme.append(label)
    if platforme:
        label = "Bygger " + (" og ".join(platforme) if len(platforme) <= 2
                              else ", ".join(platforme[:-1]) + " og " + platforme[-1])
    elif publish:
        label = "Publicerer opdateringen"
    else:
        label = "Forbereder build"
    return {"phase": "building", "progress": progress, "label": label,
            "workflow_url": workflow_url}


def hent_seneste_ci() -> dict[str, Any] | None:
    """Seneste tag-startede Desk-workflow inklusive jobfremdrift."""
    try:
        import httpx

        headers = {"Accept": "application/vnd.github+json", "User-Agent": "jarvis-release-vagt"}
        svar = httpx.get(_RUNS_URL, params={"event": "push", "per_page": 10},
                          timeout=_HTTP_TIMEOUT_S, headers=headers)
        if svar.status_code != 200:
            logger.debug("app-release: actions svarede %s", svar.status_code)
            return None
        runs = svar.json().get("workflow_runs") or []
        run = next((r for r in runs if str(r.get("head_branch") or "").startswith(_TAG_PRAEFIKS)), None)
        if not run:
            return None
        jobs_svar = httpx.get(str(run.get("jobs_url") or ""), timeout=_HTTP_TIMEOUT_S, headers=headers)
        if jobs_svar.status_code != 200:
            return None
        tag = str(run.get("head_branch"))
        return {
            "tag": tag,
            "version": tag[len(_TAG_PRAEFIKS):],
            "url": f"https://github.com/{_REPO}/releases/tag/{tag}",
            "published_at": run.get("created_at"),
            **_ci_status_fra_jobs(jobs_svar.json().get("jobs") or [],
                                  workflow_url=str(run.get("html_url") or "")),
        }
    except Exception:  # noqa: BLE001
        logger.debug("app-release: actions-hentning fejlede", exc_info=True)
        return None


def seneste_cached(*, tving: bool = False) -> dict[str, Any] | None:
    """Seneste release med kort cache, saa /latest ikke rammer GitHub pr. kald."""
    nu = time.monotonic()
    if not tving and _cache["data"] and (nu - float(_cache["hentet"])) < _CACHE_TTL_S:
        return _cache["data"]  # type: ignore[return-value]
    data = hent_seneste()
    if data:
        _cache["data"] = data
        _cache["hentet"] = nu
    return data


# ── rute ────────────────────────────────────────────────────────────────


@router.get("/api/app-release/latest")
async def app_release_latest() -> dict[str, Any]:
    """Nyeste desk-release. Auth haandteres af middlewaren, som for alle ruter."""
    data = await asyncio.to_thread(seneste_cached)
    if not data:
        return {"status": "unknown"}
    return {"status": "ok", **data}


# ── vagten ──────────────────────────────────────────────────────────────


def _release_titel(data: dict[str, Any]) -> str:
    version = data.get("version")
    if data.get("phase") == "ready":
        return f"Ny version {version} er klar"
    if data.get("phase") == "failed":
        return f"Build {version} fejlede"
    return f"Build {version} er undervejs"


def _opret_build(data: dict[str, Any]) -> bool:
    try:
        from core.services import notifikations_emittere
        notifikations_emittere.system(
            "release", _release_titel(data), str(data.get("label") or ""),
            ref=str(data.get("tag") or ""), data=data,
        )
        return True
    except Exception:
        logger.warning("release %s naaede ikke feeden", data.get("version"), exc_info=True)
        return False


def _opdater_build(data: dict[str, Any]) -> bool:
    try:
        from core.services import notifikationer
        opdateret = notifikationer.opdater(
            "release", str(data.get("tag") or ""),
            titel=_release_titel(data), tekst=str(data.get("label") or ""), data=data,
        )
        return opdateret or _opret_build(data)
    except Exception:
        logger.warning("release %s kunne ikke opdatere feeden", data.get("version"), exc_info=True)
        return False


def _udsend(data: dict[str, Any]) -> bool:
    """Laeg release-eventet paa bussen. /ws sender det videre til klienterne.

    Returnerer True naar eventet faktisk kom afsted. Kalderen maa IKKE rykke
    sin baseline videre paa et False — se kommentaren i _vagt_loop.
    """
    try:
        from core.eventbus.bus import event_bus

        event_bus.publish(
            "app.release.available",
            {
                "version": data.get("version"),
                "tag": data.get("tag"),
                "url": data.get("url"),
                "published_at": data.get("published_at"),
            },
        )
        logger.info("app-release: udsendte app.release.available version=%s", data.get("version"))
        return _opdater_build({**data, "phase": "ready", "progress": 100,
                               "label": "Klar til installation"})
    except Exception as e:  # noqa: BLE001
        # Tavs fejl her betyder at klienterne ALDRIG faar besked om en ny
        # release — og vagten skriver state alligevel, saa den ser ud til at
        # virke. Det var praecis hvad der skete 20/9: familien `app` var ikke
        # registreret, publish kastede, og debug-linjen blev aldrig laest.
        # Derfor warning — en fejl her er en fejl i push-vejen, ikke stoj.
        logger.warning("app-release: kunne ikke udsende event: %s", e, exc_info=True)
        return False


async def _vagt_loop() -> None:
    """Foerste gennemloeb saetter baseline. Derefter udsender vi KUN ved aendring.

    Uden baseline-delen ville hver API-genstart udsende et falsk «ny release»
    for den version der allerede koerer. Og uden fil-state ville vi overse det
    release der landede mens processen var nede.
    """
    global _cache
    state = _laes_state()
    sidste = state.get("sidste_tag")
    sidste_fingerprint = state.get("fingerprint")
    foerste = True
    while True:
        try:
            data = await asyncio.to_thread(hent_seneste_ci)
            if data:
                tag = str(data.get("tag") or "")
                # /latest maa aldrig se et build som stadig mangler assets.
                # CI og release-feed deler derfor kun cache, naar publish er
                # afsluttet og updater-manifestet faktisk findes.
                if data.get("phase") == "ready":
                    _cache["data"] = data
                    _cache["hentet"] = time.monotonic()
                if foerste:
                    foerste = False
                    if sidste is None:
                        # Et gammelt, faerdigt build er baseline. Et aktivt build
                        # er derimod netop det brugeren skal kunne foelge.
                        if data.get("phase") == "building" and _opret_build(data):
                            sidste = tag
                            sidste_fingerprint = f"{data.get('phase')}:{data.get('progress')}"
                            _skriv_state({"sidste_tag": tag, "fingerprint": sidste_fingerprint})
                        elif data.get("phase") != "building":
                            sidste = tag
                            sidste_fingerprint = f"{data.get('phase')}:{data.get('progress')}"
                            _skriv_state({"sidste_tag": tag, "fingerprint": sidste_fingerprint})
                    elif tag != sidste:
                        meld = _udsend(data) if data.get("phase") == "ready" else _opret_build(data)
                        if meld:
                            sidste = tag
                            sidste_fingerprint = f"{data.get('phase')}:{data.get('progress')}"
                            _skriv_state({"sidste_tag": tag, "fingerprint": sidste_fingerprint})
                    else:
                        fingerprint = f"{data.get('phase')}:{data.get('progress')}"
                        if sidste_fingerprint is None:
                            # Migration fra den gamle state-fil, der kun bar
                            # tagget. Et aktivt build skal have sin post; en
                            # allerede faerdig version er blot baseline.
                            if data.get("phase") != "building" or _opdater_build(data):
                                sidste_fingerprint = fingerprint
                                _skriv_state({"sidste_tag": tag, "fingerprint": fingerprint})
                        elif fingerprint != sidste_fingerprint:
                            meld = _udsend(data) if data.get("phase") == "ready" else _opdater_build(data)
                            if meld:
                                sidste_fingerprint = fingerprint
                                _skriv_state({"sidste_tag": tag, "fingerprint": fingerprint})
                elif tag != sidste:
                    # Baselines rykkes KUN naar eventet faktisk kom afsted.
                    # Ellers skriver vi «melding sendt» for et event ingen fik,
                    # og naeste genstart tror releasen allerede er meldt.
                    # Det var saadan 0.6.61 blev tabt 20/9: udsendelsen fejlede
                    # (familien `app` var ikke registreret), state gik videre til
                    # 0.6.61, og vagten kunne ikke raabe op igen.
                    meld = _udsend(data) if data.get("phase") == "ready" else _opret_build(data)
                    if meld:
                        sidste = tag
                        sidste_fingerprint = f"{data.get('phase')}:{data.get('progress')}"
                        _skriv_state({"sidste_tag": tag, "fingerprint": sidste_fingerprint})
                else:
                    fingerprint = f"{data.get('phase')}:{data.get('progress')}"
                    if fingerprint != sidste_fingerprint:
                        if data.get("phase") == "ready":
                            lykkedes = _udsend(data)
                        else:
                            lykkedes = _opdater_build(data)
                        if lykkedes:
                            sidste_fingerprint = fingerprint
                            _skriv_state({"sidste_tag": tag, "fingerprint": fingerprint})
        except Exception:  # noqa: BLE001
            logger.debug("app-release: vagt-gennemloeb fejlede", exc_info=True)
        await asyncio.sleep(_VAGT_INTERVAL_S)


def start_release_vagt() -> None:
    """Idempotent — gentagne kald (fx flere workers i samme proces) goer intet."""
    global _vagt_task
    if _vagt_task is not None and not _vagt_task.done():
        return
    try:
        _vagt_task = asyncio.get_running_loop().create_task(_vagt_loop())
        logger.info("app-release: vagt startet (interval=%ss)", _VAGT_INTERVAL_S)
    except RuntimeError:
        # Ingen loebende loop (fx import i en test) — vagten er valgfri.
        logger.debug("app-release: ingen event-loop, vagt ikke startet")


def stop_release_vagt() -> None:
    global _vagt_task
    if _vagt_task is not None and not _vagt_task.done():
        _vagt_task.cancel()
    _vagt_task = None
