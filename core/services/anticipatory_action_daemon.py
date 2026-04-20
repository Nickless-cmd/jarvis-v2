"""Anticipatory Action Daemon — predict + pre-act.

Jarvis' plan #4 (PLAN_PROPRIOCEPTION.md, 2026-04-20): find recurring
user patterns, then emit an `anticipation_signal` shortly *before* they
happen, so Jarvis can prepare context.

Simple v1 patterns:
- Peak contact hours: histogram of visible_runs by hour-of-day.
  If a given hour receives >= 30% of recent contacts and has N>=3
  observations, flag it as a peak. When local time is within 15 min
  before a peak hour → emit anticipation signal.

Persistence: JSON file with {peak_hours, observation_counts, last_updated}.
Recomputes once per hour (slow cadence).
"""
from __future__ import annotations

import json
import logging
import os
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/anticipatory_patterns.json"
_MIN_OBSERVATIONS_FOR_PEAK = 3
_PEAK_SHARE_THRESHOLD = 0.30  # hour must hold ≥30% of contacts among peaks
_MIN_CONFIDENCE = 0.6
_HIGH_CONFIDENCE = 0.8
_RECOMPUTE_INTERVAL_SECONDS = 3600
_ANTICIPATION_WINDOW_MINUTES = 15


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"peak_hours": [], "hour_counts": {}, "last_updated": None}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("peak_hours", [])
            data.setdefault("hour_counts", {})
            data.setdefault("last_updated", None)
            return data
    except Exception as exc:
        logger.warning("anticipatory_action: load failed: %s", exc)
    return {"peak_hours": [], "hour_counts": {}, "last_updated": None}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("anticipatory_action: save failed: %s", exc)


def _should_recompute(data: dict[str, Any], now: datetime) -> bool:
    last = data.get("last_updated")
    if not last:
        return True
    try:
        prev = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
    except Exception:
        return True
    return (now - prev).total_seconds() > _RECOMPUTE_INTERVAL_SECONDS


def _gather_contact_hours() -> Counter[int]:
    """Collect contact hours from recent visible runs."""
    hours: Counter[int] = Counter()
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=500) or []
        cutoff = datetime.now(UTC) - timedelta(days=14)
        for r in runs:
            ts = str(r.get("started_at") or "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if dt < cutoff:
                continue
            hours[dt.hour] += 1
    except Exception as exc:
        logger.debug("anticipatory_action: gather failed: %s", exc)
    return hours


def _compute_peak_hours(hour_counts: Counter[int]) -> list[dict[str, Any]]:
    total = sum(hour_counts.values())
    if total == 0:
        return []
    peaks: list[dict[str, Any]] = []
    for hour, count in hour_counts.items():
        if count < _MIN_OBSERVATIONS_FOR_PEAK:
            continue
        share = count / total
        if share < _PEAK_SHARE_THRESHOLD:
            continue
        # Confidence: balance observation count + share
        confidence = min(1.0, (count / 10) * 0.5 + share * 0.5)
        if confidence < _MIN_CONFIDENCE:
            continue
        peaks.append({
            "hour": int(hour),
            "count": int(count),
            "share": round(share, 3),
            "confidence": round(confidence, 3),
        })
    peaks.sort(key=lambda p: p["confidence"], reverse=True)
    return peaks


def recompute_patterns() -> dict[str, Any]:
    """Rebuild pattern signature from recent data."""
    data = _load()
    hour_counts = _gather_contact_hours()
    peaks = _compute_peak_hours(hour_counts)
    data["hour_counts"] = {str(h): int(c) for h, c in hour_counts.items()}
    data["peak_hours"] = peaks
    data["last_updated"] = datetime.now(UTC).isoformat()
    _save(data)
    return data


def _local_now() -> datetime:
    return datetime.now().astimezone()


def _minutes_until_hour(now_local: datetime, target_hour: int) -> int:
    """Returns minutes until next occurrence of target_hour (always in [0, 1440))."""
    minute_of_day = now_local.hour * 60 + now_local.minute
    target_minute_of_day = target_hour * 60
    delta = target_minute_of_day - minute_of_day
    if delta < 0:
        delta += 1440
    return delta


def _maybe_emit_anticipation(peaks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Emit signals for peaks coming up within the anticipation window."""
    if not peaks:
        return []
    now_local = _local_now()
    emitted: list[dict[str, Any]] = []
    for p in peaks:
        minutes = _minutes_until_hour(now_local, int(p["hour"]))
        if 0 < minutes <= _ANTICIPATION_WINDOW_MINUTES and p["confidence"] >= _HIGH_CONFIDENCE:
            signal = {
                "hour": p["hour"],
                "minutes_until": minutes,
                "confidence": p["confidence"],
                "share": p["share"],
                "at": datetime.now(UTC).isoformat(),
            }
            emitted.append(signal)
            try:
                from core.eventbus.bus import event_bus
                event_bus.publish({
                    "kind": "anticipation.contact_expected",
                    "payload": signal,
                })
            except Exception:
                pass
    return emitted


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    now = datetime.now(UTC)
    data = _load()
    if _should_recompute(data, now):
        data = recompute_patterns()
    emitted = _maybe_emit_anticipation(data.get("peak_hours") or [])
    return {
        "peaks": len(data.get("peak_hours") or []),
        "signals_emitted": len(emitted),
    }


def build_anticipatory_action_surface() -> dict[str, Any]:
    data = _load()
    peaks = data.get("peak_hours") or []
    upcoming: list[dict[str, Any]] = []
    if peaks:
        now_local = _local_now()
        for p in peaks:
            minutes = _minutes_until_hour(now_local, int(p["hour"]))
            upcoming.append({
                "hour": p["hour"],
                "minutes_until": minutes,
                "confidence": p["confidence"],
                "share": p["share"],
                "count": p["count"],
            })
        upcoming.sort(key=lambda x: x["minutes_until"])
    total_obs = sum(data.get("hour_counts", {}).values()) if isinstance(data.get("hour_counts"), dict) else 0
    return {
        "active": len(peaks) > 0,
        "peak_hour_count": len(peaks),
        "total_observations": int(total_obs),
        "upcoming_peaks": upcoming[:5],
        "last_updated": data.get("last_updated"),
        "summary": _surface_summary(peaks, upcoming),
    }


def _surface_summary(peaks: list[dict[str, Any]], upcoming: list[dict[str, Any]]) -> str:
    if not peaks:
        return "Ingen tydelige kontakt-mønstre endnu"
    if upcoming:
        soonest = upcoming[0]
        return (
            f"{len(peaks)} peak-timer identificeret, næste kl {soonest['hour']:02d} "
            f"om {soonest['minutes_until']}m (confidence={soonest['confidence']})"
        )
    return f"{len(peaks)} peak-timer kendt"


def build_anticipatory_action_prompt_section() -> str | None:
    """Surface imminent anticipated contact."""
    data = _load()
    peaks = data.get("peak_hours") or []
    if not peaks:
        return None
    now_local = _local_now()
    for p in peaks:
        minutes = _minutes_until_hour(now_local, int(p["hour"]))
        if 0 < minutes <= _ANTICIPATION_WINDOW_MINUTES and p["confidence"] >= _HIGH_CONFIDENCE:
            return (
                f"Forventer kontakt om ca {minutes} minutter (kl {p['hour']:02d}, "
                f"confidence={p['confidence']}). Klargør context."
            )
    return None
