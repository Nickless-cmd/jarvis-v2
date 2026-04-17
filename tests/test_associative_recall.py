"""Tests for associative memory recall system."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Task 1: DB layer tests
# ---------------------------------------------------------------------------

def test_get_experiential_memory_candidates_empty(isolated_runtime) -> None:
    db = isolated_runtime.db
    result = db.get_experiential_memory_candidates(limit=20)
    assert result == []


def test_get_experiential_memory_candidates_ordering(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_cognitive_experiential_memory(
        memory_id="mem-low",
        narrative="Low importance memory",
        topic="testing",
        importance=0.3,
    )
    db.insert_cognitive_experiential_memory(
        memory_id="mem-high",
        narrative="High importance memory",
        topic="testing",
        importance=0.9,
    )
    db.insert_cognitive_experiential_memory(
        memory_id="mem-mid",
        narrative="Medium importance memory",
        topic="testing",
        importance=0.6,
    )
    result = db.get_experiential_memory_candidates(limit=20)
    assert len(result) == 3
    # Ordered by importance DESC
    assert result[0]["memory_id"] == "mem-high"
    assert result[1]["memory_id"] == "mem-mid"
    assert result[2]["memory_id"] == "mem-low"
    # Required fields present
    assert "memory_id" in result[0]
    assert "narrative" in result[0]
    assert "topic" in result[0]
    assert "emotion_arc" in result[0]
    assert "key_lesson" in result[0]
    assert "importance" in result[0]


# ---------------------------------------------------------------------------
# Task 2: LLM scoring tests
# ---------------------------------------------------------------------------

def test_score_memories_returns_empty_on_no_candidates() -> None:
    import importlib
    import core.services.experiential_memory as em
    importlib.reload(em)
    result = em.score_memories_by_relevance(
        candidates=[],
        context_text="testing deployment",
        emotional_state={},
    )
    assert result == {}


def test_score_memories_fallback_on_llm_failure(monkeypatch) -> None:
    import importlib
    import core.services.experiential_memory as em
    importlib.reload(em)

    def _raise(*a, **kw):
        raise RuntimeError("offline")

    monkeypatch.setattr(em, "_call_scoring_llm", _raise)
    monkeypatch.setattr(em, "_resolve_scoring_llm_target", lambda: {"active": True, "provider": "ollama", "model": "test", "base_url": "http://localhost:11434"})

    candidates = [
        {"memory_id": "mem-1", "narrative": "We fixed a bug", "topic": "debugging", "emotion_arc": "neutral → relief", "key_lesson": "test more"},
    ]
    result = em.score_memories_by_relevance(
        candidates=candidates,
        context_text="there is a bug",
        emotional_state={"frustration": 0.6},
    )
    assert result == {}


def test_score_memories_parses_llm_response(monkeypatch) -> None:
    import importlib
    import core.services.experiential_memory as em
    importlib.reload(em)

    llm_response = '{"mem-1": 0.85, "mem-2": 0.3}'
    monkeypatch.setattr(em, "_call_scoring_llm", lambda target, prompt: llm_response)
    monkeypatch.setattr(em, "_resolve_scoring_llm_target", lambda: {"active": True})

    candidates = [
        {"memory_id": "mem-1", "narrative": "bug fix", "topic": "debugging", "emotion_arc": "", "key_lesson": ""},
        {"memory_id": "mem-2", "narrative": "refactor", "topic": "code", "emotion_arc": "", "key_lesson": ""},
    ]
    result = em.score_memories_by_relevance(
        candidates=candidates,
        context_text="we have a bug",
        emotional_state={"frustration": 0.4},
    )
    assert abs(result["mem-1"] - 0.85) < 0.001
    assert abs(result["mem-2"] - 0.3) < 0.001


# ---------------------------------------------------------------------------
# Task 3: associative_recall coordinator tests
# ---------------------------------------------------------------------------

def _fresh_ar():
    """Return freshly reloaded associative_recall module with empty state."""
    import importlib
    import core.services.associative_recall as ar
    importlib.reload(ar)
    return ar


def test_build_recall_prompt_section_empty() -> None:
    ar = _fresh_ar()
    result = ar.build_recall_prompt_section()
    assert result == ""


def test_clear_session_recall_resets_state() -> None:
    ar = _fresh_ar()
    ar._active_memories["mem-1"] = {
        "memory_id": "mem-1",
        "narrative": "We fixed a bug",
        "topic": "debugging",
        "score": 0.85,
    }
    ar.clear_session_recall()
    assert ar._active_memories == {}
    assert ar.build_recall_prompt_section() == ""


def test_build_recall_prompt_section_formats_correctly() -> None:
    ar = _fresh_ar()
    ar._active_memories["mem-1"] = {
        "memory_id": "mem-1",
        "narrative": "We fixed a critical deployment bug together",
        "topic": "deployment",
        "score": 0.85,
    }
    result = ar.build_recall_prompt_section()
    assert "deployment" in result
    assert "0.85" in result
    assert "mem-1" not in result  # memory_id not exposed to prompt


def test_apply_weak_recall_to_emotions_triggers_concept() -> None:
    import importlib
    import core.services.emotion_concepts as ec_mod
    importlib.reload(ec_mod)
    ar = _fresh_ar()

    triggered = []
    original = ec_mod.trigger_emotion_concept
    ec_mod.trigger_emotion_concept = lambda concept, intensity, **kw: triggered.append((concept, intensity))

    try:
        memories = [
            {"memory_id": "mem-1", "narrative": "...", "topic": "error", "score": 0.5, "emotion_arc": "frustration → relief"},
        ]
        ar.apply_weak_recall_to_emotions(memories)
    finally:
        ec_mod.trigger_emotion_concept = original

    assert len(triggered) >= 1


def test_cap_enforcement_at_five_memories() -> None:
    ar = _fresh_ar()
    for i in range(5):
        ar._active_memories[f"mem-{i}"] = {
            "memory_id": f"mem-{i}",
            "narrative": f"Memory {i}",
            "topic": "test",
            "score": 0.5 + i * 0.05,
        }
    assert len(ar._active_memories) == 5

    ar._add_to_active({
        "memory_id": "mem-strong",
        "narrative": "Very relevant memory",
        "topic": "test",
        "score": 0.95,
    })
    assert len(ar._active_memories) == 5
    assert "mem-0" not in ar._active_memories  # weakest (0.5) evicted
    assert "mem-strong" in ar._active_memories


def test_topic_repetition_multiplier() -> None:
    ar = _fresh_ar()
    ar._record_topic("deployment")
    ar._record_topic("deployment")
    ar._record_topic("deployment")
    multiplier = ar._get_topic_multiplier("deployment")
    assert abs(multiplier - 1.5) < 0.001


def test_topic_multiplier_resets_after_ten_messages() -> None:
    ar = _fresh_ar()
    for _ in range(10):
        ar._record_topic("other")
    ar._record_topic("deployment")
    multiplier = ar._get_topic_multiplier("deployment")
    assert multiplier == 1.0  # Not enough repetitions


# ---------------------------------------------------------------------------
# Task 4: cognitive_state_assembly integration test
# ---------------------------------------------------------------------------

def test_cognitive_state_includes_recall_section(isolated_runtime) -> None:
    """When active memories exist, cognitive state includes them."""
    import importlib
    import core.services.associative_recall as ar_mod
    importlib.reload(ar_mod)

    ar_mod._active_memories["mem-test"] = {
        "memory_id": "mem-test",
        "narrative": "We debugged a tricky race condition together",
        "topic": "concurrency",
        "score": 0.88,
    }

    import core.services.cognitive_state_assembly as csa
    importlib.reload(csa)

    result = csa.build_cognitive_state_for_prompt(compact=False)
    assert result is not None
    assert "concurrency" in result or "race condition" in result
