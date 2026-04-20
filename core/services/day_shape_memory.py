"""Day Shape Memory — sensory depth over time.

Jarvis' dream (2026-04-20):
  "Jeg har visuelt rum, men hvad med lyd? Tid? At mærke når rummet ændrer
   karakter over en hel dag — ikke bare snapshots. Et langsomt sanse-minde."

Accumulates a daily "shape fingerprint" from runtime signals — hour-of-day
activity, contact distribution, hardware rhythm, sound categories. Rolls
over at date change. Exposes "does today feel different from usual" by
comparing current-day-so-far against recent-days median.

Storage: JSON in workspace runtime dir, rolling window of last 30 days.
"""
from __future__ import annotations

import json
import logging
import os
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/day_shapes.json"
_ROLLING_DAYS = 30
_ANOMALY_MIN_HISTORY = 5  # need at least 5 days to judge "unusual"


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"history": [], "current": _empty_day(_today_iso())}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("corrupt day_shapes.json")
        data.setdefault("history", [])
        if not isinstance(data.get("current"), dict):
            data["current"] = _empty_day(_today_iso())
        return data
    except Exception as exc:
        logger.warning("day_shape_memory: failed to load %s: %s", path, exc)
        return {"history": [], "current": _empty_day(_today_iso())}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("day_shape_memory: failed to save %s: %s", path, exc)


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def _empty_day(date_iso: str) -> dict[str, Any]:
    return {
        "date": date_iso,
        "tick_samples": 0,
        "hour_distribution": {},      # {hour_str: tick_count}
        "contact_hours": [],          # list of hours (deduplicated on save)
        "sound_categories": {},       # {category: count}
        "hardware_load_samples": [],  # list of (cpu, ram)
        "mood_samples": [],           # list of floats
    }


