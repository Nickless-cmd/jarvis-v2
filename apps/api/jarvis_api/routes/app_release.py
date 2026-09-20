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

## Hvorfor releases.atom og ikke GitHub's API

Atom-feedet kraever ingen token og har ingen rate limit. API'et giver 60 kald i
timen pr. IP — vagten alene ville spise hele kvoten, og et token ville skulle
ligge i klartekst paa serveren for at hente noget der er offentligt i forvejen.

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
_TAG_PRAEFIKS = "jarvis-desktop-v"
_NS = {"a": "http://www.w3.org/2005/Atom"}

# 120 s og ikke 60: atom-feedet har ingen kvote, men vi har heller ingen grund
# til at hamre GitHub. To minutter er rigeligt — klienten sidder ikke og venter
# paa vagten, den venter paa at slippe for at vente i 15.
_VAGT_INTERVAL_S = 120
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
    try:
        fil = _state_fil()
        fil.parent.mkdir(parents=True, exist_ok=True)
        fil.write_text(json.dumps({"sidste_tag": tag}, ensure_ascii=False), encoding="utf-8")
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


def _udsend(data: dict[str, Any]) -> None:
    """Laeg release-eventet paa bussen. /ws sender det videre til klienterne."""
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
    except Exception as e:  # noqa: BLE001
        # Tavs fejl her betyder at klienterne ALDRIG faar besked om en ny
        # release — og vagten skriver state alligevel, saa den ser ud til at
        # virke. Det var praecis hvad der skete 20/9: familien `app` var ikke
        # registreret, publish kastede, og debug-linjen blev aldrig laest.
        # Derfor warning — en fejl her er en fejl i push-vejen, ikke stoj.
        logger.warning("app-release: kunne ikke udsende event: %s", e, exc_info=True)


async def _vagt_loop() -> None:
    """Foerste gennemloeb saetter baseline. Derefter udsender vi KUN ved aendring.

    Uden baseline-delen ville hver API-genstart udsende et falsk «ny release»
    for den version der allerede koerer. Og uden fil-state ville vi overse det
    release der landede mens processen var nede.
    """
    global _cache
    sidste = _laes_sidste_tag()
    foerste = True
    while True:
        try:
            data = await asyncio.to_thread(hent_seneste)
            if data:
                tag = str(data.get("tag") or "")
                _cache["data"] = data
                _cache["hentet"] = time.monotonic()
                if foerste:
                    foerste = False
                    if sidste is None:
                        # Aldrig set foer: gem som baseline uden at raabe op.
                        sidste = tag
                        _skriv_sidste_tag(tag)
                    elif tag != sidste:
                        # Der kom et release mens vi var nede — det er praecis
                        # det event klienten har ventet paa.
                        _udsend(data)
                        sidste = tag
                        _skriv_sidste_tag(tag)
                elif tag != sidste:
                    _udsend(data)
                    sidste = tag
                    _skriv_sidste_tag(tag)
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
