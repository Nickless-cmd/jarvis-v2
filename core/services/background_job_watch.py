"""Færdige baggrunds-shells — set, ikke gættet.

Signalet har ligget der siden `operator_background` blev bygget: når processen
dør, skrives `<id>.rc` med exit-koden. Men indtil 3/10-2026 læste ingen den
uden at spørge. Panelet er en pull-flade, og heartbeat kendte slet ikke
filerne.

Hvad det kostede, målt samme dag: jeg satte en wakeup til kl. 13:29 og
*HÅBEDE* at et byg var færdigt. Var det færdigt 13:10, ventede jeg 19 minutter
i tomgang; var det ikke færdigt, måtte jeg sætte en ny. En timer der
approximerer en begivenhed — når begivenheden selv skriver et tidsstempel på
disken.

Her lukkes hullet: `.rc`-filerne læses gennem broen, vi husker hvad der er
sagt, og kun det NYE giver en followup.

**Hvorfor i de ubetingede daemoner.** `act_phase` dispatcher kun videre til
`run_heartbeat_tick` når der ER prioriteter; ellers går tiket til
`productive_idle`. Et fuldførelses-signal er præcis det der skal kunne komme
når der ellers er roligt — samme fejlklasse som `heartbeat_daemon_ticks` selv
blev udskilt for 25/9-2026, hvor hvert tik gik til `productive_idle` og de
~30 daemoner holdt op med at køre.

**Hvorfor gennem `background_jobs.liste`.** Den læser alle fire kilder og er
allerede den flade panelet bruger. En femte læser af de samme filer ville
være præcis den drift QUICK_FACTS advarer om: to steder der kan komme i
utakt uden at nogen ser det.

**Broen må ikke kunne vælte et hjerteslag.** Er broen nede, ved vi ikke hvad
der kører derovre — så vi siger ingenting og prøver igen næste gang. En tom
liste er ikke «der kørte ingenting»; det er «vi kunne ikke se». De to er
stik modsat, og kun den ene må blive til en besked.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_STATE = "bg_jobs_rapporteret"
_SIDSTE_TJEK = "bg_jobs_sidste_tjek"

# Et bro-kald er en netværkstur. Hjerteslaget tikker langt oftere end et
# byg bliver færdigt, så vi måler sjældnere end vi tikker.
_MIN_MELLEMRUM_S = 90.0

# Hvor længe et rapporteret shell-id huskes. Uden en grænse vokser filen for
# evigt; med en for kort grænse kan en gammel shell blive sagt to gange.
_HUSK_DAGE = 7


def _nu() -> datetime:
    return datetime.now(UTC)


def _rapporterede() -> dict[str, str]:
    """{shell_id: iso-tidsstempel} for det vi allerede har sagt.

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
    """Skriv id'erne som rapporterede — atomisk, så api og runtime ikke
    overskriver hinandens lister (samme begrundelse som `state_store.med_laas`
    selv bærer)."""
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


class BroUkendt(RuntimeError):
    """Vi kunne ikke se operatørens maskine.

    Det er ikke det samme som at der ikke kørte noget — og forskellen er hele
    grunden til at klassen findes. `background_jobs.liste` er fail-soft: den
    sluger `BroTier` og saetter `bridge_ok=False`, saa en tom liste kan betyde
    to stik modsatte ting. Uden det her tjek ville vagtposten melde «alt
    fint» naar den i virkeligheden var blind.
    """


def scan_finished(*, uid: str) -> list[dict[str, Any]]:
    """Nye fuldførte baggrunds-shells siden sidst.

    Rejser `BroUkendt` naar broen ikke svarede — se klassen.
    """
    from core.services.background_jobs import liste
    from core.tools.simple_tools import execute_tool

    def _exec(navn: str, args: dict[str, Any]) -> dict[str, Any]:
        return execute_tool(navn, args) or {}

    svar = liste(uid=uid, exec_fn=_exec, kun_aktive=False)
    if svar.get("bridge_ok") is False:
        raise BroUkendt("broen svarede ikke — vi ved ikke hvad der kører derovre")
    kendte = _rapporterede()
    nye: list[dict[str, Any]] = []
    for job in svar.get("jobs") or []:
        if job.get("kilde") != "operator":
            continue
        kode = job.get("exit_code")
        if kode is None:
            continue  # kører endnu — ikke fuldført, bare ikke færdig
        jid = str(job.get("id") or "")
        if not jid or jid in kendte:
            continue
        nye.append(job)
    if nye:
        _husk([str(j.get("id") or "") for j in nye])
    return nye


