"""Emergent Bridge — consumer for emergent signals to influence visible prompt.

Bridges the gap between emergent_signal_tracking (producer) and visible prompts.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Only influences when signal_status == "emergent" (not "candidate")
- Observable in Mission Control
- Bounded: max 1 influence per prompt
"""
from __future__ import annotations

from typing import Any

from apps.api.jarvis_api.services.emergent_signal_tracking import (
    _signals,
    build_runtime_emergent_signal_surface,
)


_INFLUENCE_COOLDOWN_TICKS: int = 0
_influence_count: int = 0


def should_influence_prompt() -> bool:
    """Determine if an emergent signal should influence the visible prompt."""
    global _influence_count

    surface = build_runtime_emergent_signal_surface(limit=3)
    active = surface.get("items", [])
    
    for item in active:
        if (
            item.get("signal_status") == "emergent"
            and item.get("lifecycle_state") in ("strengthening", "candidate")
            and float(item.get("salience", 0)) >= 0.78
        ):
            _influence_count += 1
            return True
    
    return False


def get_influencing_emergents() -> list[dict[str, Any]]:
    """Get the emergent signals that are currently influencing."""
    surface = build_runtime_emergent_signal_surface(limit=3)
    items = surface.get("items", [])
    
    influencing = []
    for item in items:
        if (
            item.get("signal_status") == "emergent"
            and float(item.get("salience", 0)) >= 0.78
        ):
            influencing.append({
                "canonical_key": item.get("canonical_key"),
                "signal_family": item.get("signal_family"),
                "short_summary": item.get("short_summary"),
                "salience": item.get("salience"),
                "lifecycle_state": item.get("lifecycle_state"),
                "source_hints": item.get("source_hints", []),
            })
    
    return influencing


def format_emergent_for_prompt() -> str:
    """Format emergent signal for prompt injection."""
    influencing = get_influencing_emergents()
    
    if not influencing:
        return ""
    
    top = influencing[0]
    summary = str(top.get("short_summary", "")).strip()
    
    if summary:
        return f"[INDRE MØNSTER: {summary}]"
    
    return ""


def reset_emergent_bridge() -> None:
    """Reset emergent bridge state (for testing)."""
    global _influence_count
    _influence_count = 0


def get_emergent_bridge_state() -> dict[str, Any]:
    """Get current state of emergent bridge."""
    influencing = get_influencing_emergents()
    return {
        "influence_count": _influence_count,
        "can_influence": should_influence_prompt(),
        "current_influencing": influencing,
    }


def build_emergent_bridge_surface() -> dict[str, Any]:
    """Build MC surface for emergent bridge."""
    state = get_emergent_bridge_state()
    influencing = state.get("current_influencing", [])
    
    return {
        "active": bool(influencing),
        "influence_count": state.get("influence_count", 0),
        "can_influence": state.get("can_influence", False),
        "current_influencing": influencing,
        "summary": (
            f"{len(influencing)} indre mønster påvirker"
            if influencing else "Ingen indre mønstre påvirker"
        ),
    }
