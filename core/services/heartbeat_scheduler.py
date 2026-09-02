"""Hjerteslagets dæmon — tråden der spørger «er det tid?» hvert 30. sekund.

Udskilt fra heartbeat_runtime.py (7.221 linjer) 2026-09-02, mens vi jagtede en
stilstand: runtimen meldte selv `due: true` i over ti minutter uden at slå, og
det eneste der hjalp var en genstart.

Enheden er dæmonen og kun dæmonen: trådens liv, dens stop-signal, dens kadence,
og løkken. Selve beslutningen om HVAD et hjerteslag gør bliver i
heartbeat_runtime — den skal ikke flytte med, og importeres derfor dovent inde i
funktionerne. Det er ikke pynt: modulerne peger på hinanden, og en import på
modulniveau ville lave en cirkel.

DEN VIGTIGSTE ÆNDRING her er én linje. Løkkens iterations-log stod på debug og
kom aldrig ud. Under stilstanden kunne vi derfor ikke afgøre det enkleste
spørgsmål af alle — TÆLLER LØKKEN OVERHOVEDET VIDERE? — uden at genstarte, og en
genstart sletter beviset. Nu logges hver iteration på info med et løbenummer, så
en stilstand kan læses direkte af journalen: står tallet stille, er tråden væk;
tæller det videre uden at slaget falder, ligger fejlen længere inde.

Ét tal hvert 30. sekund er en pris værd at betale for at kunne se en tavs tråd.
"""
from __future__ import annotations

import logging
import threading

# BEVIDST heartbeat_runtime's logger og ikke __name__.
#
# Første udgave brugte logging.getLogger(__name__), og så forsvandt hver eneste
# linje fra dæmonen — også «loop entered», som skrives før noget som helst andet.
# Modulet importeres DOVENT inde i start(), altså efter uvicorn har sat sit
# log-setup op, og en logger født på det tidspunkt når ikke journalen. Linjerne
# fra heartbeat_runtime gør, fordi det modul var importeret inden.
#
# En udskillelse må ikke kunne gøre kode tavs. Dæmonen logger derfor dér hvor
# den altid har logget — og en fremtidig oprydning i log-opsætningen kan flytte
# den tilbage, når kanalen er ens for alle moduler.
logger = logging.getLogger("core.services.heartbeat_runtime")

INTERVAL_SECONDS = 30

_STOP = threading.Event()
_THREAD: threading.Thread | None = None
_ITERATION = 0


def is_running() -> bool:
    """Lever planlægger-tråden?

    Bemærk at dette KUN siger noget om tråden — ikke om den udretter noget.
    Netop den forskel var kernen i stilstanden 2026-09-02: `scheduler_active`
    stod på true hele vejen igennem, mens intet slag faldt.
    """
    return bool(_THREAD and _THREAD.is_alive())


def iterations() -> int:
    """Antal gennemløb siden tråden startede. Står tallet stille, er løkken væk."""
    return _ITERATION


def stop_event() -> threading.Event:
    return _STOP


def start(*, name: str = "default") -> None:
    """Start dæmonen. Er den allerede i gang, sker der ingenting."""
    global _THREAD, _ITERATION
    if is_running():
        return

    from core.services import heartbeat_runtime as hb

    recovery = hb._prepare_scheduler_startup(name=name)
    _STOP.clear()
    _ITERATION = 0
    thread = threading.Thread(
        target=_loop,
        kwargs={
            "name": name,
            "startup_recovery_requested": bool(recovery.get("startup_recovery_requested")),
        },
        name="jarvis-heartbeat-scheduler",
        daemon=True,
    )
    thread.start()
    _THREAD = thread
    hb._HEARTBEAT_LAST_SCHEDULE_SNAPSHOT = {
        "schedule_state": str(recovery.get("schedule_state") or ""),
        "due": bool(recovery.get("due")),
    }
    logger.info(
        "HEARTBEAT-STATE: scheduler started name=%s due=%s schedule_state=%s recovery_status=%s",
        name,
        bool(recovery.get("due")),
        str(recovery.get("schedule_state") or "unknown"),
        str(recovery.get("recovery_status") or "idle"),
    )
    hb.event_bus.publish(
        "heartbeat.scheduler_started",
        {
            "scheduler_active": True,
            "schedule_state": recovery.get("schedule_state"),
            "due": recovery.get("due"),
            "recovery_status": recovery.get("recovery_status"),
            "next_tick_at": recovery.get("next_tick_at"),
        },
    )


def stop(*, name: str = "default") -> None:
    global _THREAD
    from core.services import heartbeat_runtime as hb

    _STOP.set()
    thread = _THREAD
    if thread and thread.is_alive():
        thread.join(timeout=1.0)
    _THREAD = None
    hb._mark_scheduler_stopped(name=name)
    hb._HEARTBEAT_LAST_SCHEDULE_SNAPSHOT = {}
    logger.info("heartbeat scheduler stopped name=%s", name)


def _loop(*, name: str, startup_recovery_requested: bool) -> None:
    global _ITERATION
    from core.services import heartbeat_runtime as hb

    logger.info(
        "heartbeat scheduler loop entered name=%s startup_recovery_requested=%s interval_seconds=%s",
        name,
        startup_recovery_requested,
        INTERVAL_SECONDS,
    )
    try:
        hb._poll_heartbeat_schedule_with_trigger(
            name=name,
            due_trigger="startup-recovery" if startup_recovery_requested else "scheduled",
        )
    except Exception as exc:
        hb.event_bus.publish(
            "heartbeat.tick_blocked",
            {
                "blocked_reason": "scheduler-error",
                "detail": str(exc),
                "trigger": "startup-recovery" if startup_recovery_requested else "scheduled",
            },
        )

    while not _STOP.wait(INTERVAL_SECONDS):
        _ITERATION += 1
        try:
            # INFO, ikke debug. Se modulets docstring: uden dette tal kan en
            # tavs tråd ikke skelnes fra en tråd der kører uden at udrette
            # noget — og den forskel afgør hvor man skal lede.
            logger.info("HEARTBEAT-LOOP: iteration=%s name=%s", _ITERATION, name)
            hb.poll_heartbeat_schedule(name=name)
        except Exception as exc:
            logger.exception("heartbeat scheduler iteration failed name=%s", name)
            hb.event_bus.publish(
                "heartbeat.tick_blocked",
                {
                    "blocked_reason": "scheduler-error",
                    "detail": str(exc),
                    "trigger": "scheduled",
                },
            )
