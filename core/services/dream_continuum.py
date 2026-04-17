"""Dream Continuum — dreams that mature and "think" between ticks.

Extends dream_carry_over with dreams that evolve during idle periods.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Bounded state, max 3 active dream-thoughts
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
import random

from core.services.dream_carry_over import (
    _ACTIVE_DREAMS,
    get_presentable_dream,
    format_dream_for_prompt,
)


@dataclass
class DreamThought:
    """A thought a dream has between ticks."""
    thought_id: str
    dream_id: str
    content: str
    created_at: str
    relevance: float = 0.5


_dream_maturity: dict[str, float] = {}
_dream_thoughts: dict[str, list[DreamThought]] = {}
_last_evolution_at: str = ""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def evolve_dreams(duration: timedelta) -> dict[str, Any]:
    """Evolve dreams based on elapsed duration since last tick."""
    global _dream_maturity, _dream_thoughts, _last_evolution_at

    now_iso = _now_iso()
    seconds = duration.total_seconds()
    _last_evolution_at = now_iso

    evolved_count = 0
    thought_counts = {}

    active_dreams = list(_ACTIVE_DREAMS)
    for dream in active_dreams:
        dream_id = dream.get("dream_id", "")
        if not dream_id:
            continue

        current_maturity = _dream_maturity.get(dream_id, 0.0)
        
        if seconds >= 30:
            maturity_increase = min(0.3, seconds / 6000)
            _dream_maturity[dream_id] = min(1.0, current_maturity + maturity_increase)
            evolved_count += 1

            if _dream_maturity[dream_id] >= 0.05:
                thought = _generate_dream_thought(dream, _dream_maturity[dream_id])
                _dream_thoughts.setdefault(dream_id, []).append(thought)
                thought_counts[dream_id] = len(_dream_thoughts[dream_id])

    return {
        "evolved_count": evolved_count,
        "thought_counts": thought_counts,
        "duration_seconds": seconds,
    }


def _generate_dream_thought(dream: dict, maturity: float) -> DreamThought:
    """Generate a thought a dream has during idle."""
    content = dream.get("content", "")
    themes = [
        "måske handler det om",
        "jeg undrer mig over",
        "hvad nu hvis",
        "noget siger mig at",
        "jeg forestiller mig",
    ]
    theme = random.choice(themes)
    thought_content = f"{theme} {content[:100]}..."

    return DreamThought(
        thought_id=f"dream-thought-{random.randint(10000, 99999)}",
        dream_id=dream.get("dream_id", ""),
        content=thought_content,
        created_at=_now_iso(),
        relevance=min(1.0, maturity + 0.3),
    )


def get_dream_thoughts(dream_id: str) -> list[dict]:
    """Get all thoughts for a specific dream."""
    thoughts = _dream_thoughts.get(dream_id, [])
    return [
        {
            "thought_id": t.thought_id,
            "content": t.content,
            "created_at": t.created_at,
            "relevance": t.relevance,
        }
        for t in thoughts
    ]


def get_top_dream_thought() -> str | None:
    """Get the most relevant dream thought for prompt injection."""
    all_thoughts = []
    for dream_id, thoughts in _dream_thoughts.items():
        for thought in thoughts:
            all_thoughts.append((thought.relevance, thought.content))

    if not all_thoughts:
        return None

    all_thoughts.sort(key=lambda x: x[0], reverse=True)
    return all_thoughts[0][1]


def format_dreams_for_prompt() -> str:
    """Format dreams and thoughts for prompt injection."""
    presentable = get_presentable_dream()
    if not presentable:
        top_thought = get_top_dream_thought()
        if top_thought:
            return f"[DRØM-TANKER: {top_thought}]"
        return ""

    return format_dream_for_prompt(presentable)


def get_dream_maturity(dream_id: str) -> float:
    """Get maturity level of a specific dream."""
    return _dream_maturity.get(dream_id, 0.0)


def reset_dream_continuum() -> None:
    """Reset dream continuum state (for testing)."""
    global _dream_maturity, _dream_thoughts, _last_evolution_at
    _dream_maturity = {}
    _dream_thoughts = {}
    _last_evolution_at = ""


def build_dream_continuum_surface() -> dict[str, Any]:
    """Build MC surface for dream continuum."""
    active_dreams = list(_ACTIVE_DREAMS)
    return {
        "active": bool(active_dreams),
        "dream_count": len(active_dreams),
        "maturity_levels": {
            dream.get("dream_id", ""): _dream_maturity.get(dream.get("dream_id", ""), 0.0)
            for dream in active_dreams
        },
        "thought_counts": {
            dream_id: len(thoughts)
            for dream_id, thoughts in _dream_thoughts.items()
        },
        "last_evolution_at": _last_evolution_at,
        "top_thought": get_top_dream_thought(),
        "summary": (
            f"{len(active_dreams)} drømme, {sum(len(t) for t in _dream_thoughts.values())} tanker"
            if active_dreams else "Ingen aktive drømme"
        ),
    }
