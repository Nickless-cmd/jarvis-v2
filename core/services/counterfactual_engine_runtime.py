"""Daemon for periodic counterfactual reflection cycles.

Cadence: 60 minutes between cycles by default (overridable via setting).
Per-workspace advisory lock prevents overlapping cycles for the same
workspace. Phase 1 only processes the 'default' workspace.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_THREAD: Optional[threading.Thread] = None
_STOP = threading.Event()
_INTERVAL_S = 60 * 60  # 1h default
_WORKSPACE_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_LOCK = threading.Lock()  # protects _WORKSPACE_LOCKS dict mutation


def _get_workspace_lock(workspace_id: str) -> threading.Lock:
    """Lazy per-workspace lock. Same workspace_id always returns same Lock."""
    with _LOCKS_LOCK:
        lock = _WORKSPACE_LOCKS.get(workspace_id)
        if lock is None:
            lock = threading.Lock()
            _WORKSPACE_LOCKS[workspace_id] = lock
    return lock


def _run_one_cycle(workspace_id: str) -> dict:
    """Acquire workspace lock, run engine, release. Never raises."""
    lock = _get_workspace_lock(workspace_id)
    if not lock.acquire(blocking=False):
        logger.info(
            "counterfactual_runtime: skipping %s — lock held by another cycle",
            workspace_id,
        )
        return {
            "workspace_id": workspace_id,
            "skipped": True,
            "skipped_reason": "lock-held",
        }
    try:
        from core.services import counterfactual_engine as engine
        return engine.run(workspace_id=workspace_id)
    except Exception as exc:
        logger.warning(
            "counterfactual_runtime: engine.run failed for %s: %s",
            workspace_id, exc,
        )
        return {
            "workspace_id": workspace_id,
            "error": f"engine-error: {type(exc).__name__}",
        }
    finally:
        lock.release()


def _list_active_workspaces() -> list[str]:
    """Phase 1: only the default workspace.

    Phase 2+ may iterate over filesystem workspaces or registered users.
    """
    return ["default"]


def _loop() -> None:
    while not _STOP.is_set():
        try:
            for ws in _list_active_workspaces():
                _run_one_cycle(ws)
        except Exception as exc:
            logger.warning("counterfactual_runtime: outer loop error: %s", exc)
        _STOP.wait(_INTERVAL_S)


def start_counterfactual_runtime() -> None:
    """Start the periodic-evaluation daemon. Idempotent — safe to call multiple times."""
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(
        target=_loop, name="counterfactual-runtime", daemon=True,
    )
    _THREAD.start()
    logger.info("counterfactual_runtime daemon started")


def stop_counterfactual_runtime() -> None:
    """Signal the loop to exit."""
    _STOP.set()
