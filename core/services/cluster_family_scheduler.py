"""Cluster-familiernes egen løkke — tråden der spørger «hvilken familie er det tid til?»

Baggrund, fordi den er hele grunden til at filen findes:

Den 15/7-2026 blev 55 daemons pensioneret og foldet ind i 11 cluster-familier.
Familierne blev wired ind i ``_build_influence_trace`` — altså den monolitiske
``run_heartbeat_tick``-sti. Men scheduleren var allerede blevet lagt om den
18/5, så den kalder ``tick_with_phases()`` (sense/reflect/act) i stedet. Den sti
rammer aldrig familie-kaldene. Resultatet var at familierne kun kørte når
act-fasen tilfældigvis fandt priorities; ellers landede slaget i
``productive_idle``, og så rørte ingen af dem sig. Målt 5/9-2026: kadencer på
1-5 minutter, sidste kørsel over en time før.

Det der stod stille var ikke pynt: visual_memory, mail_checker, hele
hukommelsesvedligeholdelsen (decay/pruning/maintenance/safeguard),
associative_recall, curiosity, user_model, thought_stream, dream_insight.

Hvorfor en EGEN tråd og ikke bare et kald mere inde i faserne: familierne tog
~50 sekunder om at komme igennem da jeg målte dem, og hjerteslagets tick har en
frist på 90 sekunder. Lægger man familierne ind på den sti, æder de fristen og
sulter faserne — og præcis dét var grunden til at kadencerne blev skruet ned
under jagten på cutoff-fejlen. Familierne får derfor deres egen løkke, hvor en
langsom familie kun kan forsinke de andre familier og aldrig hjerteslaget.

Løkken spørger hvert 20. sekund og kører kun de familier der er forfaldne efter
deres EGEN kadence i daemon_manager. Hver familie køres bag sin egen frist, den
samme som den havde på den gamle sti. Familierne er i forvejen self-safe og
self-throttling; løkken her tilføjer ikke ny politik, den sørger bare for at
nogen kalder dem.

Kill-switch: ``cluster_family_scheduler_enabled`` i runtime-config. Sæt den til
false, og løkken kører videre men rører ingen familier — så en kadence der viser
sig at koste for meget kan slås fra uden en genstart.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime

# BEVIDST "uvicorn.error" — den eneste logger i processen der har handlers.
# Et modulnavn går i gulvet. Samme lærepenge som heartbeat_scheduler betalte.
logger = logging.getLogger("uvicorn.error")

INTERVAL_SECONDS = 20

# Familie → frist i sekunder. Tallene er IKKE nye: de er de samme som familierne
# havde i heartbeat_runtime_influence, så opførslen er uændret bortset fra hvem
# der kalder. Kadencen kommer fra daemon_manager, ikke herfra — ét sted at skrue.
_FAMILY_DEADLINES: tuple[tuple[str, float], ...] = (
    ("cluster_somatic", 8.0),
    ("cluster_innervoice", 25.0),
    ("cluster_affect", 25.0),
    ("cluster_narrative", 40.0),
    ("cluster_cognition", 40.0),
    ("cluster_memory", 60.0),
    ("cluster_aesthetic", 20.0),
    ("cluster_relation", 20.0),
    ("cluster_projects", 30.0),
    ("cluster_infra", 40.0),
)

_STOP = threading.Event()
_THREAD: threading.Thread | None = None
_ITERATION = 0
_LAST_RAN: dict[str, str] = {}


def is_running() -> bool:
    """Lever tråden? Siger intet om hvorvidt den udretter noget — se iterations()."""
    return bool(_THREAD and _THREAD.is_alive())


def iterations() -> int:
    """Gennemløb siden start. Står tallet stille, er løkken væk."""
    return _ITERATION


def stop_event() -> threading.Event:
    return _STOP


def _enabled() -> bool:
    """Kill-switch. Self-safe: kan config ikke læses, kører vi videre."""
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get("cluster_family_scheduler_enabled", True))
    except Exception:
        return True


def _tick_functions() -> dict[str, object]:
    """Slå familiernes tick-funktioner op. De bor i to moduler efter en udskillelse."""
    found: dict[str, object] = {}
    for module_name in (
        "core.services.cluster_daemon_families",
        "core.services.cluster_daemon",
    ):
        try:
            module = __import__(module_name, fromlist=["x"])
        except Exception as exc:
            logger.warning("cluster-family-scheduler: kan ikke importere %s: %s", module_name, exc)
            continue
        for family, _deadline in _FAMILY_DEADLINES:
            if family in found:
                continue
            fn = getattr(module, "tick_" + family, None)
            if fn is not None:
                found[family] = fn
    return found


def _is_due(family: str, cadence_minutes: float, last_run_at: str) -> bool:
    """Er familien forfalden efter sin egen kadence?

    Har den aldrig kørt, er den forfalden. Kan tidsstemplet ikke læses, lader vi
    den køre — et ulæseligt tidsstempel må ikke kunne holde en familie nede.
    """
    if not last_run_at:
        return True
    try:
        last = datetime.fromisoformat(str(last_run_at).replace("Z", "+00:00"))
    except Exception:
        return True
    elapsed_minutes = (datetime.now(UTC) - last.astimezone(UTC)).total_seconds() / 60.0
    return elapsed_minutes >= max(float(cadence_minutes or 1.0), 0.5)


def run_due_families() -> dict[str, object]:
    """Kør de familier der er forfaldne. Returnerer hvad der skete — også til test.

    Kører dem én ad gangen med vilje. Parallelt ville de slås om DB'en og om den
    billige lane, og en familie der venter på en provider ville skjule hvilken.
    """
    if not _enabled():
        return {"skipped": "kill-switch", "ran": [], "due": []}

    from core.services import daemon_manager as dm
    from core.services.heartbeat_runtime import _daemon_tick_with_deadline

    ticks = _tick_functions()
    states = {str(s.get("name")): s for s in dm.get_all_daemon_states()}

    ran: list[str] = []
    failed: list[str] = []
    due: list[str] = []

    for family, deadline in _FAMILY_DEADLINES:
        try:
            if not dm.is_enabled(family):
                continue
            state = states.get(family) or {}
            cadence = state.get("effective_cadence_minutes")
            if not _is_due(family, float(cadence or 1.0), str(state.get("last_run_at") or "")):
                continue
            due.append(family)

            fn = ticks.get(family)
            if fn is None:
                logger.warning("cluster-family-scheduler: ingen tick-funktion for %s", family)
                failed.append(family)
                continue

            result = _daemon_tick_with_deadline(family, fn, deadline_seconds=deadline)
            dm.record_daemon_tick(family, result or {})
            _LAST_RAN[family] = datetime.now(UTC).isoformat()
            ran.append(family)
        except Exception as exc:
            # Én familie må aldrig kunne vælte de andre.
            logger.warning("cluster-family-scheduler: %s fejlede: %s", family, exc)
            failed.append(family)

    return {"ran": ran, "due": due, "failed": failed}


def _loop() -> None:
    global _ITERATION
    logger.info("CLUSTER-FAMILY-LOOP: entered interval=%ss", INTERVAL_SECONDS)
    while not _STOP.is_set():
        _ITERATION += 1
        try:
            outcome = run_due_families()
            ran = outcome.get("ran") or []
            if ran:
                logger.info(
                    "CLUSTER-FAMILY-LOOP: iteration=%s koerte=%s", _ITERATION, ",".join(ran)
                )
            elif _ITERATION % 15 == 0:
                # Et livstegn nu og da, så en tavs tråd kan skelnes fra en rolig en.
                logger.info(
                    "CLUSTER-FAMILY-LOOP: iteration=%s ingen forfaldne familier", _ITERATION
                )
        except Exception:
            logger.exception("cluster-family-scheduler: iteration fejlede")
        _STOP.wait(INTERVAL_SECONDS)
    logger.info("CLUSTER-FAMILY-LOOP: stopped iteration=%s", _ITERATION)


def start() -> None:
    """Start løkken. Kører den allerede, sker der ingenting."""
    global _THREAD, _ITERATION
    if is_running():
        return
    _STOP.clear()
    _ITERATION = 0
    thread = threading.Thread(
        target=_loop, name="jarvis-cluster-family-scheduler", daemon=True,
    )
    thread.start()
    _THREAD = thread
    logger.info("CLUSTER-FAMILY-STATE: scheduler started families=%d", len(_FAMILY_DEADLINES))


def stop() -> None:
    global _THREAD
    _STOP.set()
    thread = _THREAD
    if thread and thread.is_alive():
        thread.join(timeout=2.0)
    _THREAD = None
    logger.info("cluster-family-scheduler stopped")


def build_cluster_family_scheduler_surface() -> dict[str, object]:
    """Hvad løkken laver — til Central og til at svare på «kører de?»."""
    from core.services import daemon_manager as dm

    states = {str(s.get("name")): s for s in dm.get_all_daemon_states()}
    now = datetime.now(UTC)
    families = []
    for family, deadline in _FAMILY_DEADLINES:
        state = states.get(family) or {}
        last = str(state.get("last_run_at") or "")
        minutes_ago = None
        try:
            minutes_ago = round(
                (now - datetime.fromisoformat(last.replace("Z", "+00:00")).astimezone(UTC)
                 ).total_seconds() / 60.0, 1)
        except Exception:
            pass
        families.append({
            "family": family,
            "enabled": bool(state.get("enabled")),
            "cadence_minutes": state.get("effective_cadence_minutes"),
            "deadline_seconds": deadline,
            "last_run_at": last,
            "minutes_since_last_run": minutes_ago,
        })
    return {
        "active": is_running(),
        "enabled": _enabled(),
        "iterations": _ITERATION,
        "interval_seconds": INTERVAL_SECONDS,
        "families": families,
    }
