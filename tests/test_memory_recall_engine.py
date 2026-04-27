"""Unit tests for memory_recall_engine."""
from __future__ import annotations

from unittest.mock import patch

from core.services.memory_recall_engine import (
    _apply_mood_boost,
    _mood_keywords_for_boost,
    unified_recall,
    unified_recall_section,
)


def test_mood_keywords_empty_when_no_mood():
    assert _mood_keywords_for_boost({}) == set()


def test_mood_keywords_includes_dominant_dimension():
    boost = _mood_keywords_for_boost({"curiosity": 0.8, "fatigue": 0.2})
    assert "udforsk" in boost
    assert "lære" in boost


def test_mood_keywords_threshold():
    # curiosity below threshold (0.6) → no boost
    boost = _mood_keywords_for_boost({"curiosity": 0.4})
    assert boost == set()


def test_mood_boost_no_op_when_no_keywords():
    assert _apply_mood_boost("text", 1.0, set()) == 1.0


def test_mood_boost_increases_score_on_match():
    score = _apply_mood_boost("Vil gerne lære om dette", 1.0, {"lære"})
    assert score > 1.0


def test_mood_boost_caps_at_3_hits():
    text = "lære udforsk ny interessant"
    s = _apply_mood_boost(text, 1.0, {"lære", "udforsk", "ny", "interessant"})
    # 4 hits but capped at 3 -> 1.0 * (1 + 0.15*3) = 1.45
    assert abs(s - 1.45) < 0.001


def test_unified_recall_empty_query():
    result = unified_recall(query="")
    assert result["count"] == 0


def test_unified_recall_aggregates_sources():
    fake_workspace = [{
        "source": "workspace", "section": "MEMORY.md", "text": "noget om memory",
        "score": 0.9, "method": "embedding",
    }]
    fake_chronicle = [{
        "source": "chronicle", "subsource": "weekly", "section": "",
        "text": "ugen handlede om memory", "score": 0.6, "method": "keyword",
    }]
    with patch("core.services.memory_recall_engine._gather_workspace", return_value=fake_workspace), \
         patch("core.services.memory_recall_engine._gather_private_brain", return_value=[]), \
         patch("core.services.memory_recall_engine._gather_chronicle", return_value=fake_chronicle), \
         patch("core.services.memory_recall_engine._current_mood", return_value={}):
        result = unified_recall(query="memory", with_mood=False)
    assert result["count"] == 2
    sources = {r["source"] for r in result["results"]}
    assert "workspace" in sources
    assert "chronicle" in sources


def test_unified_recall_with_mood_marks_boosted():
    fake = [{"source": "workspace", "section": "", "text": "lære om X", "score": 0.5, "method": "x"}]
    with patch("core.services.memory_recall_engine._gather_workspace", return_value=fake), \
         patch("core.services.memory_recall_engine._gather_private_brain", return_value=[]), \
         patch("core.services.memory_recall_engine._gather_chronicle", return_value=[]), \
         patch("core.services.memory_recall_engine._current_mood", return_value={"curiosity": 0.85}):
        result = unified_recall(query="x", with_mood=True)
    assert result["mood_boosted"] is True


def test_unified_recall_section_returns_none_when_no_results():
    with patch("core.services.memory_recall_engine.unified_recall",
               return_value={"results": [], "count": 0}):
        assert unified_recall_section("anything") is None


def test_unified_recall_section_formats_results():
    with patch("core.services.memory_recall_engine.unified_recall", return_value={
        "results": [
            {"source": "workspace", "text": "memory note", "weighted_score": 0.9},
            {"source": "chronicle", "text": "narrative", "weighted_score": 0.7},
        ],
        "count": 2,
    }):
        section = unified_recall_section("test")
    assert section is not None
    assert "memory note" in section
    assert "narrative" in section
