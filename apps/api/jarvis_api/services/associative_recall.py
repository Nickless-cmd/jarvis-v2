"""Associative Recall — dormant memories triggered by context.

Coordinator that queries the experiential memory DB, scores candidates via
local LLM, and maintains in-memory active memories for the current session.

Strong matches (score ≥ 0.7) are injected as text into the system prompt.
Weak matches (score 0.3–0.69) trigger emotion concepts at proportional intensity.

Max 5 active memories at any time. Weakest is evicted when cap is reached.
Topic repetition: same topic in ≥3 of last 10 messages amplifies scores by ×1.5.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

_MAX_ACTIVE = 5
_STRONG_THRESHOLD = 0.7
_WEAK_THRESHOLD = 0.3
_REPETITION_THRESHOLD = 3
_REPETITION_MULTIPLIER = 1.5
_TOPIC_WINDOW = 10

# In-memory state
_active_memories: dict[str, dict[str, Any]] = {}
_topic_history: deque[str] = deque(maxlen=_TOPIC_WINDOW)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recall_for_session(session_context: dict[str, Any]) -> list[dict[str, Any]]:
    """Run associative recall at session start. Populates up to 3 active memories.

    session_context keys used: channel, bearing, time_of_day (all optional).
    Returns list of memories that were activated.
    """
    from core.runtime.db import get_experiential_memory_candidates
    from apps.api.jarvis_api.services.experiential_memory import score_memories_by_relevance

    candidates = get_experiential_memory_candidates(limit=20)
    if not candidates:
        return []

    context_text = _build_session_context_text(session_context)
    scores = score_memories_by_relevance(
        candidates=candidates,
        context_text=context_text,
        emotional_state={},
    )

    if not scores:
        # Fallback: activate top-3 by importance
        for c in candidates[:3]:
            _add_to_active({**c, "score": c["importance"]})
        return list(_active_memories.values())

    activated = []
    weak = []
    for memory_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        candidate = next((c for c in candidates if c["memory_id"] == memory_id), None)
        if not candidate:
            continue
        if score >= _STRONG_THRESHOLD and len(_active_memories) < 3:
            _add_to_active({**candidate, "score": score})
            activated.append({**candidate, "score": score})
        elif score >= _WEAK_THRESHOLD:
            weak.append({**candidate, "score": score})

    if weak:
        apply_weak_recall_to_emotions(weak)

    logger.debug("associative_recall: session init — %d active, %d weak", len(activated), len(weak))
    return activated


def recall_for_message(
    message_text: str,
    emotional_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Run associative recall for a user message. Adds up to 2 active memories.

    Excludes already-active memories from candidate pool.
    Applies topic repetition multiplier to scores.
    Returns list of newly activated memories.
    """
    from core.runtime.db import get_experiential_memory_candidates, reinforce_experiential_memory
    from apps.api.jarvis_api.services.experiential_memory import score_memories_by_relevance

    topic_hint = _extract_topic_hint(message_text)
    if topic_hint:
        _record_topic(topic_hint)

    candidates = get_experiential_memory_candidates(limit=15)
    active_ids = set(_active_memories.keys())
    candidates = [c for c in candidates if c["memory_id"] not in active_ids]

    # Check for re-activation of existing active memories
    for mem_id in list(active_ids):
        mem = _active_memories.get(mem_id)
        if mem and topic_hint and topic_hint.lower() in str(mem.get("topic") or "").lower():
            try:
                reinforce_experiential_memory(mem_id)
                logger.debug("associative_recall: reinforced existing memory %s", mem_id)
            except Exception:
                pass

    if not candidates:
        return []

    scores = score_memories_by_relevance(
        candidates=candidates,
        context_text=message_text,
        emotional_state=emotional_state,
    )

    if not scores:
        return []

    # Apply topic repetition multiplier
    for memory_id in list(scores.keys()):
        candidate = next((c for c in candidates if c["memory_id"] == memory_id), None)
        if candidate:
            topic = str(candidate.get("topic") or "")
            multiplier = _get_topic_multiplier(topic)
            scores[memory_id] = min(1.0, scores[memory_id] * multiplier)

    activated = []
    weak = []
    added_count = 0
    for memory_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        candidate = next((c for c in candidates if c["memory_id"] == memory_id), None)
        if not candidate:
            continue
        if score >= _STRONG_THRESHOLD and added_count < 2:
            _add_to_active({**candidate, "score": score})
            activated.append({**candidate, "score": score})
            added_count += 1
        elif score >= _WEAK_THRESHOLD:
            weak.append({**candidate, "score": score})

    if weak:
        apply_weak_recall_to_emotions(weak)

    return activated


