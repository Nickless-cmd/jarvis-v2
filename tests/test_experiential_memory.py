"""Tests for core/services/experiential_memory.py"""

from __future__ import annotations

import json

import pytest

from core.services.experiential_memory import (
    _build_narrative,
    _build_scoring_prompt,
    _calculate_importance,
    _determine_emotion_arc,
    _extract_lesson,
    _extract_topic,
    _parse_scoring_response,
    _resolve_scoring_llm_target,
    score_memories_by_relevance,
)


# ── _extract_topic ──


def test_extract_topic_normal():
    # Words ≤3 chars are filtered; "fix" (3) and "the" (3) are dropped
    assert _extract_topic("fix the database connection timeout") == "database connection timeout"


def test_extract_topic_short_words_filtered():
    assert _extract_topic("no a an") == ""


def test_extract_topic_empty():
    assert _extract_topic("") == ""


def test_extract_topic_long_truncated():
    long_msg = " ".join(["verylongword"] * 20)
    result = _extract_topic(long_msg)
    assert len(result) <= 80


# ── _build_narrative ──


def test_build_narrative_frustrated_completed():
    result = _build_narrative(
        user_message="fix timeout",
        outcome_status="completed",
        user_mood="frustrated",
        topic="timeout fix",
    )
    assert "Bjørn var frustreret" in result
    assert "Opgaven blev løst" in result


def test_build_narrative_enthusiastic():
    result = _build_narrative(
        user_message="build new feature",
        outcome_status="success",
        user_mood="enthusiastic",
        topic="feature",
    )
    assert "Bjørn var entusiastisk" in result
    assert "Det lykkedes" in result


def test_build_narrative_failed():
    result = _build_narrative(
        user_message="deploy broke",
        outcome_status="error",
        user_mood="neutral",
        topic="deploy",
    )
    assert "Standard arbejdstilstand" in result
    assert "Der opstod en fejl" in result


def test_build_narrative_unknown_mood_and_outcome():
    result = _build_narrative(
        user_message="hello",
        outcome_status="unknown",
        user_mood="unknown",
        topic="hello",
    )
    assert "Neutral stemning" in result
    assert "Uvist udfald" in result


# ── _determine_emotion_arc ──


def test_emotion_arc_frustration_resolution():
    assert _determine_emotion_arc("frustrated", "completed") == "frustration → løsning"


def test_emotion_arc_frustration_compounds():
    assert _determine_emotion_arc("frustrated", "failed") == "frustration → mere frustration"


def test_emotion_arc_enthusiastic():
    assert _determine_emotion_arc("enthusiastic", "completed") == "begejstring → udforskning"


def test_emotion_arc_curious():
    assert _determine_emotion_arc("curious", "completed") == "nysgerrighed → indsigt"


def test_emotion_arc_neutral_success():
    assert _determine_emotion_arc("neutral", "success") == "neutral → tilfredshed"


def test_emotion_arc_neutral_failure():
    assert _determine_emotion_arc("tired", "failed") == "neutral → skuffelse"


def test_emotion_arc_default():
    assert _determine_emotion_arc("bored", "ongoing") == "neutral → neutral"


# ── _extract_lesson ──


def test_extract_lesson_frustration_resolved():
    assert "tålmodighed" in _extract_lesson("completed", "frustrated", "fix")


def test_extract_lesson_frustration_failed():
    assert "skift tilgang" in _extract_lesson("failed", "frustrated", "fix")


def test_extract_lesson_generic_failure():
    assert "Verificér" in _extract_lesson("error", "neutral", "fix")


def test_extract_lesson_impatient_success():
    assert "Direkte" in _extract_lesson("success", "impatient", "quick fix")


def test_extract_lesson_default_empty():
    assert _extract_lesson("ongoing", "bored", "hello") == ""


# ── _calculate_importance ──


def test_calculate_importance_base():
    assert _calculate_importance("neutral", "ongoing") == 0.4


def test_calculate_importance_enthusiastic_failure():
    imp = _calculate_importance("enthusiastic", "failed")
    assert imp == 0.8  # 0.4 + 0.2 + 0.2


def test_calculate_importance_frustrated_success():
    imp = _calculate_importance("frustrated", "success")
    assert imp == pytest.approx(0.65)  # 0.4 + 0.2 + 0.05


