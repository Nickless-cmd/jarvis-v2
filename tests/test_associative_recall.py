"""Tests for associative memory recall system."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_recall_persistence():
    """Stop the non-isolated recall tests leaking into the REAL runtime DB.

    Several tests in this file (e.g. test_cap_enforcement_at_five_memories)
    exercise the coordinator via ``_fresh_ar()`` WITHOUT ``isolated_runtime``,
    so ``_add_to_active`` persists rows into ``recall_active_memories`` in the
    developer's/container's real ``~/.jarvis-v2/state/jarvis.db``. Those rows
    survive the process and later make ``build_recall_prompt_section()`` return
    stale content — test_build_recall_prompt_section_empty then fails when a
    prior run (or a prior test here) left "mem-strong" behind. Clear the table
    before and after each test so recall state starts and ends empty. The
    module reload on import restores active memories from this table, so clear
    the in-memory dict too.
    """
    def _wipe():
        try:
            import core.services.associative_recall as ar
            ar._clear_persisted_memories()
            ar._active_memories.clear()
        except Exception:
            pass

    _wipe()
    yield
    _wipe()


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


def test_observe_assoc_recall_scalar_only(monkeypatch):
    """Fase 3 (§23.3 #4): hot-path recall melder scalar-metadata (aldrig indhold) →
    memory/recall observe + eventbus. private_brain_share korrekt."""
    from core.services import associative_recall as ar
    import core.services.central_core as cc
    import core.eventbus.bus as bus

    observed, published = [], []
    monkeypatch.setattr(cc, "central",
                        lambda: type("C", (), {"observe": lambda s, e: observed.append(dict(e))})())
    monkeypatch.setattr(bus.event_bus, "publish", lambda k, p=None, **kw: published.append((k, p)))

    memories = [
        {"score": 0.8, "source_table": "experiential_memory", "narrative": "HEMMELIG NARRATIV"},
        {"score": 0.4, "source_table": "private_brain_records", "narrative": "mere"},
    ]
    ar._observe_assoc_recall(memories)

    ev = observed[0]
    assert (ev["cluster"], ev["nerve"]) == ("memory", "recall")
    assert ev["result_count"] == 2 and ev["top_score"] == 0.8
    assert ev["private_brain_share"] == 0.5
    assert "HEMMELIG" not in str(ev)  # intet indhold lækket
    assert any(k == "memory.recall" for k, _ in published)


def test_observe_assoc_recall_empty(monkeypatch):
    from core.services import associative_recall as ar
    import core.services.central_core as cc
    seen = []
    monkeypatch.setattr(cc, "central",
                        lambda: type("C", (), {"observe": lambda s, e: seen.append(e)})())
    ar._observe_assoc_recall([])
    assert seen[0]["result_count"] == 0 and seen[0]["private_brain_share"] == 0.0
