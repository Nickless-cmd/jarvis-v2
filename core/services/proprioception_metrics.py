"""Proprioception Metrics — process-level body sense.

Jarvis' plan #3 (PLAN_PROPRIOCEPTION.md, 2026-04-20). Named
proprioception_metrics to avoid collision with existing somatic_daemon.py
(which generates LLM body-state phrasings — a different layer).

This daemon tracks his own process: RSS, CPU, FDs, uptime, self-measured
latency. Emits events when something shifts meaningfully:
- proprioception.memory_pressure_rising when RSS jumps >10% in one tick
- proprioception.response_slow when measured latency > 5s
- proprioception.fd_leak_suspected when open_fds > 500
"""
from __future__ import annotations

import logging
import os
import time
from collections import deque
from datetime import UTC, datetime
from typing import Any, Deque

logger = logging.getLogger(__name__)

_HISTORY_MAX = 100
_history: Deque[dict[str, Any]] = deque(maxlen=_HISTORY_MAX)

_RSS_JUMP_PCT = 10.0   # % increase in one tick → event
_LATENCY_SLOW_MS = 5000
_FD_LEAK_THRESHOLD = 500


def _psutil():
    try:
        import psutil
        return psutil
    except Exception:
        return None


def _current_snapshot() -> dict[str, Any]:
    """Sample current process stats."""
    psutil = _psutil()
    if psutil is None:
        return {"available": False}
    try:
        p = psutil.Process(os.getpid())
        with p.oneshot():
            mem = p.memory_info()
            cpu = p.cpu_percent(interval=None)
            try:
                open_fds = p.num_fds() if hasattr(p, "num_fds") else len(p.open_files())
            except Exception:
                open_fds = None
            create_time = p.create_time()
        rss_mb = round(mem.rss / (1024 * 1024), 2)
        return {
            "available": True,
            "at": datetime.now(UTC).isoformat(),
            "pid": os.getpid(),
            "rss_mb": rss_mb,
            "cpu_pct": round(float(cpu), 1),
            "open_fds": int(open_fds) if open_fds is not None else None,
            "uptime_seconds": int(time.time() - create_time),
        }
    except Exception as exc:
        logger.debug("proprioception_metrics.snapshot failed: %s", exc)
        return {"available": False}


def _measure_self_latency_ms() -> float | None:
    """Measure trivial self-dispatch as a crude latency proxy."""
    try:
        start = time.perf_counter()
        x = 0
        for i in range(1000):
            x += i
        end = time.perf_counter()
        return round((end - start) * 1000, 3)
    except Exception:
        return None


def _emit(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({"kind": kind, "payload": payload})
    except Exception:
        pass


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    snap = _current_snapshot()
    if not snap.get("available"):
        return {"available": False}

    latency = _measure_self_latency_ms()
    snap["self_latency_ms"] = latency

    prev = _history[0] if _history else None
    if prev and "rss_mb" in prev and prev["rss_mb"] > 0:
        rss_delta_pct = round(
            ((snap["rss_mb"] - prev["rss_mb"]) / prev["rss_mb"]) * 100, 2
        )
        snap["rss_delta_pct"] = rss_delta_pct
        if rss_delta_pct > _RSS_JUMP_PCT:
            _emit("proprioception.memory_pressure_rising", {
                "rss_mb": snap["rss_mb"],
                "delta_pct": rss_delta_pct,
                "at": snap["at"],
            })

    if latency is not None and latency > _LATENCY_SLOW_MS:
        _emit("proprioception.response_slow", {
            "latency_ms": latency,
            "at": snap["at"],
        })

    fds = snap.get("open_fds")
    if isinstance(fds, int) and fds > _FD_LEAK_THRESHOLD:
        _emit("proprioception.fd_leak_suspected", {
            "open_fds": fds,
            "at": snap["at"],
        })

    _history.appendleft(snap)
    return {
        "rss_mb": snap.get("rss_mb"),
        "cpu_pct": snap.get("cpu_pct"),
        "open_fds": snap.get("open_fds"),
        "self_latency_ms": latency,
    }


def recent_snapshots(*, limit: int = 20) -> list[dict[str, Any]]:
    return list(_history)[:limit]


def build_proprioception_metrics_surface() -> dict[str, Any]:
    current = _history[0] if _history else None
    if not current:
        snap = _current_snapshot()
        if not snap.get("available"):
            return {
                "active": False,
                "summary": "Proprioception mangler psutil",
            }
        snap["self_latency_ms"] = _measure_self_latency_ms()
        _history.appendleft(snap)
        current = snap
    rss_values = [s.get("rss_mb") for s in _history if isinstance(s.get("rss_mb"), (int, float))]
    rss_trend = None
    if len(rss_values) >= 5:
        recent = sum(rss_values[:5]) / 5
        older = sum(rss_values[-5:]) / 5
        rss_trend = round(recent - older, 2)
    return {
        "active": True,
        "current": {
            "rss_mb": current.get("rss_mb"),
            "cpu_pct": current.get("cpu_pct"),
            "open_fds": current.get("open_fds"),
            "uptime_seconds": current.get("uptime_seconds"),
            "self_latency_ms": current.get("self_latency_ms"),
        },
        "rss_trend_mb_over_window": rss_trend,
        "history_len": len(_history),
        "summary": _surface_summary(current, rss_trend),
    }


def _surface_summary(current: dict[str, Any], rss_trend: float | None) -> str:
    parts: list[str] = []
    if current.get("rss_mb") is not None:
        parts.append(f"RSS={current['rss_mb']}MB")
    if current.get("cpu_pct") is not None:
        parts.append(f"CPU={current['cpu_pct']}%")
    if current.get("open_fds") is not None:
        parts.append(f"fds={current['open_fds']}")
    if current.get("self_latency_ms") is not None:
        parts.append(f"latency={current['self_latency_ms']}ms")
    base = " ".join(parts)
    if rss_trend is not None:
        base += f" (RSS-trend={rss_trend:+}MB)"
    return base


def build_proprioception_metrics_prompt_section() -> str | None:
    """Only surfaces when something is actively worth noticing."""
    current = _history[0] if _history else None
    if not current:
        return None
    warnings: list[str] = []
    if isinstance(current.get("rss_delta_pct"), (int, float)):
        if current["rss_delta_pct"] > _RSS_JUMP_PCT:
            warnings.append(f"RSS steg {current['rss_delta_pct']}% på ét tick")
    if isinstance(current.get("self_latency_ms"), (int, float)):
        if current["self_latency_ms"] > _LATENCY_SLOW_MS:
            warnings.append(f"respons-latency {current['self_latency_ms']}ms")
    if isinstance(current.get("open_fds"), int):
        if current["open_fds"] > _FD_LEAK_THRESHOLD:
            warnings.append(f"{current['open_fds']} åbne fds")
    if not warnings:
        return None
    return "Somatisk: " + "; ".join(warnings) + "."


def reset_proprioception_metrics() -> None:
    _history.clear()
