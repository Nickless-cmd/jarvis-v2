"""CI-status — set, ikke gættet.

Hullet, målt 3/10-2026: `ci` var rødt på `main` i to døgn — over 30 kørsler i
træk — uden at nogen så det. Vagten (`tests/test_publish_scan.py`) fangede
fejlen med det samme; det var *fladen* der manglede. Beskyttelsen var en vane,
skrevet i MEMORY tre gange: «husk at tjekke CI efter push». Den fejlede.

Der fandtes ingen alarm. Intet i `core/`, `scripts/` eller `apps/` kaldte
GitHub Actions-API'et. Her lukkes hullet: hjerteslaget spørger selv, husker
hvilke kørsler det har set, og lægger kun det NYE røde i køen.

**Grundlinjen — hvorfor første kørsel tier.** Her er der historik, i modsætning
til baggrunds-shellene. Et rødt run fra i går er ikke nyt, og en vagtpost der
råber op om 30 gamle fejl ved første kørsel bliver slukket igen. Derfor huskes
tidsstemplet for hvornår vagtposten vågnede (`foerste_ved`), og kun kørsler
oprettet EFTER det kan give en besked. Konsekvensen er ærlig og skal siges
højt: vagtposten kan ikke melde hvad der skete før den fandtes — den fanger
det næste. Det er den kontrakt, ikke en tilfældighed.

**Hvorfor i de ubetingede daemoner.** Samme grund som `background_job_watch`:
`act_phase` dispatcher kun videre til `run_heartbeat_tick` når der ER
prioriteter. En alarm der kun kan komme når der i forvejen er travlt, er ikke
en alarm.

**Uden token, med vilje.** Repoet er offentligt og API'et svarer
uautentificeret. Loftet er 60 kald i timen; vi bruger 15. Et token ville
tilføje et nyt fejlled (udløb, manglende brugerkontekst i et bart hjerteslag)
for en grænse vi ikke er i nærheden af. Bliver det et problem, er det her
stedet at ændre.

**Rate-limit og 404 er blindhed, ikke sundhed.** Svarer API'et 403 med
`X-RateLimit-Remaining: 0`, eller 404, eller tier netværket — så VED vi ikke
om CI er rødt. Det må ikke blive «alt fint». Se `ApiUkendt`.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_REPO = "Nickless-cmd/jarvis-v2"
_API = f"https://api.github.com/repos/{_REPO}/actions/runs"

_STATE = "ci_watch_set"
_SIDSTE_TJEK = "ci_watch_sidste_tjek"
# Grundlinjen har sin EGEN fil. Foerste udgave delte `_SIDSTE_TJEK` med
# throttlen, og `_grundlinje()` satte dermed `ved` — saa foerste maaling blev
# sprunget over som «for tidligt». To begreber i én fil kan forstyrre
# hinanden; her er de skilt ad. (Fanget af testene, 3/10-2026.)
_GRUNDLINJE = "ci_watch_grundlinje"

# 60 kald i timen uautentificeret. 240 s = 15 i timen — rigeligt luft, og fint
# nok til at fange et rødt run et par minutter efter det er afsluttet.
_MIN_MELLEMRUM_S = 240.0

# Hvor længe et set run-id huskes. Vinduet er 10 runs; 30 dage er rigeligt til
# at et run ikke kan nå at falde ud af vinduet og dukke op igen som «nyt».
_HUSK_DAGE = 30

# Hvor mange kørsler vi kigger på pr. gang.
_VINDUE = 10

# Konklusioner der tæller som rødt. `cancelled` er med vilje IKKE med: et
# afbrudt run kan være et bevidst valg, og en alarm der råber op om det bliver
# ignoreret. `skipped`/`neutral` er heller ikke fejl.
_ROEDE = frozenset({"failure", "timed_out", "startup_failure", "action_required"})


def _nu() -> datetime:
    return datetime.now(UTC)


class ApiUkendt(RuntimeError):
    """Vi kunne ikke se CI.

    Det er ikke det samme som at CI er grøn — og forskellen er hele grunden til
    at klassen findes. En vagtpost der melder «alt fint» når den i
    virkeligheden er blind, er den fejlklasse `test_publish_scan` blev skrevet
    for at fange.
    """


def _rapporterede() -> dict[str, str]:
    """{run_id: iso-tidsstempel} for det vi allerede har set.

    Poster ældre end `_HUSK_DAGE` falder væk under læsningen — filen rydder
    sig selv uden et separat oprydningsjob.
    """
    from core.runtime import state_store

    raa = state_store.load_json(_STATE, {})
    if not isinstance(raa, dict):
        return {}
    graense = _nu() - timedelta(days=_HUSK_DAGE)
    ud: dict[str, str] = {}
    for noegle, vaerdi in raa.items():
        try:
            stempel = datetime.fromisoformat(str(vaerdi))
        except (ValueError, TypeError):  # ulaeseligt tidsstempel — posten kan ikke dateres
            continue
        if stempel >= graense:
            ud[str(noegle)] = str(vaerdi)
    return ud


def _husk(ids: list[str]) -> None:
    """Skriv id'erne som sete — atomisk, så api og runtime ikke overskriver
    hinandens lister."""
    if not ids:
        return
    from core.runtime import state_store

    stempel = _nu().isoformat()
    with state_store.med_laas(_STATE):
        post = _rapporterede()
        for i in ids:
            if i:
                post[i] = stempel
        state_store.save_json(_STATE, post)


def _grundlinje() -> str:
    """Tidsstemplet for hvornår vagtposten vågnede. Sættes én gang.

    Alt hvad der er oprettet før det, er historik vi ikke kan udtale os om —
    og som vi derfor husker uden at melde. Se modulets docstring.
    """
    from core.runtime import state_store

    post = state_store.load_json(_GRUNDLINJE, None)
    if isinstance(post, dict) and post.get("foerste_ved"):
        return str(post["foerste_ved"])
    stempel = _nu().isoformat()
    state_store.save_json(_GRUNDLINJE, {"foerste_ved": stempel})
    return stempel


def _hent_runs() -> list[dict[str, Any]]:
    """Kørslerne på `main`. Rejser `ApiUkendt` når vi ikke kunne se dem."""
    req = urllib.request.Request(
        f"{_API}?branch=main&per_page={_VINDUE}",
        headers={
            # GitHub afviser et kald uden User-Agent.
            "User-Agent": "jarvis-ci-status-watch",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raa = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 403/429 = rate-limit, 404 = repoet findes ikke (eller er blevet
        # privat). Begge betyder «vi kan ikke se», ikke «alt er fint».
        raise ApiUkendt(f"http_{exc.code}") from exc
    except Exception as exc:  # netvaerk/utilgaengeligt — samme blindhed
        raise ApiUkendt(f"kaldet_fejlede: {str(exc)[:80]}") from exc
    if not isinstance(raa, dict):
        raise ApiUkendt("uventet_svarform")
    return [r for r in (raa.get("workflow_runs") or []) if isinstance(r, dict)]


def scan_roede() -> list[dict[str, Any]]:
    """Nye røde kørsler på `main` siden sidst — efter grundlinjen.

    Rejser `ApiUkendt` når vi ikke kunne se CI.
    """
    grundlinje = _grundlinje()
    try:
        graense = datetime.fromisoformat(grundlinje)
    except (ValueError, TypeError):  # ulaeselig grundlinje — behandl alt som historik
        graense = _nu()

    kendte = _rapporterede()
    nye: list[dict[str, Any]] = []
    sete: list[str] = []
    for run in _hent_runs():
        rid = str(run.get("id") or "")
        if not rid:
            continue
        sete.append(rid)
        if rid in kendte:
            continue
        if str(run.get("status")) != "completed":
            continue  # kører endnu — ikke rødt, bare ikke færdigt
        if str(run.get("conclusion") or "") not in _ROEDE:
            continue
        try:
            oprettet = datetime.fromisoformat(str(run.get("created_at")).replace("Z", "+00:00"))
        except (ValueError, TypeError):  # ulaeseligt tidsstempel — kan ikke placeres mod grundlinjen
            continue
        if oprettet <= graense:
            continue  # historik fra før vagtposten fandtes — huskes, meldes ikke
        nye.append(run)

    # Alt i vinduet huskes — ogsaa de groenne. Ellers ville et run vi allerede
    # har vurderet blive vurderet igen hver gang, og et gammelt roedt run der
    # laa i vinduet ved grundlinjen kunne dukke op som «nyt» naar dets
    # tidsstempel faldt ud af sammenligningen.
    _husk(sete)
    return nye


def _beskriv(run: dict[str, Any]) -> str:
    navn = str(run.get("display_title") or run.get("name") or "(kørsel)").strip()
    navn = " ".join(navn.split())[:90]
    sha = str(run.get("head_sha") or "")[:9]
    konkl = str(run.get("conclusion") or "?")
    url = str(run.get("html_url") or "")
    linje = f"- `{sha}` — {konkl}: {navn}"
    return f"{linje}\n  {url}" if url else linje


def _sekunder_siden(sidste: Any) -> float | None:
    """Sekunder siden forrige tjek — eller None når stemplet mangler eller er
    ulæseligt. None betyder «mål», ikke «spring over»: en ulaeselig state må
    ikke kunne slukke vagtposten for evigt."""
    if not isinstance(sidste, dict) or not sidste.get("ved"):
        return None
    try:
        return (_nu() - datetime.fromisoformat(str(sidste["ved"]))).total_seconds()
    except (ValueError, TypeError):  # ulaeseligt tidsstempel — maal i stedet for at springe over
        return None


def tik() -> dict[str, Any]:
    """Tjek CI på `main` og læg én followup for nye røde kørsler.

    Kaster aldrig. Kaldes fra de ubetingede daemoner, så den må ikke kunne
    standse et hjerteslag: hver fejl returneres som en status.
    """
    from core.runtime import state_store

    # Throttle. Tidsstemplet ligger i state_store, så målingen holder hen over
    # genstart.
    try:
        sidste = state_store.load_json(_SIDSTE_TJEK, None)
    except Exception as exc:  # ulaeselig state — vi maa hellere maale end springe over
        logger.debug("ci_status_watch: kunne ikke laese sidste tjek: %s", exc)
        sidste = None
    forloebet = _sekunder_siden(sidste)
    if forloebet is not None and forloebet < _MIN_MELLEMRUM_S:
        return {"status": "skip", "grund": "for-tidligt"}

    try:
        nye = scan_roede()
    except Exception as exc:
        # Vi VED ikke om CI er rødt. Saa siger vi ingenting frem for at sige
        # «alt fint» — og vi roerer ikke tidsstemplet, saa vi proever igen.
        logger.debug("ci_status_watch: kunne ikke se CI: %s", exc)
        return {"status": "ukendt", "grund": str(exc)[:120]}

    try:
        state_store.save_json(_SIDSTE_TJEK, {"ved": _nu().isoformat()})
    except Exception as exc:  # tidsstemplet er en optimering — et tabt skriv giver kun et tjek for meget
        logger.debug("ci_status_watch: kunne ikke gemme sidste tjek: %s", exc)

    if not nye:
        return {"status": "ok", "nye": 0}

    tekst = "CI gik rødt på main:\n" + "\n".join(_beskriv(r) for r in nye)
    # 3/10-2026: udgangen flyttet fra heartbeat-trigger-koeen til
    # notification_bridge — samme grund som i `background_job_watch`.
    #
    # Koeen toemmes aldrig: `consume_trigger` kaldes kun bag
    # `ping_channel != "webchat"` og kun fra head. En CI-alarm der ikke kan
    # naa frem er ikke en alarm — og det var hele grunden til at vagtposten
    # blev bygget (ci var roedt i to doegn uden at nogen saa det).
    #
    # `send_session_notification` er den etablerede vej for en
    # baggrundsproces der vil sige noget. `push=False`: denne vej sendte
    # ikke mobil-push foer.
    try:
        from core.services.notification_bridge import (
            delivery_succeeded,
            send_session_notification,
        )

        levering = send_session_notification(
            tekst[:2000],
            source="ci-status-watch",
            push=False,
        )
    except Exception as exc:
        logger.warning("ci_status_watch: kunne ikke sende besked: %s", exc)
        return {"status": "fejl", "nye": len(nye), "grund": str(exc)[:120]}
    # "queued" ER en succes — se `_DELIVERY_OK_STATUSES`.
    if not delivery_succeeded(levering):
        # Uden det her tjek ville vi melde «sendt» om en alarm der aldrig
        # blev leveret — og runnene er allerede markeret sete, saa de ville
        # ikke komme igen.
        return {
            "status": "fejl",
            "nye": len(nye),
            "grund": f"levering-{levering.get('status') or 'error'}",
        }
    return {"status": "ok", "nye": len(nye), "tekst": tekst}