def test_calculate_importance_max():
    # Max is 0.8: 0.4 base + 0.2 max mood bonus + 0.2 failed/error
    imp = _calculate_importance("frustrated", "error")
    assert imp == 0.8


# ── _build_scoring_prompt ──


def test_build_scoring_prompt_basic():
    candidates = [
        {
            "memory_id": "exp-001",
            "narrative": "Bjørn var frustreret. fix timeout. Opgaven blev løst.",
            "topic": "database",
            "emotion_arc": "frustration → løsning",
        }
    ]
    prompt = _build_scoring_prompt(
        candidates=candidates,
        context_text="fixing database timeout issue",
        emotional_state={"content": 0.5, "euphoric": 0.1},
    )
    assert "database timeout" in prompt
    assert "exp-001" in prompt
    assert "content=0.50" in prompt
    assert "euphoric" not in prompt  # filtered: ≤0.1
    assert "Score each memory" in prompt


def test_build_scoring_prompt_empty_emotional():
    prompt = _build_scoring_prompt(
        candidates=[{"memory_id": "exp-001", "narrative": "test", "topic": "x", "emotion_arc": "n"}],
        context_text="test",
        emotional_state={},
    )
    assert "neutral" in prompt


# ── _parse_scoring_response ──


def test_parse_scoring_response_valid():
    candidates = [
        {"memory_id": "exp-001", "narrative": "t"},
        {"memory_id": "exp-002", "narrative": "t"},
    ]
    result = _parse_scoring_response('{"exp-001": 0.85, "exp-002": 0.10}', candidates)
    assert result == {"exp-001": 0.85, "exp-002": 0.10}


def test_parse_scoring_response_code_fence():
    candidates = [{"memory_id": "exp-abc", "narrative": "t"}]
    result = _parse_scoring_response(
        '```json\n{"exp-abc": 0.72}\n```', candidates
    )
    assert result == {"exp-abc": 0.72}


def test_parse_scoring_response_inline_json():
    candidates = [{"memory_id": "exp-xyz", "narrative": "t"}]
    result = _parse_scoring_response(
        'Sure, here are the scores: {"exp-xyz": 0.55}', candidates
    )
    assert result == {"exp-xyz": 0.55}


def test_parse_scoring_response_unknown_ids_filtered():
    candidates = [{"memory_id": "exp-real", "narrative": "t"}]
    result = _parse_scoring_response(
        '{"exp-fake": 0.9, "exp-real": 0.5}', candidates
    )
    assert result == {"exp-real": 0.5}


def test_parse_scoring_response_clamps_to_range():
    candidates = [{"memory_id": "exp-001", "narrative": "t"}]
    result = _parse_scoring_response('{"exp-001": 1.5}', candidates)
    assert result == {"exp-001": 1.0}

    result = _parse_scoring_response('{"exp-001": -0.3}', candidates)
    assert result == {"exp-001": 0.0}


def test_parse_scoring_response_garbage():
    candidates = [{"memory_id": "exp-001", "narrative": "t"}]
    assert _parse_scoring_response("not json at all", candidates) == {}


def test_parse_scoring_response_empty_string():
    assert _parse_scoring_response("", []) == {}


# ── _resolve_scoring_llm_target ──


def test_resolve_scoring_llm_target_returns_dict_or_none():
    """Smoke-test: returns None or a dict with expected keys."""
    target = _resolve_scoring_llm_target()
    if target is not None:
        assert isinstance(target, dict)
        assert "provider" in target
        assert "model" in target
        assert "active" in target


# ── score_memories_by_relevance ──


def test_score_memories_empty_candidates():
    result = score_memories_by_relevance(
        candidates=[],
        context_text="test",
        emotional_state={},
    )
    assert result == {}


def test_score_memories_returns_dict():
    """Smoke-test: returns dict, doesn't crash."""
    candidates = [
        {
            "memory_id": "exp-test-001",
            "narrative": "Bjørn testede noget",
            "topic": "test",
            "emotion_arc": "neutral → neutral",
        }
    ]
    result = score_memories_by_relevance(
        candidates=candidates,
        context_text="testing the system",
        emotional_state={"content": 0.5},
    )
    assert isinstance(result, dict)
    # May be empty if no LLM target resolves, but must not crash
    for score in result.values():
        assert 0.0 <= score <= 1.0
