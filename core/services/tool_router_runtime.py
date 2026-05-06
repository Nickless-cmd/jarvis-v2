"""Nightly daemon: refresh always-core ranking, recompute embeddings,
adjust adaptive threshold, write daemon-run summary event."""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_THREAD: Optional[threading.Thread] = None
_STOP = threading.Event()
_INTERVAL_S = 6 * 3600  # ~6h between runs; daemon idempotent so over-frequent is fine


def _adjust_threshold(*, current: float, load_more_rate_7d: float) -> float:
    if load_more_rate_7d > 0.15:
        new_val = current + 0.05
    elif load_more_rate_7d < 0.05:
        new_val = current - 0.03
    else:
        new_val = current
    return max(0.30, min(0.85, new_val))


def _read_load_more_rate() -> float:
    from core.services.tool_router import _load_more_rate_7d
    return _load_more_rate_7d()


def run_once() -> dict:
    """Single daemon iteration. Safe to call manually for testing."""
    summary: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())}
    try:
        from core.services.tool_embeddings import warmup_all
        n = warmup_all()
        summary["embeddings_warmed"] = n
    except Exception as exc:
        summary["embeddings_error"] = str(exc)

    try:
        rate = _read_load_more_rate()
        from core.runtime.settings import RuntimeSettings
        s = RuntimeSettings()
        new_t = _adjust_threshold(current=s.tool_router_threshold, load_more_rate_7d=rate)
        summary["load_more_rate_7d"] = rate
        summary["threshold_proposed"] = new_t
        summary["threshold_current"] = s.tool_router_threshold
    except Exception as exc:
        summary["adjust_error"] = str(exc)

    try:
        event_bus.publish("tool_router.daemon_run", summary)
    except Exception:
        pass

    summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    return summary


def _loop() -> None:
    while not _STOP.is_set():
        try:
            run_once()
        except Exception as exc:
            logger.warning("tool_router_runtime loop error: %s", exc)
        _STOP.wait(_INTERVAL_S)


def start_tool_router_runtime() -> None:
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(
        target=_loop, name="tool-router-runtime", daemon=True,
    )
    _THREAD.start()
    logger.info("tool_router_runtime daemon started")


def stop_tool_router_runtime() -> None:
    _STOP.set()
