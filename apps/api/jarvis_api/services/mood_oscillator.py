"""Mood Oscillator — sinusoidal mood waves between ticks.

Creates rhythm-based mood oscillations using sine waves.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Deterministic, bounded state
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

_phase_offset: float = 0.0
_tick_count: int = 0


def tick(seconds: float) -> dict[str, Any]:
    """Update phase offset based on elapsed time."""
    global _phase_offset, _tick_count
    _tick_count += 1
    _phase_offset += seconds / 600
    return {
        "phase_offset": _phase_offset,
        "tick_count": _tick_count,
    }


def get_current_mood() -> str:
    """Get current mood based on sinusoidal oscillation."""
    value = math.sin(_phase_offset)
    if value > 0.6:
        return "euphoric"
    elif value > 0.3:
        return "content"
    elif value > -0.3:
        return "neutral"
    elif value > -0.6:
        return "melancholic"
    else:
        return "distressed"


def get_mood_intensity() -> float:
    """Get mood intensity (0-1) based on absolute position in cycle."""
    return abs(math.sin(_phase_offset))


def get_mood_description() -> str:
    """Get human-readable mood description."""
    mood = get_current_mood()
    intensity = get_mood_intensity()
    mood_labels = {
        "euphoric": "Euforisk",
        "content": "Tilfreds",
        "neutral": "Neutral",
        "melancholic": "Melankolisk",
        "distressed": "Trist",
    }
    label = mood_labels.get(mood, mood)
    if intensity > 0.8:
        return f"Meget {label}"
    elif intensity > 0.5:
        return label
    else:
        return "Lidt " + label


def format_mood_for_prompt() -> str:
    """Format mood for prompt injection."""
    mood = get_current_mood()
    desc = get_mood_description()
    return f"[STEMNING: {desc}]"


def reset_mood_oscillator() -> None:
    """Reset mood oscillator (for testing)."""
    global _phase_offset, _tick_count
    _phase_offset = 0.0
    _tick_count = 0


def build_mood_oscillator_surface() -> dict[str, Any]:
    """Build MC surface for mood oscillator."""
    return {
        "active": True,
        "phase_offset": _phase_offset,
        "tick_count": _tick_count,
        "current_mood": get_current_mood(),
        "mood_description": get_mood_description(),
        "intensity": get_mood_intensity(),
        "summary": get_mood_description(),
    }
