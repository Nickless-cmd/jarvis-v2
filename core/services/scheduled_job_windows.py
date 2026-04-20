"""Scheduled Job Windows — time-window batch scheduling with provider preferences.

Ported from jarvis-ai (2026-03): define a window (start_hour, end_hour) in
local time during which batch-friendly jobs may run, with ordered provider
preferences (e.g., prefer_free_first for overnight work). Scheduler checks
each tick whether now() is inside a window and enqueues a batch job if not
already queued for that window-day.

Storage: JSON file. Per-tick scheduler: `tick_windows()` checks windows and
calls a callback for each (window, key) pair that should fire. Caller supplies
the callback — this module doesn't execute anything, only *marks* windows
due. Deduplication via `(window_id, day_key)` ensures one fire per window
per day.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/scheduled_windows.json"


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"windows": [], "fire_history": []}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("windows", [])
            data.setdefault("fire_history", [])
            return data
    except Exception as exc:
        logger.warning("scheduled_job_windows: load failed: %s", exc)
    return {"windows": [], "fire_history": []}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("scheduled_job_windows: save failed: %s", exc)


def register_window(
    *,
    name: str,
    start_hour: int,
    end_hour: int,
    max_requests: int = 100,
    allowed_providers: list[str] | None = None,
    prefer_free_first: bool = False,
    active: bool = True,
) -> str:
    """Register a scheduled window. Hours in local time.

    start_hour in [0, 23]. end_hour in [1, 24]. Wraparound is supported:
    if end_hour <= start_hour, the window spans midnight (e.g., 22→6).
    """
    if not (0 <= int(start_hour) <= 23):
        raise ValueError("start_hour must be in [0, 23]")
    if not (1 <= int(end_hour) <= 24):
        raise ValueError("end_hour must be in [1, 24]")
    if int(end_hour) == int(start_hour):
        raise ValueError("end_hour must differ from start_hour")
    data = _load()
    window_id = f"win-{uuid4().hex[:12]}"
    data["windows"].append({
        "window_id": window_id,
        "name": str(name)[:80],
        "start_hour": int(start_hour),
        "end_hour": int(end_hour),
        "max_requests": int(max_requests),
        "allowed_providers": list(allowed_providers or []),
        "prefer_free_first": bool(prefer_free_first),
        "active": bool(active),
        "created_at": datetime.now(UTC).isoformat(),
    })
    _save(data)
    return window_id


def set_window_active(window_id: str, active: bool) -> bool:
    data = _load()
    for w in data["windows"]:
        if w.get("window_id") == window_id:
            w["active"] = bool(active)
            _save(data)
            return True
    return False


def is_inside_window(now: datetime, start_hour: int, end_hour: int) -> bool:
    """Supports wraparound (end_hour <= start_hour means crosses midnight)."""
    hour = int(now.hour)
    start = int(start_hour)
    end = int(end_hour)
    if end > start:
        return start <= hour < end
    # Wraparound: inside if hour >= start OR hour < end
    return hour >= start or hour < end


def current_window_day_key(now: datetime, start_hour: int) -> str:
    """Generate a unique key for (window, day) — e.g., '2026-04-20-22'.

    For wraparound windows, the hours after midnight share the key of the
    previous day's window. E.g., a 22→6 window running at 02:00 2026-04-21
    uses key '2026-04-20-22'.
    """
    hour = int(now.hour)
    start = int(start_hour)
    # If we're in the post-midnight portion of a wraparound window,
    # attribute to the previous day's window start.
    if hour < start:
        prev = now.date() - timedelta(days=1)
        return f"{prev.isoformat()}-{start:02d}"
    return f"{now.date().isoformat()}-{start:02d}"


def _already_fired(history: list[dict[str, Any]], window_id: str, day_key: str) -> bool:
    for h in history[-200:]:  # check recent history only
        if h.get("window_id") == window_id and h.get("day_key") == day_key:
            return True
    return False


def tick_windows(
    *,
    now: datetime | None = None,
    callback: Callable[[dict[str, Any], str], None] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate all windows. For each window currently inside and not-yet-fired
    today, record a fire event and optionally invoke callback(window, day_key).

    Returns list of fire events created.
    """
    now_dt = now or datetime.now(UTC).astimezone()
    data = _load()
    fires: list[dict[str, Any]] = []
    for w in data["windows"]:
        if not w.get("active", True):
            continue
        if not is_inside_window(now_dt, w["start_hour"], w["end_hour"]):
            continue
        day_key = current_window_day_key(now_dt, w["start_hour"])
        if _already_fired(data["fire_history"], w["window_id"], day_key):
            continue
        fire = {
            "fire_id": f"fire-{uuid4().hex[:10]}",
            "window_id": w["window_id"],
            "window_name": w.get("name"),
            "day_key": day_key,
            "fired_at": datetime.now(UTC).isoformat(),
            "max_requests": w.get("max_requests"),
            "allowed_providers": w.get("allowed_providers"),
            "prefer_free_first": w.get("prefer_free_first", False),
        }
        data["fire_history"].append(fire)
        fires.append(fire)
        if callback is not None:
            try:
                callback(w, day_key)
            except Exception as exc:
                logger.debug("scheduled_job_windows callback failed: %s", exc)
    # Cap history
    if len(data["fire_history"]) > 1000:
        data["fire_history"] = data["fire_history"][-1000:]
    if fires:
        _save(data)
    return fires


def list_windows() -> list[dict[str, Any]]:
    return list(_load()["windows"])


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook — evaluates windows, no-op when not inside any."""
    fires = tick_windows()
    return {"fires": len(fires)}


def build_scheduled_job_windows_surface() -> dict[str, Any]:
    data = _load()
    windows = data["windows"]
    history = data["fire_history"]
    now = datetime.now(UTC).astimezone()
    active_now: list[str] = []
    for w in windows:
        if w.get("active", True) and is_inside_window(now, w["start_hour"], w["end_hour"]):
            active_now.append(w.get("name") or w["window_id"])
    recent = history[-5:] if history else []
    return {
        "active": len(windows) > 0,
        "total_windows": len(windows),
        "active_windows": [w for w in windows if w.get("active", True)],
        "inside_window_now": active_now,
        "fires_today": sum(
            1 for h in history
            if str(h.get("fired_at", ""))[:10] == now.date().isoformat()
        ),
        "recent_fires": recent,
        "summary": _surface_summary(windows, active_now, history),
    }


def _surface_summary(
    windows: list[dict[str, Any]],
    active_now: list[str],
    history: list[dict[str, Any]],
) -> str:
    if not windows:
        return "Ingen job-vinduer registreret"
    if active_now:
        return f"Inde i vindue: {', '.join(active_now)} ({len(windows)} registreret)"
    return f"{len(windows)} vinduer registreret, ingen aktiv lige nu"
