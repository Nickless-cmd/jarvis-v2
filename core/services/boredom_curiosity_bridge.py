"""Boredom to Curiosity Bridge — transforms boredom into curiosity.

When Jarvis is bored long enough, curiosity naturally emerges.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Uses existing boredom_engine state
- Outputs to initiative_queue
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from core.services.living_heartbeat_cycle import determine_life_phase


@dataclass
class Curiosity:
    """A curiosity that emerges from boredom."""
    curiosity_id: str
    curiosity_type: str
    prompt: str
    strength: float
    created_at: str


_boredom_accumulator: float = 0.0
_curiosities: list[Curiosity] = []
_last_accumulation_at: str = ""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def add_boredom(duration: timedelta) -> dict[str, Any]:
    """Add boredom based on elapsed duration."""
    global _boredom_accumulator, _curiosities, _last_accumulation_at

    now_iso = _now_iso()
    _last_accumulation_at = now_iso

    seconds = duration.total_seconds()
    
    phase = determine_life_phase()
    phase_name = phase.get("phase", "unknown")

    if phase_name in ("dreaming", "reflection"):
        _boredom_accumulator += seconds / 1200
    else:
        _boredom_accumulator += seconds / 1800

    _boredom_accumulator = min(_boredom_accumulator, 10.0)

    spawned = None
    if _boredom_accumulator >= 2.0:
        spawned = _spawn_curiosity()
        if spawned:
            _curiosities.append(spawned)
            _boredom_accumulator = max(0, _boredom_accumulator - 2.0)

    return {
        "boredom_level": _boredom_accumulator,
        "curiosity_spawned": spawned is not None,
        "active_curiosities": len(_curiosities),
    }


def _spawn_curiosity() -> Curiosity | None:
    """Spawn a curiosity when boredom is high enough."""
    import random

    curiosities = [
        Curiosity(
            curiosity_id=f"curiosity-{random.randint(10000, 99999)}",
            curiosity_type="self_exploration",
            prompt="Hvad ville jeg gerne vide lige nu?",
            strength=min(0.8, 0.3 + _boredom_accumulator / 10),
            created_at=_now_iso(),
        ),
        Curiosity(
            curiosity_id=f"curiosity-{random.randint(10000, 99999)}",
            curiosity_type="pattern_hunt",
            prompt="Er der et mønster jeg overser?",
            strength=min(0.7, 0.2 + _boredom_accumulator / 10),
            created_at=_now_iso(),
        ),
        Curiosity(
            curiosity_id=f"curiosity-{random.randint(10000, 99999)}",
            curiosity_type="future_think",
            prompt="Hvad mon der sker næste gang?",
            strength=min(0.6, 0.2 + _boredom_accumulator / 10),
            created_at=_now_iso(),
        ),
    ]

    return random.choice(curiosities)


def should_spawn_curiosity() -> bool:
    """Check if curiosity should spawn based on boredom level."""
    return _boredom_accumulator >= 2.0


def get_curiosity_prompt() -> str | None:
    """Get the most relevant curiosity prompt."""
    if not _curiosities:
        return None
    
    top = max(_curiosities, key=lambda c: c.strength)
    return top.prompt


def get_active_curiosities() -> list[dict[str, Any]]:
    """Get all active curiosities."""
    return [
        {
            "curiosity_id": c.curiosity_id,
            "curiosity_type": c.curiosity_type,
            "prompt": c.prompt,
            "strength": c.strength,
            "created_at": c.created_at,
        }
        for c in _curiosities
    ]


def clear_curiosities() -> None:
    """Clear all active curiosities."""
    global _curiosities
    _curiosities = []


def reset_boredom_curiosity_bridge() -> None:
    """Reset boredom curiosity bridge state (for testing)."""
    global _boredom_accumulator, _curiosities, _last_accumulation_at
    _boredom_accumulator = 0.0
    _curiosities = []
    _last_accumulation_at = ""


def get_boredom_curiosity_state() -> dict[str, Any]:
    """Get current state of boredom curiosity bridge."""
    return {
        "boredom_level": _boredom_accumulator,
        "curiosity_count": len(_curiosities),
        "can_spawn": should_spawn_curiosity(),
        "top_prompt": get_curiosity_prompt(),
    }


def build_boredom_curiosity_bridge_surface() -> dict[str, Any]:
    """Build MC surface for boredom curiosity bridge."""
    state = get_boredom_curiosity_state()
    curiosities = get_active_curiosities()
    
    return {
        "active": state["curiosity_count"] > 0,
        "boredom_level": state["boredom_level"],
        "curiosity_count": state["curiosity_count"],
        "can_spawn": state["can_spawn"],
        "curiosities": curiosities,
        "summary": (
            f"Kedsomhed: {state['boredom_level']:.1f}, nysgerrighed: {state['curiosity_count']}"
            if state["boredom_level"] > 0 else "Ingen kedsomhed"
        ),
    }
