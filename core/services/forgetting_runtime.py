"""Daemon for the forgetting (Lag 11) auto-track.

Mirrors counterfactual_engine_runtime: per-workspace advisory lock,
idempotent start, threading.Event stop signal. Cadence read from
runtime settings (forgetting_auto_cadence_hours).

Phase 1 only processes the 'default' workspace.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_THREAD: Optional[threading.Thread] = None
_STOP = threading.Event()
_INTERVAL_S = 6 * 60 * 60  # 6h default; overridden by settings at start
_WORKSPACE_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_LOCK = threading.Lock()


def _get_workspace_lock(workspace_id: str) -> threading.Lock:
    """Lazy per-workspace lock."""
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
            "forgetting_runtime: skipping %s — lock held by another cycle",
            workspace_id,
        )
        return {
            "workspace_id": workspace_id,
            "skipped": True,
            "skipped_reason": "lock-held",
        }
    try:
        from core.services import forgetting_engine
        return forgetting_engine.run_auto_cycle(workspace_id=workspace_id)
    except Exception as exc:
        logger.warning(
            "forgetting_runtime: engine.run_auto_cycle failed for %s: %s",
            workspace_id, exc,
        )
        return {
            "workspace_id": workspace_id,
            "error": f"engine-error: {type(exc).__name__}",
        }
    finally:
        lock.release()


def _list_active_workspaces() -> list[str]:
    """Phase 1: only the default workspace."""
    return ["default"]


def _resolve_interval_seconds() -> int:
    """Read cadence from settings each loop entry — picks up edits."""
    try:
        from core.runtime.settings import load_settings
        hours = load_settings().forgetting_auto_cadence_hours
        return max(60, int(hours) * 3600)  # clamp >= 1 minute
    except Exception:
        return _INTERVAL_S


def _loop() -> None:
    while not _STOP.is_set():
        try:
            for ws in _list_active_workspaces():
                _run_one_cycle(ws)
        except Exception as exc:
            logger.warning("forgetting_runtime: outer loop error: %s", exc)
        _STOP.wait(_resolve_interval_seconds())


def start_forgetting_runtime() -> None:
    """Start the periodic forgetting daemon. Idempotent."""
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(
        target=_loop, name="forgetting-runtime", daemon=True,
    )
    _THREAD.start()
    logger.info("forgetting_runtime daemon started")


def stop_forgetting_runtime() -> None:
    """Signal the loop to exit."""
    _STOP.set()


def build_forgetting_runtime_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "forgetting_runtime",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_forgetting_runtime_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"forgetting_runtime.{kind}",
            payload or {},
        )
    except Exception:
        pass