def _beskriv(job: dict[str, Any]) -> str:
    navn = str(job.get("navn") or "(baggrunds-shell)").strip()
    navn = " ".join(navn.split())[:90]
    try:
        kode = int(job.get("exit_code") or 0)
    except (TypeError, ValueError):  # en ikke-tal exit-kode kan ikke graderes — antag ok
        kode = 0
    dom = "færdig" if kode == 0 else f"FEJLEDE (exit {kode})"
    return f"- {navn} — {dom}"


def _bruger_id() -> str:
    """Brugeren der ejer baggrunds-shellene. Tom streng når konteksten ikke
    kan slås op — så ved vi ikke hvem der skal have beskeden."""
    try:
        from core.identity.workspace_context import current_user_id
    except Exception as exc:  # kontekst-modulet utilgaengeligt — ingen bruger at maale for
        logger.debug("background_job_watch: brugerkontekst utilgaengelig: %s", exc)
        return ""
    try:
        return current_user_id() or ""
    except Exception as exc:  # ingen bunden bruger (fx i et bart hjerteslag)
        logger.debug("background_job_watch: ingen bundet bruger: %s", exc)
        return ""


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


def tik(*, uid: str = "") -> dict[str, Any]:
    """Tjek for færdige shells og læg én followup. Kaster aldrig.

    Kaldes fra de ubetingede daemoner, så den må ikke kunne standse et
    hjerteslag: hver fejl returneres som en status, ikke som en undtagelse.
    """
    from core.runtime import state_store

    if not uid:
        uid = _bruger_id()
    if not uid:
        return {"status": "skip", "grund": "ingen-bruger"}

    # Throttle. `_forloebet_sekunder`-mønsteret fra heartbeat_daemon_ticks:
    # tidsstemplet ligger i state_store, så målingen holder hen over genstart.
    try:
        sidste = state_store.load_json(_SIDSTE_TJEK, None)
    except Exception as exc:  # ulaeselig state — vi maa hellere maale end springe over
        logger.debug("background_job_watch: kunne ikke laese sidste tjek: %s", exc)
        sidste = None
    forloebet = _sekunder_siden(sidste)
    if forloebet is not None and forloebet < _MIN_MELLEMRUM_S:
        return {"status": "skip", "grund": "for-tidligt"}

    try:
        nye = scan_finished(uid=uid)
    except Exception as exc:
        # Broen tier, eller listen kunne ikke bygges. Vi VED ikke hvad der
        # kører derovre — og så siger vi ingenting frem for at sige «intet».
        logger.debug("background_job_watch: kunne ikke se jobs: %s", exc)
        return {"status": "ukendt", "grund": "broen-svarede-ikke"}

    try:
        state_store.save_json(_SIDSTE_TJEK, {"ved": _nu().isoformat()})
    except Exception as exc:  # tidsstemplet er en optimering — et tabt skriv giver kun et tjek for meget
        logger.debug("background_job_watch: kunne ikke gemme sidste tjek: %s", exc)

    if not nye:
        return {"status": "ok", "nye": 0}

    tekst = "Baggrundsjob færdig:\n" + "\n".join(_beskriv(j) for j in nye)
    try:
        from core.runtime.heartbeat_triggers import set_trigger_for_default_workspace

        post = set_trigger_for_default_workspace(
            reason="background-job-done",
            source="background_job_watch",
            text=tekst[:2000],
        )
    except Exception as exc:
        logger.warning("background_job_watch: kunne ikke laegge followup: %s", exc)
        return {"status": "fejl", "nye": len(nye), "grund": str(exc)[:120]}
    if post is None:
        # Funktionen sluger sin EGEN fejl og returnerer None (fx naar
        # arbejdsrummet ikke kan slaaes op). Uden det her tjek ville vi melde
        # «sendt» om en besked der aldrig blev lagt — og jobbet er allerede
        # markeret som rapporteret, saa den ville ikke komme igen.
        return {"status": "fejl", "nye": len(nye), "grund": "trigger-blev-ikke-lagt"}
    return {"status": "ok", "nye": len(nye), "tekst": tekst}
