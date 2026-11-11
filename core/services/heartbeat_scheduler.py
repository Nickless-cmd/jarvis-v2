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

# BEVIDST "uvicorn.error" — samme logger som heartbeat_runtime (linje 219).
#
# To forsøg gik galt før dette. Først logging.getLogger(__name__): hver eneste
# linje fra dæmonen forsvandt, også «loop entered», som skrives før noget som
# helst andet. Så gættede jeg på import-rækkefølge og bad om
# getLogger("core.services.heartbeat_runtime") — lige så tavs.
#
# Årsagen var hverken: heartbeat_runtime logger IKKE på sit eget modulnavn. Den
# bruger uvicorn's egen fejl-logger, og det er den ENESTE kanal i processen der
# har handlers. Et modulnavn — hvilket som helst — går i gulvet.
#
# En udskillelse må ikke kunne gøre kode tavs. Dæmonen logger derfor præcis dér
# hvor den loggede før den flyttede.
logger = logging.getLogger("uvicorn.error")

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
        name="jarvis-tick-scheduler",
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


# ── Måling af liv (ikke flag) ────────────────────────────────────────────────
# Fejlformen (2026-09-02 og 2026-11-11): `scheduler_active`/`scheduler_health`
# er et FLAG der skrives af start(), og ingen målte om tråden faktisk slog.
# assess_liveness er ren (ingen I/O) så den kan testes og genbruges af både
# heartbeat_status og vagten nedenfor.

def _parse_iso(value: object):
    from datetime import UTC, datetime

    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        # Ulæseligt tidsstempel = «vi ved ikke hvornår», ikke «nu». Kalderen
        # behandler None som en MANGLENDE måling (se assess_liveness: aktiv
        # uden parsbar next_tick_at er DEGRADED, ikke ACTIVE). At gætte et
        # tidspunkt her ville gøre en død dæmon til en levende.
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def assess_liveness(
    *,
    scheduler_active: object,
    scheduler_health: object,
    next_tick_at: object,
    last_tick_at: object = None,
    interval_minutes: object = None,
    thread_running: bool | None,
    iterations_count: int | None,
    db_last_tick_started_at: object = None,
    now=None,
) -> dict[str, object]:
    """Dom om dæmonen LEVER, ud fra målinger — ikke ud fra flaget alene.

    verdict: ACTIVE | STARTING | DEGRADED | STALLED | STOPPED.
    STALLED: next_tick_at overskredet med > 2× interval.
    DEGRADED: flag og måling er uenige (mismatch ikke tom).
    """
    from datetime import UTC, datetime

    now = now or datetime.now(UTC)
    try:
        interval = float(interval_minutes) if interval_minutes else 15.0
    except (TypeError, ValueError):
        interval = 15.0
    active = bool(scheduler_active)
    nxt = _parse_iso(next_tick_at)
    overdue = (now - nxt).total_seconds() / 60.0 if nxt and now > nxt else 0.0
    newest = max(
        [d for d in (_parse_iso(last_tick_at), _parse_iso(db_last_tick_started_at)) if d],
        default=None,
    )
    mismatch: list[str] = []
    # None betyder at kalderen IKKE er schedulerens ejerproces. False betyder
    # derimod at ejerprocessen faktisk har målt sin lokale tråd som død. En
    # API-proces har altid sin egen tomme kopi af modul-globalerne og må derfor
    # aldrig sende False/0 som om det var en global måling.
    if active and thread_running is False:
        mismatch.append("flag_active_but_thread_not_running")
    if not active and thread_running is True:
        mismatch.append("flag_stopped_but_thread_running")
    if active and nxt is None:
        # Kan vi ikke læse næste tick, kan vi ikke afvise stilstand — og så må
        # dommen ikke være ACTIVE. Uden denne gren gav et ulæseligt
        # tidsstempel overdue=0 og dermed et falsk «alt er fint».
        mismatch.append("next_tick_at_unparseable")
    if active and str(scheduler_health or "") == "active" and iterations_count == 0 \
            and overdue > interval:
        mismatch.append("health_active_but_zero_iterations")
    stalled = active and overdue > 2 * interval
    if not active:
        verdict = "STOPPED"
    elif stalled:
        verdict = "STALLED"
    elif mismatch:
        verdict = "DEGRADED"
    elif str(scheduler_health or "") == "starting":
        verdict = "STARTING"
    else:
        verdict = "ACTIVE"
    return {
        "verdict": verdict,
        "mismatch": mismatch,
        "overdue_minutes": round(overdue, 1),
        "stall_threshold_minutes": 2 * interval,
        "thread_running": thread_running,
        "thread_observation": (
            "not_observed_in_this_process"
            if thread_running is None
            else "running" if thread_running else "not_running"
        ),
        "iterations": int(iterations_count) if iterations_count is not None else None,
        "newest_tick_started_at": newest.isoformat() if newest else None,
        "next_tick_at": str(next_tick_at or "") or None,
    }


