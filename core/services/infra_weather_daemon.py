"""Infra Weather Daemon — "The atmosphere of my system".

Jarvis' PLAN_WILD_IDEAS #8 (2026-04-20): sense whether the system is well
like feeling air pressure before a storm. Combines load, disk, network,
API cost, and process health into a single weather report.

Recomputes every 5 minutes (heartbeat-gated). Emits critical-weather
events when thresholds cross.
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_RECOMPUTE_SECONDS = 5 * 60
_CRITICAL_COOLDOWN_MINUTES = 30  # don't spam critical alerts

_last_state: dict[str, Any] = {}
_last_computed_ts: float = 0.0
_last_critical_alert_ts: float | None = None

_DISK_PATHS = ("/", "/media/projects")
_DISK_WARN_PCT = 85.0
_DISK_CRITICAL_PCT = 95.0
_LOAD_WARN = 0.75
_LOAD_CRITICAL = 0.92
_API_COST_WARN_USD = 5.0
_API_COST_CRITICAL_USD = 15.0


def _psutil():
    try:
        import psutil
        return psutil
    except Exception:
        return None


def _system_load() -> dict[str, float]:
    psu = _psutil()
    if psu is None:
        return {}
    try:
        cpu = float(psu.cpu_percent(interval=None))
        vm = psu.virtual_memory()
        ram_pct = float(vm.percent)
        # Normalized load (0..1) weighted toward whichever is higher
        load = max(cpu, ram_pct) / 100.0
        return {"cpu_pct": cpu, "ram_pct": ram_pct, "load_0_1": round(load, 3)}
    except Exception:
        return {}


def _disk_pressure() -> dict[str, Any]:
    worst_pct = 0.0
    per_path: dict[str, dict[str, float]] = {}
    for path in _DISK_PATHS:
        if not os.path.exists(path):
            continue
        try:
            du = shutil.disk_usage(path)
            used_pct = round(((du.total - du.free) / du.total) * 100, 2) if du.total > 0 else 0.0
            per_path[path] = {
                "total_gb": round(du.total / (1024**3), 2),
                "free_gb": round(du.free / (1024**3), 2),
                "used_pct": used_pct,
            }
            worst_pct = max(worst_pct, used_pct)
        except Exception:
            continue
    return {"per_path": per_path, "worst_used_pct": worst_pct}


def _network_latency() -> dict[str, Any]:
    """Lightweight network health check.

    Tests reachability to Ollama (internal) and checks for recent
    network-related errors in the eventbus. No external pings —
    stays within known infrastructure.
    """
    result: dict[str, Any] = {"status": "unknown", "ollama_ms": None, "errors_recent": 0}

    # 1) Internal: ping Ollama (known endpoint)
    try:
        import socket
        ollama_host = os.environ.get("OLLAMA_HOST", "10.0.0.25")
        ollama_port = int(os.environ.get("OLLAMA_PORT", "11434"))
        start = datetime.now(UTC).timestamp()
        sock = socket.create_connection((ollama_host, ollama_port), timeout=2.0)
        elapsed_ms = round((datetime.now(UTC).timestamp() - start) * 1000, 1)
        sock.close()
        result["ollama_ms"] = elapsed_ms
        result["status"] = "ok" if elapsed_ms < 100 else "slow"
    except Exception:
        result["status"] = "degraded"
        result["ollama_ms"] = None

    # 2) Recent network errors from eventbus
    try:
        from core.eventbus.bus import event_bus
        recent = list(event_bus.recent(limit=50, kind="runtime"))
        err_count = sum(
            1 for e in recent
            if isinstance(e, dict)
            and any(kw in str(e.get("kind", "")).lower() for kw in ("fail", "error", "timeout"))
            and any(kw in str(e.get("payload", "")).lower() for kw in ("network", "connect", "timeout", "dns"))
        )
        result["errors_recent"] = err_count
        if err_count > 3 and result["status"] == "ok":
            result["status"] = "unstable"
    except Exception:
        pass

    return result


def _api_cost_today() -> float:
    """Sum of today's API costs via the costs ledger."""
    try:
        from core.costing.ledger import telemetry_summary
        summary = telemetry_summary()
        return float(summary.get("total_cost_usd", 0.0))
    except Exception:
        pass
    # Fallback: direct DB query
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) AS total "
                "FROM costs WHERE date(created_at) = date('now')"
            ).fetchone()
            return float(row["total"] or 0.0)
    except Exception:
        return 0.0


