"""Seed System — prospective memory / dormant intentions.

Seeds are ideas planted now that activate in the future:
- Time-based: "Check back on deploy in 2 hours"
- Event-based: "When user mentions X, surface Y"
- Context-based: "When working on frontend, remind about Z"
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    insert_cognitive_seed,
    list_cognitive_seeds,
    update_cognitive_seed_status,
)

logger = logging.getLogger(__name__)


def plant_seed(
    *,
    title: str,
    summary: str = "",
    activate_at: str = "",
    activate_on_event: list[str] | None = None,
    activate_on_context: list[str] | None = None,
    relevance_score: float = 0.5,
    linked_goal: str = "",
) -> dict[str, object]:
    """Plant a dormant intention seed."""
    seed_id = f"seed-{uuid4().hex[:10]}"
    result = insert_cognitive_seed(
        seed_id=seed_id,
        title=title,
        summary=summary,
        activate_at=activate_at,
        activate_on_event=json.dumps(activate_on_event or [], ensure_ascii=False),
        activate_on_context=json.dumps(activate_on_context or [], ensure_ascii=False),
        relevance_score=relevance_score,
        linked_goal=linked_goal,
    )

    event_bus.publish(
        "cognitive_seed.planted",
        {"seed_id": seed_id, "title": title},
    )
    return result


def check_seed_activation(
    *,
    current_context: str = "",
    current_event: str = "",
) -> list[dict[str, object]]:
    """Check if any planted seeds should activate."""
    now = datetime.now(UTC)
    seeds = list_cognitive_seeds(status="planted", limit=50)
    activated = []

    for seed in seeds:
        should_activate = False

        # Time-based activation
        activate_at = str(seed.get("activate_at") or "").strip()
        if activate_at:
            try:
                target = datetime.fromisoformat(activate_at.replace("Z", "+00:00"))
                if now >= target:
                    should_activate = True
            except Exception:
                pass

        # Context-based activation
        contexts = _safe_json_list(seed.get("activate_on_context"))
        if contexts and current_context:
            ctx_lower = current_context.lower()
            if any(c.lower() in ctx_lower for c in contexts):
                should_activate = True

        # Event-based activation
        events = _safe_json_list(seed.get("activate_on_event"))
        if events and current_event:
            if current_event in events:
                should_activate = True

        if should_activate:
            update_cognitive_seed_status(seed_id=seed["seed_id"], status="sprouted")
            activated.append(seed)
            event_bus.publish(
                "cognitive_seed.sprouted",
                {"seed_id": seed["seed_id"], "title": seed.get("title")},
            )

    return activated


def fulfill_seed(seed_id: str) -> None:
    """Mark a seed as fulfilled."""
    update_cognitive_seed_status(seed_id=seed_id, status="fulfilled")
    event_bus.publish("cognitive_seed.fulfilled", {"seed_id": seed_id})


def build_seed_surface() -> dict[str, object]:
    planted = list_cognitive_seeds(status="planted", limit=20)
    sprouted = list_cognitive_seeds(status="sprouted", limit=10)
    return {
        "active": bool(planted) or bool(sprouted),
        "planted": planted,
        "sprouted": sprouted,
        "summary": (
            f"{len(planted)} planted, {len(sprouted)} sprouted"
            if planted or sprouted else "No seeds"
        ),
    }


def auto_plant_seeds_from_conversation(*, user_message: str) -> list[dict[str, object]]:
    """Scan user message for future-intent markers and auto-plant seeds."""
    msg_lower = user_message.lower()
    planted = []

    _INTENT_MARKERS = [
        ("vi skal huske", "reminder"),
        ("husk at", "reminder"),
        ("bagefter", "deferred_task"),
        ("næste gang", "future_context"),
        ("senere", "deferred_task"),
        ("i morgen", "deferred_task"),
        ("vi tager det", "deferred_task"),
        ("todo", "task"),
    ]

    for marker, seed_type in _INTENT_MARKERS:
        if marker in msg_lower:
            # Extract context around the marker
            idx = msg_lower.index(marker)
            context = user_message[max(0, idx - 20):idx + len(marker) + 80].strip()
            if len(context) < 10:
                continue

            # Extract keywords for activation context
            words = [w for w in context.split() if len(w) > 4][:5]

            result = plant_seed(
                title=f"Auto: {context[:60]}",
                summary=context[:200],
                activate_on_context=json.dumps(words, ensure_ascii=False),
            )
            planted.append(result)

    return planted


def _safe_json_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return []
