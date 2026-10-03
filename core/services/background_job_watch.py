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

Her lukkes hullet: signalerne læses, vi husker hvad der er sagt, og kun det
NYE giver en followup.

**Hvorfor i per-bruger-konteksten.** Første udgave laa i de ubetingede
daemoner (`tik_indre_daemoner`). Den var blind i drift, maalt fire minutter
efter commit: `current_user_id()` er TOM uden for en request, og bro-kaldet
til operatoerens maskine kraever et bruger-id. Den svarede «ingen-bruger»
hvert tik og gjorde intet. Bruger-id'et findes i `_tik_for_bruger`, hvor
`set_context()` binder det omkring daemonerne — saa der hoerer den hjem.

**Hvorfor gennem `background_jobs.liste`.** Den læser alle fire kilder og er
allerede den flade panelet bruger. En femte læser af de samme filer ville
være præcis den drift QUICK_FACTS advarer om: to steder der kan komme i
utakt uden at nogen ser det.

**To kilder, ikke én — og blindhed er delvis (3/10-2026, anden udgave).**
Første udgave behandlede `bridge_ok=False` som «vi ved ingenting» og kastede
HELE listen. Det er forkert: supervisor-jobs ligger paa serveren og er
laesbare uden bro. En blind bro betyder at OPERATOER-delen er ukendt — ikke
at vi intet kan se. Fejlen er den samme klasse som `test_publish_scan` blev
skrevet for at fange: en flade der siger «alt fint» naar den ikke kan se.
Her er den bare spejlet — en flade der sagde «intet» naar den godt kunne se
noget.

**Hvorfor en grundlinje.** `process_supervisor`-registret er et ARKIV uden
oprydning: ni poster, hvoraf de nyeste stoppede 16. september og to i maj.
Uden en grundlinje ville foerste koersel melde en proces der doede for fire
maaneder siden som om den lige var faerdig. Kun det der stopper EFTER
vagtposten vaagnede, kan blive en besked. Konsekvensen siges hoejt: den kan
ikke melde hvad der skete foer den fandtes — den fanger det naeste.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_STATE = "bg_jobs_rapporteret"
_SIDSTE_TJEK = "bg_jobs_sidste_tjek"
#: Foerste koersel saetter denne. Alt der er stoppet FOER den er historik vi
#: ikke kan udtale os om — se modulets docstring om supervisor-arkivet.
_GRUNDLINJE = "bg_jobs_grundlinje"

# Et bro-kald er en netværkstur. Hjerteslaget tikker langt oftere end et
# byg bliver færdigt, så vi måler sjældnere end vi tikker.
_MIN_MELLEMRUM_S = 90.0

# Hvor længe et rapporteret job huskes. Uden en grænse vokser filen for
# evigt; med en for kort grænse kan et gammelt job blive sagt to gange.
_HUSK_DAGE = 7

#: Kilderne der bærer et fuldførelses-bevis.
#:
#: `operator` = shells paa Bjoerns maskine, `.rc`-filen skrives naar de doer.
#: `supervisor` = processer Jarvis selv starter, med exit-kode og stop-tid.
#: `shell` (aabne sessioner) og `agent` (scouts) er BEVIDST udeladt: de har
#: ingen exit-kode at maale paa, og scouts har deres eget register.
_KILDER = ("operator", "supervisor")


def _nu() -> datetime:
    return datetime.now(UTC)


def _laes_tid(vaerdi: Any) -> datetime | None:
    """ISO-tidsstempel fra state eller registry — eller None.

    Tolererer baade `Z` og `+00:00`, fordi de to skrivere i repoet ikke er
    enige (process_supervisor skriver `Z`, state_store skriver `+00:00`).
    """
    if not vaerdi:
        return None
    try:
        return datetime.fromisoformat(str(vaerdi).replace("Z", "+00:00"))
    except (ValueError, TypeError):  # ulaeseligt tidsstempel — kan ikke dateres
        return None


def _grundlinje() -> datetime:
    """Tidsstemplet for hvornår vagtposten vågnede. Sættes én gang."""
    from core.runtime import state_store

    try:
        post = state_store.load_json(_GRUNDLINJE, None)
    except Exception as exc:  # ulaeselig state — vi saetter en ny grundlinje
        logger.debug("background_job_watch: kunne ikke laese grundlinje: %s", exc)
        post = None
    naar = _laes_tid((post or {}).get("foerste_ved") if isinstance(post, dict) else None)
    if naar is not None:
        return naar
    naar = _nu()
    try:
        state_store.save_json(_GRUNDLINJE, {"foerste_ved": naar.isoformat()})
    except Exception as exc:  # et tabt skriv giver kun én ekstra tavs koersel
        logger.debug("background_job_watch: kunne ikke gemme grundlinje: %s", exc)
    return naar


