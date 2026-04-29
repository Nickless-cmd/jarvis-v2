"""Experiential Memory — not just facts, but lived experiences with emotion.

Each run creates a brief experiential memory:
narrative + user_mood + key_lesson + emotion_arc + topic.
Relevant memories are surfaced in future prompts.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any
from urllib import request as urllib_request
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


def score_memories_by_relevance(
    *,
    candidates: list[dict[str, object]],
    context_text: str,
    emotional_state: dict[str, object],
) -> dict[str, float]:
    """Score candidate memories for relevance using local LLM.

    Returns {memory_id: score} dict with scores 0.0–1.0.
    Returns empty dict if no candidates, LLM unavailable, or LLM call fails.
    """
    if not candidates:
        return {}
    target = _resolve_scoring_llm_target()
    if not target:
        return {}
    prompt = _build_scoring_prompt(candidates, context_text, emotional_state)
    try:
        response = _call_scoring_llm(target, prompt)
        return _parse_scoring_response(response, candidates)
    except Exception:
        logger.debug("experiential_memory: LLM scoring failed", exc_info=True)
        return {}


def _resolve_scoring_llm_target() -> dict[str, object] | None:
    """Resolve local/cheap LLM lane for scoring."""
    try:
        from core.runtime.provider_router import resolve_provider_router_target
        for lane in ("local", "cheap"):
            try:
                target = resolve_provider_router_target(lane=lane)
                if bool(target.get("active")):
                    return target
            except Exception:
                continue
    except Exception:
        pass
    return None


def _build_scoring_prompt(
    candidates: list[dict[str, object]],
    context_text: str,
    emotional_state: dict[str, object],
) -> str:
    """Build LLM prompt for memory relevance scoring."""
    emotion_parts = [
        f"{k}={v:.2f}" for k, v in emotional_state.items()
        if isinstance(v, (int, float)) and float(v) > 0.1
    ]
    emotion_str = ", ".join(emotion_parts) if emotion_parts else "neutral"

    candidate_lines = []
    for c in candidates:
        narrative = str(c.get("narrative") or "")[:80]
        topic = str(c.get("topic") or "")
        emotion_arc = str(c.get("emotion_arc") or "")
        candidate_lines.append(
            f'  "{c["memory_id"]}": topic={topic!r}, narrative={narrative!r}, arc={emotion_arc!r}'
        )
    candidates_str = "\n".join(candidate_lines)

    return (
        f"Current context: {context_text[:200]}\n"
        f"Emotional state: {emotion_str}\n\n"
        f"Score each memory for relevance to the current context (0.0 = irrelevant, 1.0 = highly relevant).\n"
        f"Consider: semantic similarity, emotional resonance, topic overlap.\n\n"
        f"Memories:\n{candidates_str}\n\n"
        f"Return ONLY a JSON object: {{\"memory_id\": score, ...}}\n"
        f"Example: {{\"exp-abc123\": 0.82, \"exp-def456\": 0.15}}"
    )


def _call_scoring_llm(target: dict[str, object], prompt: str) -> str:
    """Score memories with cloud-first / local-fallback strategy.

    2026-04-29: scoring prompts are public-safe (200-char user-message
    snippet + 80-char memory narrative snippets, no identity context).
    Per project norms (see prompt_relevance_backend) this content class
    is acceptable for OllamaFreeAPI cloud calls. We try cloud first
    (typical 0.7-1.5s) and fall back to local Ollama (3s ceiling).

    The local Ollama path is preserved unchanged as the safety net —
    if cloud is down or rate-limited, scoring still works at the
    higher local-Ollama latency.
    """
    try:
        from core.runtime.settings import load_settings
        primary = str(
            getattr(load_settings(), "memory_scoring_primary", "ollamafreeapi") or ""
        ).strip().lower()
    except Exception:
        primary = "ollamafreeapi"

    if primary == "ollamafreeapi":
        cloud_text = _call_scoring_llm_ollamafreeapi(prompt)
        if cloud_text:
            return cloud_text
        logger.info(
            "experiential_memory: cloud scoring unavailable, falling back to local Ollama"
        )

    return _call_scoring_llm_local(target, prompt)


def _call_scoring_llm_ollamafreeapi(prompt: str) -> str:
    """Score via OllamaFreeAPI cloud with hard wall-clock timeout.

    The library silently drops its own timeout kwarg, so we run the
    call in a daemon thread and enforce the deadline ourselves.
    Returns "" on timeout/error so the caller can fall back to local.
    """
    try:
        from core.runtime.ollamafreeapi_provider import call_ollamafreeapi
        from core.runtime.settings import load_settings
    except Exception:
        return ""

    try:
        settings = load_settings()
        model = str(
            getattr(settings, "memory_scoring_ollamafreeapi_model", "gpt-oss:20b")
            or "gpt-oss:20b"
        )
        timeout = float(
            getattr(settings, "memory_scoring_ollamafreeapi_timeout", 2) or 2
        )
    except Exception:
        model, timeout = "gpt-oss:20b", 2.0

    holder: dict[str, Any] = {}

    def _runner() -> None:
        try:
            holder["result"] = call_ollamafreeapi(
                model=model, prompt=prompt, timeout=int(timeout)
            )
        except BaseException as exc:  # noqa: BLE001
            holder["exc"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout=max(0.1, timeout))
    if thread.is_alive():
        logger.info(
            "experiential_memory: ollamafreeapi scoring timed out after %.1fs", timeout
        )
        return ""
    if "exc" in holder:
        logger.debug(
            "experiential_memory: ollamafreeapi scoring error", exc_info=holder["exc"]
        )
        return ""
    payload = holder.get("result") or {}
    return str((payload.get("message") or {}).get("content") or "").strip()


def _call_scoring_llm_local(target: dict[str, object], prompt: str) -> str:
    """Local Ollama scoring path. Configurable timeout ceiling (default 3s)."""
    try:
        from core.runtime.settings import load_settings
        timeout = int(
            getattr(load_settings(), "memory_scoring_ollama_timeout", 3) or 3
        )
    except Exception:
        timeout = 3

    provider = str(target.get("provider") or "")
    model = str(target.get("model") or "")
    base_url = str(target.get("base_url") or "")

    if provider == "ollama":
        url = f"{base_url or 'http://127.0.0.1:11434'}/api/chat"
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 300},
        }).encode()
        req = urllib_request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
        return str(result.get("message", {}).get("content", ""))
    return ""


def _parse_scoring_response(
    text: str,
    candidates: list[dict[str, object]],
) -> dict[str, float]:
    """Parse LLM JSON scoring response. Validates memory_ids against candidates."""
    valid_ids = {str(c["memory_id"]) for c in candidates}
    text = text.strip()
    if text.startswith("```"):
        lines = [line for line in text.split("\n") if not line.startswith("```")]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return {
                k: max(0.0, min(1.0, float(v)))
                for k, v in parsed.items()
                if k in valid_ids and isinstance(v, (int, float))
            }
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict):
                return {
                    k: max(0.0, min(1.0, float(v)))
                    for k, v in parsed.items()
                    if k in valid_ids and isinstance(v, (int, float))
                }
        except Exception:
            pass
    return {}


def _safe(fn, **kwargs):
    try:
        fn(**kwargs)
    except Exception:
        logger.debug("experiential_memory: failed", exc_info=True)
