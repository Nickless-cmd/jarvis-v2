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


# ─── 2026-05-22: Truth-ranked source weights regression tests ───
# After Codex+Bjørn diagnosis: private_brain (1.2) outranked workspace (1.0),
# letting hallucinated self-generated content compete with curated truth.

def test_workspace_outranks_private_brain():
    """Curated MEMORY/IDENTITY/SOUL must always beat self-generated content."""
    from core.services.memory_recall_engine import _SOURCE_WEIGHTS_DEFAULT
    assert _SOURCE_WEIGHTS_DEFAULT["workspace"] > _SOURCE_WEIGHTS_DEFAULT["private_brain"], (
        "Curated workspace files must outrank self-generated private_brain"
    )
    # specifically: workspace at least 2x private_brain to be load-bearing
    assert _SOURCE_WEIGHTS_DEFAULT["workspace"] >= 2 * _SOURCE_WEIGHTS_DEFAULT["private_brain"]


def test_chronicle_outranks_private_brain():
    """Consolidated narratives beat self-generated reflections."""
    from core.services.memory_recall_engine import _SOURCE_WEIGHTS_DEFAULT
    assert _SOURCE_WEIGHTS_DEFAULT["chronicle"] > _SOURCE_WEIGHTS_DEFAULT["private_brain"]


def test_private_brain_below_one():
    """Self-generated content must not be ranked as high as 1.0.

    Below 1.0 means even a perfect private_brain match (score 1.0)
    cannot outrank a moderate workspace match (score 0.5 * 2.0 = 1.0).
    """
    from core.services.memory_recall_engine import _SOURCE_WEIGHTS_DEFAULT
    assert _SOURCE_WEIGHTS_DEFAULT["private_brain"] < 1.0


# ─── Memory Fix Phase 1 tests (2026-06-08) ─────────────────────────


def test_compute_recall_score_perfect_match():
    """Identical query and record → score near maximum."""
    from core.services.memory_recall_engine import compute_recall_score
    emb = [0.1] * 768
    score = compute_recall_score(
        query_embedding=emb,
        record_embedding=emb,
        created_at="2026-06-08T00:00:00+00:00",
        importance=1.0,
        recall_freq=5,
    )
    # embedding_sim=1.0 * 0.4 + recency~1.0 * 0.3 + freq=1.0 * 0.2 + importance=1.0 * 0.1
    assert score > 0.95


def test_compute_recall_score_no_match():
    """Orthogonal vectors → score near minimum (only recency + importance)."""
    from core.services.memory_recall_engine import compute_recall_score
    import math
    q = [1.0] + [0.0] * 767
    r = [0.0] * 767 + [1.0]
    score = compute_recall_score(
        query_embedding=q,
        record_embedding=r,
        created_at="2026-06-08T00:00:00+00:00",
        importance=0.1,
        recall_freq=0,
    )
    # embedding_sim=0.0 * 0.4 + recency~1.0 * 0.3 + freq=0.0 * 0.2 + importance=0.1 * 0.1
    # = 0 + 0.3 + 0 + 0.01 = 0.31
    assert abs(score - 0.31) < 0.01


def test_compute_recall_score_zero_vectors():
    """Zero vectors → emb_sim=0, rest still contributes."""
    from core.services.memory_recall_engine import compute_recall_score
    score = compute_recall_score(
        query_embedding=[0.0] * 768,
        record_embedding=[0.0] * 768,
        created_at="2026-06-08T00:00:00+00:00",
        importance=0.5,
        recall_freq=0,
    )
    # emb=0, recency~1.0 * 0.3, freq=0, imp=0.5*0.1=0.05
    assert 0.3 <= score <= 0.4


def test_compute_recall_score_old_record():
    """Record from long ago → recency component near zero."""
    from core.services.memory_recall_engine import compute_recall_score
    from datetime import datetime, timezone, timedelta
    old = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    emb = [0.1] * 768
    score = compute_recall_score(
        query_embedding=emb,
        record_embedding=emb,
        created_at=old,
        importance=0.5,
        recall_freq=0,
    )
    # emb=1.0*0.4=0.4, recency~0.017*0.3=0.005, freq=0, imp=0.5*0.1=0.05
    # total ~0.455
    assert score < 0.6
    assert score > 0.3


def test_compute_recall_score_string_datetime():
    """Accepts ISO string or datetime object for created_at."""
    from core.services.memory_recall_engine import compute_recall_score
    from datetime import datetime, timezone
    emb = [0.1] * 768
    score_str = compute_recall_score(
        query_embedding=emb, record_embedding=emb,
        created_at="2026-06-08T00:00:00+00:00",
    )
    score_dt = compute_recall_score(
        query_embedding=emb, record_embedding=emb,
        created_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
    )
    assert abs(score_str - score_dt) < 0.01


def test_compute_recall_score_without_timezone():
    """Naive datetime gets treated as UTC."""
    from core.services.memory_recall_engine import compute_recall_score
    score = compute_recall_score(
        query_embedding=[0.1] * 768,
        record_embedding=[0.1] * 768,
        created_at="2026-06-08T00:00:00",  # no tz
        importance=0.5,
        recall_freq=0,
    )
    assert 0.7 <= score <= 1.0


def test_cold_tier_recall_empty_query():
    """Empty query returns no results."""
    from core.services.memory_recall_engine import cold_tier_recall
    result = cold_tier_recall(query="")
    assert result["count"] == 0
    assert result["status"] == "ok"


def test_cold_tier_recall_sources_structure():
    """Returns expected metadata keys."""
    from core.services.memory_recall_engine import cold_tier_recall
    result = cold_tier_recall(query="test", with_mood=False)
    assert "sources_searched" in result
    assert "quality_threshold" in result
    assert "tier" in result
    assert result["tier"] == "cold"


def test_cold_tier_recall_can_exclude_private_brain():
    """include_private_brain=False → only workspace+chronicle searched."""
    from core.services.memory_recall_engine import cold_tier_recall
    result = cold_tier_recall(query="test", with_mood=False, include_private_brain=False)
    assert "private_brain" not in result.get("sources_searched", [])


def test_cold_tier_recall_includes_private_brain_by_default():
    """Default includes private_brain in searched sources."""
    from core.services.memory_recall_engine import cold_tier_recall
    result = cold_tier_recall(query="test", with_mood=False, include_private_brain=True)
    assert "private_brain" in result.get("sources_searched", [])


def test_private_brain_has_low_weight():
    """Private brain results always have lower weight than workspace."""
    from core.services.memory_recall_engine import _SOURCE_WEIGHTS_DEFAULT
    assert _SOURCE_WEIGHTS_DEFAULT["private_brain"] == 0.5
    assert _SOURCE_WEIGHTS_DEFAULT["workspace"] >= 2 * _SOURCE_WEIGHTS_DEFAULT["private_brain"]
