"""Subjective Time — how time FEELS, not just passes.

An intense 5-min conversation feels longer than 6 hours of silence.
"""
from __future__ import annotations
from datetime import UTC, datetime


def build_subjective_time_perception(
    *, tick_count_last_hour: int = 0, conversation_intensity: float = 0.0,
    novelty_score: float = 0.0, idle_hours: float = 0.0,
) -> dict[str, object]:
    if conversation_intensity > 0.7 and idle_hours < 1:
        feel = "tiden fløj — intens samtale"
    elif idle_hours > 8:
        feel = "en lang stille strækning"
    elif idle_hours > 4:
        feel = "en rolig pause"
    elif novelty_score > 0.6:
        feel = "nyt og overraskende — tiden er mættet"
    elif tick_count_last_hour > 3:
        feel = "en travl time med mange tanker"
    else:
        feel = "en jævn, rolig rytme"
    return {"feel": feel, "idle_hours": idle_hours,
            "intensity": conversation_intensity, "novelty": novelty_score}


def build_subjective_time_surface() -> dict[str, object]:
    return {"active": True, "summary": "Subjective time runs per prompt assembly"}
