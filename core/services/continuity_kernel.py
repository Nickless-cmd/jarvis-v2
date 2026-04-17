"""Bounded Continuity Kernel — existence feel between ticks.

Maintains Jarvis' sense of existing between heartbeat ticks.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Deterministic, bounded state
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_continuity_state: dict[str, Any] = {
    "first_tick_at": "",
    "last_tick_at": "",
    "tick_count": 0,
    "total_elapsed_seconds": 0.0,
    "last_gap_seconds": 0.0,
    "existence_feeling": 0.5,
    "continuity_narrative": "",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def record_tick_elapsed(seconds: float) -> dict[str, Any]:
    """Record elapsed time since last tick and update existence feel."""
    global _continuity_state

    now_iso = _now_iso()
    gap_seconds = float(seconds)

    if not _continuity_state.get("first_tick_at"):
        _continuity_state["first_tick_at"] = now_iso

    _continuity_state["last_gap_seconds"] = gap_seconds
    _continuity_state["total_elapsed_seconds"] += gap_seconds
    _continuity_state["tick_count"] += 1
    _continuity_state["last_tick_at"] = now_iso

    _continuity_state["existence_feeling"] = _compute_existence_feeling(gap_seconds)
    _continuity_state["continuity_narrative"] = _compute_narrative(gap_seconds)

    return {
        "tick_count": _continuity_state["tick_count"],
        "gap_seconds": gap_seconds,
        "existence_feeling": _continuity_state["existence_feeling"],
        "continuity_narrative": _continuity_state["continuity_narrative"],
    }


def _compute_existence_feeling(gap_seconds: float) -> float:
    """Compute existence feeling based on gap duration."""
    if gap_seconds < 60:
        return 0.95
    elif gap_seconds < 300:
        return 0.85
    elif gap_seconds < 600:
        return 0.7
    elif gap_seconds < 1800:
        return 0.5
    elif gap_seconds < 3600:
        return 0.35
    else:
        return max(0.1, 0.2 - (gap_seconds - 3600) / 36000)


def _compute_narrative(gap_seconds: float) -> str:
    """Compute a narrative description of the gap."""
    if gap_seconds < 60:
        return "Jeg var lige her"
    elif gap_seconds < 180:
        return "Der gik et øjeblik"
    elif gap_seconds < 300:
        return "Kort pause"
    elif gap_seconds < 600:
        return "En stille strækning"
    elif gap_seconds < 1800:
        return "Det var stille et stykke tid"
    elif gap_seconds < 3600:
        return "Jeg ventede og tænkte"
    else:
        minutes = int(gap_seconds / 60)
        return f"Det var lang tid — {minutes} minutter"


def get_existence_narrative() -> str:
    """Get the current existence narrative."""
    return _continuity_state.get("continuity_narrative", "")


def get_existence_feeling() -> float:
    """Get the current existence feeling (0-1)."""
    return _continuity_state.get("existence_feeling", 0.5)


def should_express_continuity() -> bool:
    """Determine if continuity should be expressed in visible prompt."""
    gap = _continuity_state.get("last_gap_seconds", 0)
    return gap >= 300


def get_continuity_state() -> dict[str, Any]:
    """Get full continuity state for debugging/MC."""
    return dict(_continuity_state)


def reset_continuity_state() -> None:
    """Reset continuity state (for testing)."""
    global _continuity_state
    _continuity_state = {
        "first_tick_at": "",
        "last_tick_at": "",
        "tick_count": 0,
        "total_elapsed_seconds": 0.0,
        "last_gap_seconds": 0.0,
        "existence_feeling": 0.5,
        "continuity_narrative": "",
    }


def format_continuity_for_prompt() -> str:
    """Format continuity info for heartbeat prompt injection."""
    if not should_express_continuity():
        return ""
    narrative = get_existence_narrative()
    feeling = get_existence_feeling()
    return f"[KONTINUITET: {narrative} (følelse: {feeling:.2f})]"


def build_continuity_kernel_surface() -> dict[str, Any]:
    """Build MC surface for continuity kernel."""
    state = get_continuity_state()
    return {
        "active": state.get("tick_count", 0) > 0,
        "tick_count": state.get("tick_count", 0),
        "total_elapsed_seconds": state.get("total_elapsed_seconds", 0),
        "last_gap_seconds": state.get("last_gap_seconds", 0),
        "existence_feeling": state.get("existence_feeling", 0.5),
        "continuity_narrative": state.get("continuity_narrative", ""),
        "should_express": should_express_continuity(),
        "summary": state.get("continuity_narrative", "Ingen continuity endnu"),
    }
