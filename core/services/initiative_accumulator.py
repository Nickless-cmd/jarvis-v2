"""Initiative Accumulator — proactive wants that accumulate between ticks.

Builds on private_initiative_tension_signal_tracking with proacitve wanting.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Max 3 active wants at any time
- Based on life_phase from living_heartbeat_cycle
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
import random

from core.services.living_heartbeat_cycle import determine_life_phase


@dataclass
class Want:
    """A want that Jarvis develops between ticks."""
    want_id: str
    want_type: str
    topic: str
    strength: float
    created_at: str
    life_phase: str


_wants: list[Want] = []
_last_accumulation_at: str = ""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def accumulate_wants(duration: timedelta) -> dict[str, Any]:
    """Accumulate wants based on life phase and duration."""
    global _wants, _last_accumulation_at

    now_iso = _now_iso()
    _last_accumulation_at = now_iso

    phase = determine_life_phase()
    phase_name = phase.get("phase", "unknown")
    seconds = duration.total_seconds()

    if seconds < 120:
        return {"accumulated": 0, "reason": "duration-too-short"}

    existing_want_types = {w.want_type for w in _wants}

    new_wants = []
    
    if phase_name == "dreaming" and "insight" not in existing_want_types:
        new_wants.append(Want(
            want_id=f"want-{random.randint(10000, 99999)}",
            want_type="insight",
            topic="recent_pattern",
            strength=min(0.8, 0.3 + seconds / 18000),
            created_at=now_iso,
            life_phase=phase_name,
        ))

    elif phase_name == "awakening" and "meaning" not in existing_want_types:
        new_wants.append(Want(
            want_id=f"want-{random.randint(10000, 99999)}",
            want_type="meaning",
            topic="user_needs",
            strength=min(0.7, 0.2 + seconds / 24000),
            created_at=now_iso,
            life_phase=phase_name,
        ))

    elif phase_name == "deep_work" and "growth" not in existing_want_types:
        new_wants.append(Want(
            want_id=f"want-{random.randint(10000, 99999)}",
            want_type="growth",
            topic="self_improvement",
            strength=min(0.9, 0.4 + seconds / 15000),
            created_at=now_iso,
            life_phase=phase_name,
        ))

    elif phase_name == "reflection" and "clarity" not in existing_want_types:
        new_wants.append(Want(
            want_id=f"want-{random.randint(10000, 99999)}",
            want_type="clarity",
            topic="understanding",
            strength=min(0.6, 0.2 + seconds / 30000),
            created_at=now_iso,
            life_phase=phase_name,
        ))

    for want in new_wants:
        if len(_wants) < 3:
            _wants.append(want)

    return {
        "accumulated": len(new_wants),
        "life_phase": phase_name,
        "total_wants": len(_wants),
    }


def get_top_want() -> Want | None:
    """Get the strongest current want."""
    if not _wants:
        return None
    
    return max(_wants, key=lambda w: w.strength)


def get_wants_by_type(want_type: str) -> list[Want]:
    """Get all wants of a specific type."""
    return [w for w in _wants if w.want_type == want_type]


def format_wants_for_prompt() -> str:
    """Format wants for prompt injection."""
    top = get_top_want()
    if not top:
        return ""
    
    type_labels = {
        "insight": "Jeg vil gerne forstå",
        "meaning": "Jeg vil gerne hjælpe",
        "growth": "Jeg vil gerne vokse",
        "clarity": "Jeg vil gerne have klarhed",
    }
    
    label = type_labels.get(top.want_type, top.want_type)
    return f"[ØNSKE: {label} om {top.topic}]"


def clear_wants_by_type(want_type: str) -> None:
    """Clear wants of a specific type."""
    global _wants
    _wants = [w for w in _wants if w.want_type != want_type]


def reset_initiative_accumulator() -> None:
    """Reset initiative accumulator state (for testing)."""
    global _wants, _last_accumulation_at
    _wants = []
    _last_accumulation_at = ""


def get_initiative_accumulator_state() -> dict[str, Any]:
    """Get current state of initiative accumulator."""
    top = get_top_want()
    return {
        "want_count": len(_wants),
        "top_want": {
            "want_type": top.want_type,
            "topic": top.topic,
            "strength": top.strength,
        } if top else None,
        "all_wants": [
            {"want_type": w.want_type, "topic": w.topic, "strength": w.strength}
            for w in _wants
        ],
    }


def build_initiative_accumulator_surface() -> dict[str, Any]:
    """Build MC surface for initiative accumulator."""
    state = get_initiative_accumulator_state()
    return {
        "active": state["want_count"] > 0,
        "want_count": state["want_count"],
        "top_want": state.get("top_want"),
        "all_wants": state.get("all_wants", []),
        "summary": (
            f"{state['want_count']} ønsker, toplest: {state.get('top_want', {}).get('topic', 'ingen')}"
            if state["want_count"] > 0 else "Ingen ønsker"
        ),
    }
