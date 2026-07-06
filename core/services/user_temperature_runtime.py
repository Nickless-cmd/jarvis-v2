"""Daemon for the user-temperature LLM stream (Lag 10).

Two timing rhythms in one loop:
- Every _TRIGGER_CHECK_S (60s): check if any workspace has pending trigger
- Every user_temperature_llm_cadence_hours (4h): force-run all workspaces

Per-workspace lock prevents overlapping cycles. Mirrors patterns from
forgetting_runtime and counterfactual_engine_runtime.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_THREAD: Optional[threading.Thread] = None
_STOP = threading.Event()
_TRIGGER_CHECK_S = 60  # how often to poll trigger flag
_WORKSPACE_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_LOCK = threading.Lock()


def _get_workspace_lock(workspace_id: str) -> threading.Lock:
    with _LOCKS_LOCK:
        lock = _WORKSPACE_LOCKS.get(workspace_id)
        if lock is None:
            lock = threading.Lock()
            _WORKSPACE_LOCKS[workspace_id] = lock
    return lock


def _run_one_cycle(workspace_id: str, *, force: bool = False) -> dict:
    """Acquire workspace lock, run LLM stream. Never raises."""
    lock = _get_workspace_lock(workspace_id)
    if not lock.acquire(blocking=False):
        return {"skipped": True, "reason": "lock-held"}
    try:
        from core.services import user_temperature_engine
        return user_temperature_engine.run_llm_stream(
            workspace_id=workspace_id, force=force,
        )
    except Exception as exc:
        logger.warning("user_temperature_runtime: cycle failed: %s", exc)
        return {"error": f"engine-error: {type(exc).__name__}"}
    finally:
        lock.release()


def _list_active_workspaces() -> list[str]:
    return ["default"]


def _resolve_periodic_interval_seconds() -> int:
    try:
        from core.runtime.settings import load_settings
        hours = load_settings().user_temperature_llm_cadence_hours
        return max(60, int(hours) * 3600)
    except Exception:
        return 4 * 3600


def _loop() -> None:
    """Two rhythms in one loop:
    - Every _TRIGGER_CHECK_S: check trigger flag per workspace
    - Every periodic interval: force-run all workspaces
    """
    last_periodic_at = 0.0
    while not _STOP.is_set():
        try:
            now_t = time.time()
            interval = _resolve_periodic_interval_seconds()
            for ws in _list_active_workspaces():
                if (now_t - last_periodic_at) >= interval:
                    _run_one_cycle(ws, force=True)
                    last_periodic_at = now_t
                    continue
                from core.services.user_temperature_engine import _has_pending_trigger
                if _has_pending_trigger(workspace_id=ws):
                    _run_one_cycle(ws, force=False)
        except Exception as exc:
            logger.warning("user_temperature_runtime loop error: %s", exc)
        _STOP.wait(_TRIGGER_CHECK_S)


def start_user_temperature_runtime() -> None:
    """Start the daemon. Idempotent."""
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(
        target=_loop, name="user-temperature-runtime", daemon=True,
    )
    _THREAD.start()
    logger.info("user_temperature_runtime daemon started")


def stop_user_temperature_runtime() -> None:
    _STOP.set()


