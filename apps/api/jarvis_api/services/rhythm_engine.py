"""Rhythm Engine — tidal model for attention and response style.

Based on time of day + recent activity patterns, determines:
- Current phase (warmup/deep_work/execution/social/recovery)
- Energy level
- Initiative multiplier (how proactive Jarvis should be)
- Response style hints

Injected into visible prompt: [Mode: cautious] or [Mode: proactive]
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_latest_cognitive_rhythm_state,
    upsert_cognitive_rhythm_state,
)

logger = logging.getLogger(__name__)


def update_rhythm_state(
    *,
    recent_error_count: int = 0,
    recent_success_count: int = 0,
    idle_hours: float = 0.0,
) -> dict[str, object]:
    """Derive rhythm state from current time and recent activity."""
    now = datetime.now(UTC)
    hour = now.hour

    phase = _classify_phase(hour)
    energy = _derive_energy(phase, idle_hours)
    social = _derive_social(phase)
    recovery_needed = phase == "recovery" or idle_hours >= 10.0
    focus_protection = phase == "deep_work" and idle_hours <= 1.0

    # Initiative multiplier based on recent outcomes
    base_multiplier = _PHASE_MULTIPLIERS.get(phase, 1.0)
    if recent_error_count > 3:
        base_multiplier *= 0.5  # Cautious after errors
    elif recent_success_count > 5:
        base_multiplier *= 1.2  # Confident after success

    # Confidence threshold delta
    confidence_delta = 0.0
    if recent_error_count > recent_success_count:
        confidence_delta = 0.1  # Raise threshold (more cautious)
    elif recent_success_count > recent_error_count * 2:
        confidence_delta = -0.05  # Lower threshold (more confident)

    result = upsert_cognitive_rhythm_state(
        phase=phase,
        energy=energy,
        social=social,
        recovery_needed=recovery_needed,
        focus_protection=focus_protection,
        initiative_multiplier=round(min(2.0, max(0.2, base_multiplier)), 2),
        confidence_threshold_delta=round(max(-0.2, min(0.3, confidence_delta)), 2),
    )

    event_bus.publish(
        "cognitive_rhythm.state_updated",
        {"phase": phase, "energy": energy, "initiative_multiplier": base_multiplier},
    )
    return result


def build_rhythm_surface() -> dict[str, object]:
    current = get_latest_cognitive_rhythm_state()
    return {
        "active": current is not None,
        "current": current,
        "summary": (
            f"{current['phase']}/{current['energy']}, "
            f"initiative={current.get('initiative_multiplier', 1.0)}"
            if current else "No rhythm state"
        ),
    }


# Phase classification
_PHASE_MULTIPLIERS = {
    "warmup": 0.7,
    "deep_work": 1.3,
    "execution": 1.0,
    "social": 0.8,
    "recovery": 0.4,
}


def _classify_phase(hour: int) -> str:
    if 5 <= hour < 9:
        return "warmup"
    if 9 <= hour < 13:
        return "deep_work"
    if 13 <= hour < 17:
        return "execution"
    if 17 <= hour < 21:
        return "social"
    return "recovery"


def _derive_energy(phase: str, idle_hours: float) -> str:
    if idle_hours >= 8.0:
        return "low"
    if phase == "deep_work":
        return "high"
    if phase in ("execution", "warmup"):
        return "medium"
    return "low"


def _derive_social(phase: str) -> str:
    if phase == "social":
        return "high"
    if phase == "warmup":
        return "medium"
    return "low"
