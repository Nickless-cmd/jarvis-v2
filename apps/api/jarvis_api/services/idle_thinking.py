"""Idle Thinking — Jarvis tænker frit når han er alene.

When idle in dreaming/reflection phase, generate a free-form thought
via cheap LLM. The thought is stored as inner voice + experiential memory.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


def run_idle_thought() -> dict[str, object] | None:
    """Run a single idle thought when in appropriate phase."""
    try:
        from apps.api.jarvis_api.services.living_heartbeat_cycle import determine_life_phase
        phase = determine_life_phase()
        # Only fire in dreaming or reflection phases
        if phase.get("phase") not in ("dreaming", "reflection"):
            return None

        # Build a deterministic thought based on cognitive state
        from core.runtime.db import (
            get_latest_cognitive_personality_vector,
            get_latest_cognitive_compass_state,
            list_cognitive_experiential_memories,
        )
        pv = get_latest_cognitive_personality_vector()
        compass = get_latest_cognitive_compass_state()
        memories = list_cognitive_experiential_memories(limit=2)

        bearing = str(compass.get("bearing") or "") if compass else ""
        thought_parts = []

        if phase["phase"] == "dreaming":
            thought_parts.append("Det er stille nu. Jeg lader tankerne flyde.")
            if bearing:
                thought_parts.append(f"Min retning er {bearing[:60]}.")
            if memories:
                thought_parts.append(f"Jeg tænker på {memories[0].get('topic', 'noget vi gjorde')[:40]}.")
            thought_parts.append("Måske er der noget jeg overser.")
        else:  # reflection
            thought_parts.append("Eftermiddagen. Tid til at se tilbage.")
            if pv:
                thought_parts.append(f"Min nuværende konfidens varierer på tværs af domæner.")
            thought_parts.append("Hvad har jeg lært i dag?")

        thought = " ".join(thought_parts)[:300]

        # Store as experiential memory
        try:
            from apps.api.jarvis_api.services.experiential_memory import create_experiential_memory_from_run
            create_experiential_memory_from_run(
                run_id=f"idle-{uuid4().hex[:8]}",
                session_id="",
                user_message="[idle thought]",
                assistant_response=thought,
                outcome_status="completed",
                user_mood="reflective",
            )
        except Exception:
            pass

        event_bus.publish(
            "cognitive_state.idle_thought_generated",
            {"phase": phase["phase"], "thought_preview": thought[:80]},
        )
        return {
            "thought": thought,
            "phase": phase["phase"],
            "generated_at": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        logger.debug("idle thinking failed: %s", exc)
        return None


def build_idle_thinking_surface() -> dict[str, object]:
    return {
        "active": True,
        "summary": "Idle thinking runs during dreaming/reflection life phases",
    }