def _process_health() -> dict[str, Any]:
    """Check some expected child processes / threads are alive."""
    psu = _psutil()
    if psu is None:
        return {"available": False}
    try:
        proc = psu.Process(os.getpid())
        threads = proc.num_threads()
        children = len(proc.children())
        return {
            "available": True,
            "main_pid": os.getpid(),
            "threads": int(threads),
            "children": int(children),
        }
    except Exception:
        return {"available": False}


def _weather_label(load: float, disk_pct: float, cost: float) -> tuple[str, str]:
    """Return (label, emoji) — ☀️ clear, 🌧 under pressure, ⛈ critical."""
    if (
        load >= _LOAD_CRITICAL
        or disk_pct >= _DISK_CRITICAL_PCT
        or cost >= _API_COST_CRITICAL_USD
    ):
        return "critical", "⛈"
    if (
        load >= _LOAD_WARN
        or disk_pct >= _DISK_WARN_PCT
        or cost >= _API_COST_WARN_USD
    ):
        return "under-pressure", "🌧"
    return "clear", "☀️"


def _compose_report() -> dict[str, Any]:
    load = _system_load()
    disk = _disk_pressure()
    net = _network_latency()
    cost = _api_cost_today()
    proc = _process_health()

    load_val = float(load.get("load_0_1") or 0.0)
    disk_pct = float(disk.get("worst_used_pct") or 0.0)
    label, emoji = _weather_label(load_val, disk_pct, cost)

    reasons: list[str] = []
    if load_val >= _LOAD_WARN:
        reasons.append(f"load={load_val}")
    if disk_pct >= _DISK_WARN_PCT:
        reasons.append(f"disk={disk_pct}%")
    if cost >= _API_COST_WARN_USD:
        reasons.append(f"api-cost=${cost:.2f}")

    return {
        "label": label,
        "emoji": emoji,
        "reasons": reasons,
        "load": load,
        "disk": disk,
        "network": net,
        "api_cost_today_usd": round(float(cost), 4),
        "process_health": proc,
        "computed_at": datetime.now(UTC).isoformat(),
    }


def _maybe_emit_critical(report: dict[str, Any]) -> None:
    global _last_critical_alert_ts
    if report.get("label") != "critical":
        return
    now_ts = datetime.now(UTC).timestamp()
    if _last_critical_alert_ts is not None:
        if (now_ts - _last_critical_alert_ts) < _CRITICAL_COOLDOWN_MINUTES * 60:
            return
    _last_critical_alert_ts = now_ts
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "infra_weather.critical",
            "payload": {
                "reasons": report.get("reasons"),
                "load_0_1": report.get("load", {}).get("load_0_1"),
                "disk_worst_pct": report.get("disk", {}).get("worst_used_pct"),
                "api_cost": report.get("api_cost_today_usd"),
                "at": report.get("computed_at"),
            },
        })
    except Exception:
        pass
    # ntfy alert
    try:
        from core.services.ntfy_gateway import send_notification
        msg = "⛈ System under kritisk pres: " + ", ".join(report.get("reasons") or [])
        send_notification(msg, title="Jarvis infra_weather", priority="high")
    except Exception:
        pass


def get_weather() -> dict[str, Any]:
    global _last_state, _last_computed_ts
    now_ts = datetime.now(UTC).timestamp()
    if not _last_state or (now_ts - _last_computed_ts) > _RECOMPUTE_SECONDS:
        _last_state = _compose_report()
        _last_computed_ts = now_ts
        _maybe_emit_critical(_last_state)
    return dict(_last_state)


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    return {"label": get_weather().get("label")}


def build_infra_weather_surface() -> dict[str, Any]:
    r = get_weather()
    return {
        "active": True,
        "label": r.get("label"),
        "emoji": r.get("emoji"),
        "reasons": r.get("reasons"),
        "load": r.get("load"),
        "disk": r.get("disk"),
        "api_cost_today_usd": r.get("api_cost_today_usd"),
        "process_health": r.get("process_health"),
        "computed_at": r.get("computed_at"),
        "summary": _surface_summary(r),
    }


def _surface_summary(r: dict[str, Any]) -> str:
    emoji = r.get("emoji", "")
    label = str(r.get("label") or "")
    reasons = r.get("reasons") or []
    if reasons:
        return f"{emoji} {label} ({', '.join(reasons)})"
    return f"{emoji} {label}"


def build_infra_weather_prompt_section() -> str | None:
    """Silent when clear. Speaks when pressure or critical."""
    r = get_weather()
    label = str(r.get("label") or "")
    if label == "clear":
        return None
    reasons = r.get("reasons") or []
    reason_str = ", ".join(reasons) if reasons else "ukendt pres"
    return f"Infra-vejr: {r.get('emoji','')} {label} — {reason_str}."
