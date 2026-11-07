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


def build_tool_router_runtime_surface() -> dict:
    """Mission Control-surface: koerer router-daemonen, og hvad sagde dens sidste kørsel?

    READ-ONLY. To ting der ellers er usynlige: load-more-raten (som
    `_load_more_rate_7d` returnerer som 0.0 ved enhver fejl) og at daemonen kun
    FORESLAAR en ny taerskel — `run_once` anvender den aldrig.
    """
    base = {"mode": "tool-router-runtime"}
    daemon = {"thread_alive": bool(_THREAD is not None and _THREAD.is_alive()),
              "interval_seconds": _INTERVAL_S}
    try:
        from core.runtime.db import connect
        with connect() as conn:
            have = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('tool_router_decisions','tool_router_load_more')").fetchall()}
            if have != {"tool_router_decisions", "tool_router_load_more"}:
                return {**base, "active": False,
                        "reason": "router-tabellerne findes ikke: mangler " + ", ".join(
                            sorted({"tool_router_decisions", "tool_router_load_more"} - have)),
                        "signals": {"daemon": daemon}, "summary": "ingen routerdata at maale paa"}
            decisions = int(conn.execute(
                "SELECT COUNT(*) FROM tool_router_decisions WHERE created_at >= datetime('now','-7 days')"
            ).fetchone()[0])
            more = int(conn.execute(
                "SELECT COUNT(*) FROM tool_router_load_more WHERE created_at >= datetime('now','-7 days')"
            ).fetchone()[0])
        from core.eventbus.bus import event_bus
        runs = [e for e in (event_bus.recent_by_family("tool_router", limit=50) or [])
                if e.get("kind") == "tool_router.daemon_run"]
    except Exception as exc:  # surface skal melde aarsagen, ikke kaste ind i MC
        return {**base, "active": False, "reason": f"{type(exc).__name__}: {exc}"[:300],
                "signals": {"daemon": daemon}, "summary": "router-kilder ulaeselige"}
    rate = (more / decisions) if decisions else None
    last = (runs[0].get("payload") or {}) if runs else {}
    return {
        **base, "active": bool(daemon["thread_alive"] or runs or decisions),
        **({} if (daemon["thread_alive"] or runs or decisions) else
           {"reason": "daemonen koerer ikke og der er hverken kørsler eller beslutninger"}),
        "signals": {"daemon": daemon, "decisions_7d": decisions, "load_more_7d": more,
                    "load_more_rate_7d": round(rate, 4) if rate is not None else None,
                    "recorded_runs": len(runs),
                    "last_run": {k: last.get(k) for k in (
                        "started_at", "finished_at", "embeddings_warmed", "load_more_rate_7d",
                        "threshold_current", "threshold_proposed", "embeddings_error", "adjust_error")
                        if k in last} or None,
                    "threshold_applied_by_daemon": False},
        "summary": (f"tråd {'oppe' if daemon['thread_alive'] else 'nede'}; {decisions} beslutninger/7d, "
                    f"load-more {round(rate, 3) if rate is not None else 'ukendt'}; {len(runs)} kørsler i bussen"),
    }
