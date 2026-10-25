"""Cross-process reservation for unattended run starts.

The reservation closes the check/start race between inbox wakeups and idle
side tasks.  It is an OS flock, so a crashed process releases it automatically;
no stale lease row can strand the scheduler.  Active-run sensors are evaluated
while the lock is held and fail closed.
"""
from __future__ import annotations

import fcntl
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from core.runtime import state_store

logger = logging.getLogger(__name__)

_LOCK_KEY = "background_session_start"


@dataclass(frozen=True)
class StartReservation:
    acquired: bool
    reason: str = ""


def _active_reason(session_id: str) -> str:
    """Return an active-run reason; raise when a sensor cannot be trusted."""
    from core.services import in_flight_runs, run_event_log

    local_run = str(run_event_log.active_run_for_session(session_id) or "")
    if local_run:
        return f"local-active:{local_run[:24]}"
    shared = in_flight_runs.levende_koersler(session_id=session_id)
    if shared:
        run_id = str(shared[0].get("run_id") or "")
        return f"shared-active:{run_id[:24]}"
    return ""


@contextmanager
def reserve_background_start(session_id: str) -> Iterator[StartReservation]:
    """Reserve the shared check/start section, or yield a refusal reason.

    The global lock is intentionally held only across synchronous run startup.
    Runs in different sessions may execute concurrently after registration.
    """
    sid = str(session_id or "").strip()
    if not sid:
        yield StartReservation(False, "no-session")
        return

    path = state_store._path(_LOCK_KEY).with_suffix(".lock")
    handle = None
    locked = False
    result = StartReservation(False, "reservation-unavailable")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except BlockingIOError:
            result = StartReservation(False, "start-reserved")
        if locked:
            try:
                active = _active_reason(sid)
            except Exception as exc:  # sensor failure must block an unattended start
                logger.warning(
                    "background start: active-run sensor failed for %s: %s",
                    sid[:28], exc,
                )
                result = StartReservation(False, "active-state-unavailable")
            else:
                result = StartReservation(False, active) if active else StartReservation(True)
    except Exception as exc:  # lock failure must block an unattended start
        logger.warning("background start: reservation failed for %s: %s", sid[:28], exc)
        result = StartReservation(False, "reservation-unavailable")

    try:
        yield result
    finally:
        if locked and handle is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except Exception:  # closing the descriptor also releases the OS lock
                pass
        if handle is not None:
            handle.close()


__all__ = ["StartReservation", "reserve_background_start"]
