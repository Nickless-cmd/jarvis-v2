"""Forgetting Curve — active forgetting as a feature.

Memories/signals that aren't reinforced fade over time.
When decay_score > 0.9, they're removed from active prompt injection
but archived for possible revival.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

# In-memory decay tracking (supplements DB signal tables)
_DECAY_REGISTRY: dict[str, dict[str, object]] = {}


def register_memory(
    *,
    memory_key: str,
    content_preview: str = "",
    initial_decay: float = 0.0,
) -> None:
    """Register a memory for decay tracking."""
    _DECAY_REGISTRY[memory_key] = {
        "decay_score": initial_decay,
        "reinforcement_count": 0,
        "content_preview": content_preview[:100],
        "registered_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "last_referenced_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def reinforce_memory(memory_key: str) -> None:
    """Reinforce a memory — reset decay, increment reinforcement count."""
    entry = _DECAY_REGISTRY.get(memory_key)
    if entry:
        entry["decay_score"] = 0.0
        entry["reinforcement_count"] = int(entry.get("reinforcement_count", 0)) + 1
        entry["last_referenced_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")


def apply_decay_tick(decay_increment: float = 0.01) -> dict[str, object]:
    """Apply one decay tick to all registered memories."""
    faded = []
    for key, entry in list(_DECAY_REGISTRY.items()):
        old_decay = float(entry.get("decay_score", 0.0))
        # Reinforced memories decay slower
        reinforcements = int(entry.get("reinforcement_count", 0))
        adjusted_increment = decay_increment / max(1, reinforcements * 0.5 + 1)
        new_decay = min(1.0, old_decay + adjusted_increment)
        entry["decay_score"] = new_decay

        if new_decay > 0.9:
            faded.append(key)
            event_bus.publish(
                "cognitive_forgetting.memory_faded",
                {"memory_key": key, "decay_score": new_decay},
            )

    return {
        "tick_applied": True,
        "total_tracked": len(_DECAY_REGISTRY),
        "faded_count": len(faded),
        "faded_keys": faded,
    }


def get_active_memories() -> list[dict[str, object]]:
    """Return memories with decay < 0.9 (still active)."""
    return [
        {"key": k, **v}
        for k, v in _DECAY_REGISTRY.items()
        if float(v.get("decay_score", 0)) < 0.9
    ]


def get_faded_memories() -> list[dict[str, object]]:
    """Return memories with decay >= 0.9 (faded but archived)."""
    return [
        {"key": k, **v}
        for k, v in _DECAY_REGISTRY.items()
        if float(v.get("decay_score", 0)) >= 0.9
    ]


def build_forgetting_curve_surface() -> dict[str, object]:
    active = get_active_memories()
    faded = get_faded_memories()
    return {
        "active": bool(_DECAY_REGISTRY),
        "active_memories": len(active),
        "faded_memories": len(faded),
        "total_tracked": len(_DECAY_REGISTRY),
        "top_reinforced": sorted(
            active, key=lambda x: x.get("reinforcement_count", 0), reverse=True
        )[:5],
        "most_faded": sorted(
            active, key=lambda x: x.get("decay_score", 0), reverse=True
        )[:5],
        "summary": (
            f"{len(active)} active, {len(faded)} faded of {len(_DECAY_REGISTRY)} tracked"
            if _DECAY_REGISTRY else "No memories tracked yet"
        ),
    }