def build_recall_prompt_section() -> str:
    """Format active memories for system prompt injection.

    Returns empty string if no active memories.
    """
    if not _active_memories:
        return ""

    lines = ["Associative memories (triggered by current context):"]
    for mem in sorted(_active_memories.values(), key=lambda m: m.get("score", 0), reverse=True):
        narrative = str(mem.get("narrative") or "")[:80]
        topic = str(mem.get("topic") or "")
        score = float(mem.get("score") or 0)
        lines.append(f"- {narrative} (topic: {topic}, strength: {score:.2f})")

    return "\n".join(lines)


def apply_weak_recall_to_emotions(memories: list[dict[str, Any]]) -> None:
    """Trigger emotion concepts from weak-scoring memories.

    Maps emotion_arc content to relevant emotion concepts at proportional intensity.
    """
    try:
        from apps.api.jarvis_api.services.emotion_concepts import trigger_emotion_concept
    except Exception:
        return

    for mem in memories:
        score = float(mem.get("score") or 0)
        emotion_arc = str(mem.get("emotion_arc") or "").lower()
        intensity = score * 0.5  # Scale: 0.3 → 0.15, 0.69 → 0.345

        if "frustration" in emotion_arc:
            trigger_emotion_concept("frustration_blocked", intensity, trigger="weak_recall", source="associative_recall")
        elif "relief" in emotion_arc:
            trigger_emotion_concept("relief", intensity, trigger="weak_recall", source="associative_recall")
        elif "indsigt" in emotion_arc or "insight" in emotion_arc:
            trigger_emotion_concept("insight", intensity, trigger="weak_recall", source="associative_recall")
        elif "begejstring" in emotion_arc or "enthusias" in emotion_arc:
            trigger_emotion_concept("anticipation", intensity, trigger="weak_recall", source="associative_recall")
        elif "tilfredshed" in emotion_arc or "satisf" in emotion_arc:
            trigger_emotion_concept("accomplishment", intensity, trigger="weak_recall", source="associative_recall")
        elif "skuffelse" in emotion_arc or "disappoint" in emotion_arc:
            trigger_emotion_concept("doubt", intensity, trigger="weak_recall", source="associative_recall")
        else:
            trigger_emotion_concept("curiosity_narrow", intensity, trigger="weak_recall", source="associative_recall")


def clear_session_recall() -> None:
    """Reset all active memories and topic history. Call at session end."""
    global _topic_history
    _active_memories.clear()
    _topic_history = deque(maxlen=_TOPIC_WINDOW)
    logger.debug("associative_recall: session cleared")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _add_to_active(memory: dict[str, Any]) -> None:
    """Add memory to active set. Evicts weakest if at cap."""
    memory_id = str(memory["memory_id"])
    if len(_active_memories) >= _MAX_ACTIVE and memory_id not in _active_memories:
        weakest_id = min(
            _active_memories.keys(),
            key=lambda k: float(_active_memories[k].get("score") or 0),
        )
        del _active_memories[weakest_id]
    _active_memories[memory_id] = memory


def _record_topic(topic: str) -> None:
    """Record a topic in the sliding window history."""
    _topic_history.append(topic.lower()[:50])


def _get_topic_multiplier(topic: str) -> float:
    """Return ×1.5 if topic appears ≥3 times in recent history, else ×1.0."""
    if not topic:
        return 1.0
    topic_lower = topic.lower()
    count = sum(1 for t in _topic_history if topic_lower in t or t in topic_lower)
    return _REPETITION_MULTIPLIER if count >= _REPETITION_THRESHOLD else 1.0


def _extract_topic_hint(text: str) -> str:
    """Extract a short topic hint from message text (first meaningful words)."""
    words = [w.strip(".,!?") for w in text.split() if len(w) > 4][:3]
    return " ".join(words)[:40] if words else ""


def _build_session_context_text(session_context: dict[str, Any]) -> str:
    """Build a context description string for session-level scoring."""
    parts = []
    if channel := session_context.get("channel"):
        parts.append(f"channel={channel}")
    if bearing := session_context.get("bearing"):
        parts.append(f"bearing={bearing}")
    if time_of_day := session_context.get("time_of_day"):
        parts.append(f"time={time_of_day}")
    return "Session start. " + ", ".join(parts) if parts else "Session start."