# ── Selvhelbredende vagt ─────────────────────────────────────────────────────
# Kører på SIN EGEN dæmontråd, ikke i scheduler-tråden: en vagt der bor i det
# den overvåger dør sammen med det.
WATCHDOG_INTERVAL_SECONDS = 300
_WATCHDOG_STOP = threading.Event()
_WATCHDOG_THREAD: threading.Thread | None = None
_WATCHDOG_LAST_ITER: int | None = None


def watchdog_check(*, now=None) -> dict[str, object]:
    """Én kontrol. Genstarter kun hvis STALLED OG iterations() ikke er steget
    siden forrige kontrol (første kontrol sætter kun baseline)."""
    global _WATCHDOG_LAST_ITER
    from core.services import heartbeat_runtime as hb

    current = iterations()
    previous = _WATCHDOG_LAST_ITER
    _WATCHDOG_LAST_ITER = current
    state = hb.get_heartbeat_runtime_state() or {}
    assessment = assess_liveness(
        scheduler_active=state.get("scheduler_active"),
        scheduler_health=state.get("scheduler_health"),
        next_tick_at=state.get("next_tick_at"),
        last_tick_at=state.get("last_tick_at"),
        interval_minutes=state.get("interval_minutes"),
        thread_running=is_running(),
        iterations_count=current,
        now=now,
    )
    if assessment["verdict"] != "STALLED" or previous is None or current > previous:
        return {"restarted": False, **assessment}
    message = (
        f"heartbeat stalled: next_tick_at={assessment['next_tick_at']} overskredet "
        f"{assessment['overdue_minutes']} min (>{assessment['stall_threshold_minutes']}), "
        f"iterations={current} uændret, thread_running={assessment['thread_running']} "
        f"— genstarter dæmonen"
    )
    logger.error("HEARTBEAT-WATCHDOG: %s", message)
    try:
        from core.runtime.db_central_incidents import record_central_incident

        record_central_incident(
            cluster="heartbeat", nerve="scheduler", kind="scheduler_stalled",
            severity="error", message=message,
        )
    except Exception:
        logger.warning("HEARTBEAT-WATCHDOG: incident kunne ikke skrives", exc_info=True)
    stop()
    start()
    _WATCHDOG_LAST_ITER = None
    return {"restarted": True, **assessment}


def _watchdog_loop() -> None:
    while not _WATCHDOG_STOP.wait(WATCHDOG_INTERVAL_SECONDS):
        try:
            watchdog_check()
        except Exception:
            logger.exception("heartbeat watchdog check failed")


def start_watchdog() -> None:
    """Idempotent. Stoppes ikke af stop() — et bevidst stop sætter
    scheduler_active=False, og så rører vagten ikke ved noget."""
    global _WATCHDOG_THREAD
    if _WATCHDOG_THREAD and _WATCHDOG_THREAD.is_alive():
        return
    _WATCHDOG_STOP.clear()
    _WATCHDOG_THREAD = threading.Thread(
        target=_watchdog_loop, name="jarvis-heartbeat-watchdog", daemon=True
    )
    _WATCHDOG_THREAD.start()


def stop_watchdog() -> None:
    global _WATCHDOG_THREAD
    _WATCHDOG_STOP.set()
    _WATCHDOG_THREAD = None


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

    # Først NU har tråden gennemført sin første iteration — først nu må
    # helbredet hedde "active". start() skriver kun "starting" (se
    # heartbeat_runtime._prepare_scheduler_startup).
    try:
        hb._mark_scheduler_health(name=name, health="active")
    except Exception:
        logger.warning("heartbeat scheduler: kunne ikke sætte health=active", exc_info=True)

    while not _STOP.wait(INTERVAL_SECONDS):
        _ITERATION += 1
        try:
            # INFO, ikke debug. Se modulets docstring: uden dette tal kan en
            # tavs tråd ikke skelnes fra en tråd der kører uden at udrette
            # noget — og den forskel afgør hvor man skal lede.
            #
            # Tælleren alene var ikke nok. Natten 2.-3. sept. viste den at
            # løkken kørte 1011 gange på ni timer (~32 s pr. gennemløb, altså
            # sund) mens kun FEM slag faldt — og /mc/heartbeat svarede samtidig
            # `due: true`. Så spørgsmålet flyttede sig: hvad ser TRÅDEN?
            #
            # Derfor logges nu trådens EGEN beregning ved siden af tælleren.
            # Den koster en ekstra cheap-path-beregning pr. gennemløb; det er
            # en midlertidig pris for at kunne sammenligne trådens billede med
            # det en HTTP-forespørgsel får, i stedet for at gætte på forskellen.
            seen = {}
            try:
                seen = hb._cheap_heartbeat_schedule_state(name) or {}
            except Exception as diag_exc:
                seen = {"fejl": f"{type(diag_exc).__name__}: {diag_exc}"}
            logger.info(
                "HEARTBEAT-LOOP: iteration=%s name=%s due=%s schedule=%s interval=%s next=%s",
                _ITERATION,
                name,
                seen.get("due"),
                seen.get("schedule_state"),
                seen.get("interval_minutes"),
                seen.get("next_tick_at"),
            )
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