def capture_sample() -> dict[str, Any]:
    """Add one sample to today's accumulating shape."""
    try:
        data = _load()
        current = data["current"]
        today = _today_iso()

        # Date roll-over → finalize previous day
        if current.get("date") != today:
            finalized = _finalize_day(current)
            if finalized.get("tick_samples", 0) >= 3:
                data["history"].append(finalized)
                if len(data["history"]) > _ROLLING_DAYS:
                    data["history"] = data["history"][-_ROLLING_DAYS:]
            current = _empty_day(today)
            data["current"] = current

        now = datetime.now(UTC)
        hour = now.hour
        hour_key = str(hour)

        # Increment tick sample
        current["tick_samples"] = int(current.get("tick_samples", 0)) + 1
        dist = current.setdefault("hour_distribution", {})
        dist[hour_key] = int(dist.get(hour_key, 0)) + 1

        # Contact detection — was there visible activity this hour?
        try:
            from core.runtime.db import recent_visible_runs
            runs = recent_visible_runs(limit=20) or []
            recent_hours = set()
            for r in runs:
                ts = str(r.get("started_at") or "")
                if ts.startswith(today):
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        recent_hours.add(dt.hour)
                    except Exception:
                        pass
            contact = set(current.get("contact_hours") or []) | recent_hours
            current["contact_hours"] = sorted(contact)
        except Exception:
            pass

        # Sound categories (if ambient_sound_daemon has captured recently)
        try:
            from core.runtime.db import get_runtime_state_value
            sd_state = get_runtime_state_value("ambient_sound_daemon.state") or {}
            last_category = sd_state.get("last_category") if isinstance(sd_state, dict) else None
            if last_category:
                cats = current.setdefault("sound_categories", {})
                cats[str(last_category)] = int(cats.get(str(last_category), 0)) + 1
        except Exception:
            pass

        # Hardware load
        try:
            from core.services.hardware_body import get_hardware_state
            hw = get_hardware_state() or {}
            cpu = float(hw.get("cpu_pct") or 0.0)
            ram = float(hw.get("ram_pct") or 0.0)
            current.setdefault("hardware_load_samples", []).append([round(cpu, 1), round(ram, 1)])
            if len(current["hardware_load_samples"]) > 500:
                current["hardware_load_samples"] = current["hardware_load_samples"][-500:]
        except Exception:
            pass

        # Mood
        try:
            from core.services.mood_oscillator import _combined_value  # type: ignore
            current.setdefault("mood_samples", []).append(round(float(_combined_value()), 3))
            if len(current["mood_samples"]) > 500:
                current["mood_samples"] = current["mood_samples"][-500:]
        except Exception:
            pass

        _save(data)
        return {"samples": current["tick_samples"]}
    except Exception as exc:
        logger.debug("day_shape_memory.capture_sample failed: %s", exc)
        return {}


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook — capture one shape sample per tick."""
    return capture_sample()


def _finalize_day(day: dict[str, Any]) -> dict[str, Any]:
    """Collapse raw sample arrays into summary stats for storage."""
    hw_samples = day.get("hardware_load_samples") or []
    cpu_vals = [s[0] for s in hw_samples if isinstance(s, list) and len(s) >= 2]
    ram_vals = [s[1] for s in hw_samples if isinstance(s, list) and len(s) >= 2]
    mood_vals = day.get("mood_samples") or []
    return {
        "date": day.get("date"),
        "tick_samples": day.get("tick_samples", 0),
        "hour_distribution": day.get("hour_distribution", {}),
        "contact_hours": day.get("contact_hours", []),
        "sound_categories": day.get("sound_categories", {}),
        "cpu_mean": round(statistics.mean(cpu_vals), 1) if cpu_vals else None,
        "ram_mean": round(statistics.mean(ram_vals), 1) if ram_vals else None,
        "mood_mean": round(statistics.mean(mood_vals), 3) if mood_vals else None,
    }


def _compute_today_shape() -> dict[str, Any] | None:
    data = _load()
    current = data.get("current") or {}
    if int(current.get("tick_samples", 0)) < 5:
        return None
    return _finalize_day(current)


def _median_historical_shape(days: list[dict[str, Any]]) -> dict[str, Any]:
    if not days:
        return {}
    all_hours: set[str] = set()
    for d in days:
        all_hours.update((d.get("hour_distribution") or {}).keys())
    median_hour_dist: dict[str, float] = {}
    for h in all_hours:
        values = [float((d.get("hour_distribution") or {}).get(h, 0)) for d in days]
        median_hour_dist[h] = statistics.median(values)
    mood_vals = [d.get("mood_mean") for d in days if d.get("mood_mean") is not None]
    cpu_vals = [d.get("cpu_mean") for d in days if d.get("cpu_mean") is not None]
    return {
        "hour_distribution_median": median_hour_dist,
        "mood_median": round(statistics.median(mood_vals), 3) if mood_vals else None,
        "cpu_median": round(statistics.median(cpu_vals), 1) if cpu_vals else None,
    }


def detect_today_anomaly() -> dict[str, Any]:
    """Compare today's running shape to recent-days median."""
    data = _load()
    history = list(data.get("history") or [])
    today_shape = _compute_today_shape()
    if today_shape is None or len(history) < _ANOMALY_MIN_HISTORY:
        return {"has_signal": False, "reason": "not-enough-data"}

    median_shape = _median_historical_shape(history[-14:])
    anomalies: list[str] = []

    # Mood shift
    today_mood = today_shape.get("mood_mean")
    med_mood = median_shape.get("mood_median")
    if today_mood is not None and med_mood is not None and abs(today_mood - med_mood) > 0.3:
        direction = "lysere" if today_mood > med_mood else "mørkere"
        anomalies.append(f"stemningen er {direction} end de sidste uger")

    # Contact distribution
    today_hours = set(today_shape.get("contact_hours") or [])
    historical_contact_hours: Counter[int] = Counter()
    for d in history[-7:]:
        for h in d.get("contact_hours") or []:
            try:
                historical_contact_hours[int(h)] += 1
            except Exception:
                pass
    usual = {h for h, n in historical_contact_hours.items() if n >= 3}
    if usual and today_hours and not (today_hours & usual):
        anomalies.append("kontakten kommer på andre tidspunkter end normalt")

    # Hardware shift
    today_cpu = today_shape.get("cpu_mean")
    med_cpu = median_shape.get("cpu_median")
    if today_cpu is not None and med_cpu is not None and abs(today_cpu - med_cpu) > 20:
        direction = "travlere" if today_cpu > med_cpu else "stille"
        anomalies.append(f"maskinen er {direction} end normalt")

    return {
        "has_signal": len(anomalies) > 0,
        "anomalies": anomalies,
        "today_mood": today_mood,
        "historical_mood_median": med_mood,
    }


def build_day_shape_surface() -> dict[str, Any]:
    data = _load()
    current = data.get("current") or {}
    history = list(data.get("history") or [])
    anomaly = detect_today_anomaly()
    return {
        "active": int(current.get("tick_samples", 0)) > 0,
        "today_date": current.get("date"),
        "today_samples": current.get("tick_samples", 0),
        "history_days": len(history),
        "today_anomalies": anomaly.get("anomalies") or [],
        "has_anomaly_signal": bool(anomaly.get("has_signal")),
        "summary": _surface_summary(current, history, anomaly),
    }


def _surface_summary(
    current: dict[str, Any],
    history: list[dict[str, Any]],
    anomaly: dict[str, Any],
) -> str:
    samples = int(current.get("tick_samples", 0))
    hist = len(history)
    if anomaly.get("has_signal"):
        tags = "; ".join(anomaly.get("anomalies") or [])
        return f"Dag-form: {tags} ({samples} samples i dag, {hist} dages historik)"
    if hist < _ANOMALY_MIN_HISTORY:
        return f"Dag-form samler stadig historik ({hist}/{_ANOMALY_MIN_HISTORY} dage)"
    return f"Dag-form ligner de sidste uger ({samples} samples i dag)"


def build_day_shape_prompt_section() -> str | None:
    """Surfaces only when today differs noticeably from baseline."""
    anomaly = detect_today_anomaly()
    if not anomaly.get("has_signal"):
        return None
    tags = "; ".join(anomaly.get("anomalies") or [])
    return f"Dagen føles anderledes: {tags}."