def _rapporterede() -> dict[str, str]:
    """{noegle: iso-tidsstempel} for det vi allerede har sagt.

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
        stempel = _laes_tid(vaerdi)
        if stempel is None:
            continue  # ulaeseligt tidsstempel — posten kan ikke dateres
        if stempel >= graense:
            ud[str(noegle)] = str(vaerdi)
    return ud


def _husk(noegler: list[str]) -> None:
    """Skriv noeglerne som rapporterede — atomisk, så api og runtime ikke
    overskriver hinandens lister (samme begrundelse som `state_store.med_laas`
    selv bærer)."""
    if not noegler:
        return
    from core.runtime import state_store

    stempel = _nu().isoformat()
    with state_store.med_laas(_STATE):
        post = _rapporterede()
        for n in noegler:
            if n:
                post[n] = stempel
        state_store.save_json(_STATE, post)


def _noegle(job: dict[str, Any]) -> str:
    """Stabil identitet for et job.

    Operator-shells har et unikt id (`<id>.rc` skrives én gang). Supervisor-
    NAVNE genbruges derimod: `grid-bot` kan startes, do og startes igen. Derfor
    baerer noeglen ogsaa stop-tidspunktet — ellers ville en genstartet proces
    blive laest som «allerede rapporteret».
    """
    jid = str(job.get("id") or "")
    if job.get("kilde") == "supervisor":
        return f"{jid}|{job.get('stopped_at') or ''}"
    return jid


def scan_finished(*, uid: str) -> dict[str, Any]:
    """Nye fuldførte jobs siden sidst, plus om operator-siden var laesbar.

    Returnerer `{"nye": [...], "blind": bool}`. `blind` betyder at OPERATOER-
    delen ikke kunne ses — ikke at listen var tom. Kalderen skal melde det
    som en delvis sandhed frem for at kaste det hele væk.
    """
    from core.services.background_jobs import liste
    from core.tools.simple_tools import execute_tool

    def _exec(navn: str, args: dict[str, Any]) -> dict[str, Any]:
        return execute_tool(navn, args) or {}

    svar = liste(uid=uid, exec_fn=_exec, kun_aktive=False)
    # Broen er blind for OPERATOER-delen. Supervisor-jobs ligger lokalt og er
    # laesbare uanset — saa vi kaster ikke listen vaek, vi markerer hvad der
    # ikke kunne ses.
    blind = svar.get("bridge_ok") is False

    grundlinje = _grundlinje()
    kendte = _rapporterede()
    nye: list[dict[str, Any]] = []
    for job in svar.get("jobs") or []:
        kilde = job.get("kilde")
        if kilde not in _KILDER:
            continue
        kode = job.get("exit_code")
        if kode is None:
            continue  # kører endnu — ikke fuldført, bare ikke færdig
        if kilde == "supervisor":
            # Arkivet rydder sig ikke. En post der stoppede foer vi vaagnede
            # er historik, ikke en begivenhed.
            stoppet = _laes_tid(job.get("stopped_at"))
            if stoppet is None or stoppet <= grundlinje:
                continue
        n = _noegle(job)
        if not n or n in kendte:
            continue
        nye.append(job)
    if nye:
        _husk([_noegle(j) for j in nye])
    return {"nye": nye, "blind": blind}


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
    naar = _laes_tid((sidste or {}).get("ved") if isinstance(sidste, dict) else None)
    if naar is None:
        return None
    return (_nu() - naar).total_seconds()


def tik(*, uid: str = "") -> dict[str, Any]:
    """Tjek for færdige jobs og læg én followup. Kaster aldrig.

    Kaldes fra hjerteslaget, så den må ikke kunne standse det: hver fejl
    returneres som en status, ikke som en undtagelse.
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
        svar = scan_finished(uid=uid)
    except Exception as exc:
        # Listen kunne slet ikke bygges — ikke engang de lokale kilder. Vi VED
        # ikke hvad der kører, og så siger vi ingenting frem for «intet».
        logger.debug("background_job_watch: kunne ikke se jobs: %s", exc)
        return {"status": "ukendt", "grund": "kunne-ikke-laeses"}

    nye = svar.get("nye") or []
    blind = bool(svar.get("blind"))

    try:
        state_store.save_json(_SIDSTE_TJEK, {"ved": _nu().isoformat()})
    except Exception as exc:  # tidsstemplet er en optimering — et tabt skriv giver kun et tjek for meget
        logger.debug("background_job_watch: kunne ikke gemme sidste tjek: %s", exc)

    if not nye:
        # Intet at melde. Er operator-siden blind, er det stadig en delvis
        # sandhed — den skal ikke se ud som «alt er fint».
        return {"status": "ukendt" if blind else "ok", "nye": 0}

    tekst = "Baggrundsjob færdig:\n" + "\n".join(_beskriv(j) for j in nye)
    if blind:
        tekst += "\n(operatørens maskine kunne ikke ses — flere kan mangle)"
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
    return {
        "status": "ukendt" if blind else "ok",
        "nye": len(nye),
        "blind": blind,
        "tekst": tekst,
    }
