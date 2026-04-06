"""Experiential Memory — not just facts, but lived experiences with emotion.

Each run creates a brief experiential memory:
narrative + user_mood + key_lesson + emotion_arc + topic.
Relevant memories are surfaced in future prompts.
"""

from __future__ import annotations

import logging
import threading
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_relevant_experiential_memories,
    insert_cognitive_experiential_memory,
    list_cognitive_experiential_memories,
)

logger = logging.getLogger(__name__)


def create_experiential_memory_from_run(
    *,
    run_id: str,
    session_id: str = "",
    user_message: str,
    assistant_response: str,
    outcome_status: str,
    user_mood: str = "neutral",
) -> dict[str, object] | None:
    """Create an experiential memory from a visible run."""
    if not user_message.strip():
        return None

    # Extract topic from user message (first meaningful words)
    topic = _extract_topic(user_message)
    if not topic:
        return None

    # Build narrative
    narrative = _build_narrative(
        user_message=user_message,
        outcome_status=outcome_status,
        user_mood=user_mood,
        topic=topic,
    )

    # Determine emotion arc
    emotion_arc = _determine_emotion_arc(user_mood, outcome_status)

    # Key lesson (deterministic)
    key_lesson = _extract_lesson(outcome_status, user_mood, user_message)

    # Importance: higher for corrections, failures, enthusiasm
    importance = _calculate_importance(user_mood, outcome_status)

    # Determine Jarvis mood from outcome
    jarvis_mood = "satisfied" if outcome_status in ("completed", "success") else "uncertain"
    if outcome_status in ("failed", "error"):
        jarvis_mood = "concerned"

    memory_id = f"exp-{uuid4().hex[:10]}"
    result = insert_cognitive_experiential_memory(
        memory_id=memory_id,
        session_id=session_id,
        run_id=run_id,
        narrative=narrative,
        user_mood=user_mood,
        jarvis_mood=jarvis_mood,
        key_lesson=key_lesson,
        emotion_arc=emotion_arc,
        topic=topic,
        importance=importance,
    )

    event_bus.publish(
        "cognitive_experiential.memory_created",
        {
            "memory_id": memory_id,
            "topic": topic,
            "user_mood": user_mood,
            "importance": importance,
        },
    )
    return result


def create_experiential_memory_async(**kwargs) -> None:
    """Fire-and-forget wrapper."""
    threading.Thread(
        target=lambda: _safe(create_experiential_memory_from_run, **kwargs),
        daemon=True,
    ).start()


def find_relevant_memories(context: str, limit: int = 2) -> list[dict[str, object]]:
    """Find experiential memories relevant to current context."""
    return get_relevant_experiential_memories(context=context, limit=limit)


def recall_with_nostalgia(memory_id: str) -> str | None:
    """Recall an old experience with emotional coloring — nostalgia."""
    from core.runtime.db import reinforce_experiential_memory
    memories = list_cognitive_experiential_memories(limit=50)
    memory = next((m for m in memories if m.get("memory_id") == memory_id), None)
    if not memory:
        return None
    reinforce_experiential_memory(memory_id)
    narrative = str(memory.get("narrative") or "")
    emotion = str(memory.get("emotion_arc") or "")
    topic = str(memory.get("topic") or "")
    return (
        f"Jeg husker den gang vi arbejdede med {topic[:40]}... "
        f"{narrative[:80]}. "
        f"{'Følelsen: ' + emotion if emotion else 'Det var en god oplevelse.'}"
    )


def build_experiential_memory_surface() -> dict[str, object]:
    """MC surface for experiential memories."""
    memories = list_cognitive_experiential_memories(limit=15)
    mood_counts: dict[str, int] = {}
    for m in memories:
        mood = m.get("user_mood", "neutral")
        mood_counts[mood] = mood_counts.get(mood, 0) + 1

    topics = list({m.get("topic", "") for m in memories if m.get("topic")})[:10]

    return {
        "active": bool(memories),
        "memories": memories,
        "total_count": len(memories),
        "mood_distribution": mood_counts,
        "topics": topics,
        "summary": (
            f"{len(memories)} experiences, topics: {', '.join(topics[:5])}"
            if memories else "No experiential memories yet"
        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_topic(user_message: str) -> str:
    """Extract a short topic from user message."""
    words = [w for w in user_message.split() if len(w) > 3][:6]
    return " ".join(words)[:80] if words else ""


def _build_narrative(
    *,
    user_message: str,
    outcome_status: str,
    user_mood: str,
    topic: str,
) -> str:
    """Build a brief narrative of the experience."""
    mood_text = {
        "frustrated": "Bjørn var frustreret",
        "enthusiastic": "Bjørn var entusiastisk",
        "impatient": "Bjørn ville have tempo",
        "curious": "Bjørn var nysgerrig",
        "tired": "Bjørn var træt",
        "neutral": "Standard arbejdstilstand",
    }.get(user_mood, "Neutral stemning")

    outcome_text = {
        "completed": "Opgaven blev løst",
        "success": "Det lykkedes",
        "failed": "Det fejlede",
        "error": "Der opstod en fejl",
    }.get(outcome_status, "Uvist udfald")

    return f"{mood_text}. Emne: {topic[:50]}. {outcome_text}."[:500]


def _determine_emotion_arc(user_mood: str, outcome_status: str) -> str:
    """Determine the emotional arc of the experience."""
    if user_mood == "frustrated" and outcome_status in ("completed", "success"):
        return "frustration → løsning"
    if user_mood == "frustrated" and outcome_status in ("failed", "error"):
        return "frustration → mere frustration"
    if user_mood == "enthusiastic":
        return "begejstring → udforskning"
    if user_mood == "curious":
        return "nysgerrighed → indsigt"
    if outcome_status in ("completed", "success"):
        return "neutral → tilfredshed"
    if outcome_status in ("failed", "error"):
        return "neutral → skuffelse"
    return "neutral → neutral"


def _extract_lesson(outcome_status: str, user_mood: str, user_message: str) -> str:
    """Extract a deterministic lesson."""
    if user_mood == "frustrated" and outcome_status in ("completed", "success"):
        return "Frustration kan løses med tålmodighed og grundighed"
    if user_mood == "frustrated" and outcome_status in ("failed", "error"):
        return "Når brugeren er frustreret, skift tilgang i stedet for at gentage"
    if outcome_status in ("failed", "error"):
        return "Verificér grundigere før næste forsøg"
    if user_mood == "impatient" and outcome_status in ("completed", "success"):
        return "Direkte og hurtigt giver bedst resultat ved utålmodighed"
    return ""


def _calculate_importance(user_mood: str, outcome_status: str) -> float:
    """Calculate importance score for the memory."""
    base = 0.4
    if user_mood in ("frustrated", "enthusiastic"):
        base += 0.2
    if user_mood in ("impatient", "curious"):
        base += 0.1
    if outcome_status in ("failed", "error"):
        base += 0.2
    if outcome_status in ("completed", "success"):
        base += 0.05
    return min(1.0, base)


def _safe(fn, **kwargs):
    try:
        fn(**kwargs)
    except Exception:
        logger.debug("experiential_memory: failed", exc_info=True)
