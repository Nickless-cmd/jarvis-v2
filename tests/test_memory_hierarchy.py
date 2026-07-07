"""Unit tests for memory_hierarchy."""
from __future__ import annotations

from unittest.mock import patch

from core.services.memory_hierarchy import (
    _hot_tier_snapshot,
    _warm_tier_snapshot,
    _cold_tier_search,
    recall_before_act,
    recall_before_act_summary,
)


def test_hot_tier_returns_signals():
    with patch("core.services.heartbeat_phases.sense_phase",
               return_value={"mood_name": "curiosity", "active_goals": [],
                             "events_last_hour": 5, "context_pressure_level": "comfortable"}):
        snap = _hot_tier_snapshot()
    assert snap["tier"] == "hot"
    assert "signals" in snap


def test_warm_tier_includes_active_goals():
    with patch("core.services.autonomous_goals.list_goals", return_value=[
        {"title": "test goal", "priority": "high"}
    ]), patch("core.services.chronicle_engine.get_chronicle_context_for_prompt",
              return_value=""):
        snap = _warm_tier_snapshot()
    assert snap["tier"] == "warm"
    assert len(snap["active_goals"]) == 1
    assert snap["active_goals"][0]["title"] == "test goal"


def test_warm_tier_searches_workspace_when_query_given():
    with patch("core.services.autonomous_goals.list_goals", return_value=[]), \
         patch("core.services.memory_search.search_memory", return_value=[
             {"source": "MEMORY.md", "section": "x", "text": "found note"}
         ]), patch("core.services.chronicle_engine.get_chronicle_context_for_prompt",
                   return_value=""):
        snap = _warm_tier_snapshot(query="test")
    assert "workspace_hits" in snap
    assert len(snap["workspace_hits"]) == 1


def test_cold_tier_skips_short_query():
    snap = _cold_tier_search(query="ab")
    assert snap["results"] == []


def test_cold_tier_uses_cold_tier_recall():
    # 2026-06-08 Memory Fix Phase 1: _cold_tier_search now calls
    # cold_tier_recall() (quality-scored) rather than unified_recall() directly.
    with patch("core.services.memory_recall_engine.cold_tier_recall", return_value={
        "results": [
            {"source": "private_brain", "text": "deep memory note", "weighted_score": 0.8},
        ],
        "mood_boosted": True,
    }):
        snap = _cold_tier_search(query="memory architecture")
    assert len(snap["results"]) == 1
    assert snap["mood_boosted"] is True


def test_recall_before_act_assembles_all_tiers():
    with patch("core.services.heartbeat_phases.sense_phase", return_value={"active_goals": []}), \
         patch("core.services.autonomous_goals.list_goals", return_value=[]), \
         patch("core.services.memory_search.search_memory", return_value=[]), \
         patch("core.services.chronicle_engine.get_chronicle_context_for_prompt",
               return_value=""), \
         patch("core.services.memory_recall_engine.unified_recall",
               return_value={"results": [], "mood_boosted": False}):
        bundle = recall_before_act(query="test query", include_cold=True)
    assert "hot" in bundle
    assert "warm" in bundle
    assert "cold" in bundle


def test_recall_before_act_skips_cold_when_no_query():
    with patch("core.services.heartbeat_phases.sense_phase", return_value={"active_goals": []}), \
         patch("core.services.autonomous_goals.list_goals", return_value=[]), \
         patch("core.services.chronicle_engine.get_chronicle_context_for_prompt",
               return_value=""):
        bundle = recall_before_act(query="", include_cold=True)
    assert "cold" not in bundle


def test_summary_returns_none_when_nothing_to_show():
    with patch("core.services.memory_hierarchy.recall_before_act", return_value={
        "hot": {"signals": {}}, "warm": {}, "cold": {"results": []},
    }):
        assert recall_before_act_summary() is None


def test_summary_includes_active_goals():
    with patch("core.services.memory_hierarchy.recall_before_act", return_value={
        "hot": {"signals": {"active_goals": [{"title": "important goal"}]}},
        "warm": {}, "cold": {"results": []},
    }):
        out = recall_before_act_summary()
    assert out is not None
    assert "important goal" in out


def test_summary_lists_cold_tier_results():
    with patch("core.services.memory_hierarchy.recall_before_act", return_value={
        "hot": {"signals": {}},
        "warm": {},
        "cold": {"results": [
            {"source": "workspace", "text": "found this in cold storage"},
        ]},
    }):
        out = recall_before_act_summary("query")
    assert "found this in cold storage" in out


# ─── 2026-06-08: Cold-tier quality-gate tests ───
# The 2026-05-22 hard exclusion of private_brain was deliberately replaced by a
# quality gate (Memory Fix Phase 1): good self-generated content surfaces,
# hallucinations are filtered by compute_recall_score(). _cold_tier_search now
# delegates to cold_tier_recall() which applies the gate.

def test_cold_tier_quality_gates_private_brain():
    """Cold-tier delegates to cold_tier_recall() with an explicit quality
    threshold and include_private_brain flag (quality gate, not hard exclusion)."""
    from unittest.mock import patch
    from core.services.memory_hierarchy import _cold_tier_search

    with patch("core.services.memory_recall_engine.cold_tier_recall") as mock_recall:
        mock_recall.return_value = {"results": [], "mood_boosted": False}
        _cold_tier_search(query="test query")
        assert mock_recall.called
        call_kwargs = mock_recall.call_args.kwargs
        # Quality threshold is passed through (default 0.25) — this is the gate
        # that replaced the old hard private_brain exclusion.
        assert "quality_threshold" in call_kwargs
        assert "include_private_brain" in call_kwargs


def test_cold_tier_skips_short_query():
    from core.services.memory_hierarchy import _cold_tier_search
    result = _cold_tier_search(query="ab")  # < 3 chars
    assert result["results"] == []
