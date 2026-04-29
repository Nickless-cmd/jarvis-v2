"""Temporal Context — time-based situational awareness.

Tracks user activity patterns and provides temporal context
for prompt assembly (time of day, productive hours, etc).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


def build_temporal_context() -> dict[str, object]:
    """Build current temporal context."""
    now = datetime.now(UTC)
    hour = now.hour
    weekday = now.weekday()  # 0=Monday

    phase = _classify_day_phase(hour)
    is_weekend = weekday >= 5
    is_peak_focus = 9 <= hour <= 13 and not is_weekend

    _en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    _da = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]

    return {
        "time_of_day": f"{hour:02d}:00",
        "day_phase": phase,
        "weekday": _en[weekday],
        "weekday_da": _da[weekday],
        "is_weekend": is_weekend,
        "is_peak_focus": is_peak_focus,
        "hour": hour,
    }


def build_temporal_context_surface() -> dict[str, object]:
    ctx = build_temporal_context()
    return {
        "active": True,
        "current": ctx,
        "summary": f"{ctx['weekday_da']} {ctx['time_of_day']} — {ctx['day_phase']}",
    }


def _classify_day_phase(hour: int) -> str:
    if 5 <= hour < 9:
        return "morning"
    if 9 <= hour < 12:
        return "late_morning"
    if 12 <= hour < 14:
        return "midday"
    if 14 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"
