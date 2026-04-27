"""Unit tests for agent_self_evaluation."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.agent_self_evaluation import (
    evaluate_tick_quality,
    tick_quality_summary,
    detect_stale_goals,
    stale_goals_section,
    decision_adherence_summary,
    self_evaluation_section,
)


def _fake_tick(act_kind="productive_idle", priorities=None, actions=None, elapsed_ms=1000):
    return {
        "elapsed_ms": elapsed_ms,
        "phases": {
            "sense": {
                "mood_name": "x", "active_goals": [], "events_last_hour": 0,
                "context_pressure_level": "comfortable", "errors_last_hour": 0,
            },
            "reflect": {"priorities": priorities or []},
            "act": {
                "kind": act_kind,
                "result": {"actions": actions or []},
            },
        },
    }


def test_evaluate_idle_tick_with_no_actions():
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"):
        result = evaluate_tick_quality(tick_result=_fake_tick())
    assert "score" in result
    assert "evaluated_at" in result
    # No priorities + no actions = lower score
    assert result["score"] < 60


def test_evaluate_high_quality_tick():
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"):
        result = evaluate_tick_quality(tick_result=_fake_tick(
            act_kind="tick_dispatched",
            priorities=["compact_context", "verify_mutations"],
            elapsed_ms=2000,
        ))
    assert result["score"] >= 70


def test_evaluate_idle_with_actions():
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"):
        result = evaluate_tick_quality(tick_result=_fake_tick(
            act_kind="productive_idle",
            actions=["personality_snapshot", "composite_candidates:2"],
            elapsed_ms=5000,
        ))
    assert result["score"] >= 50


def test_summary_no_evals_returns_empty():
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]):
        s = tick_quality_summary()
    assert s["count"] == 0
    assert s["avg_score"] is None


def test_summary_calculates_trend_improving():
    now = datetime.now(UTC)
    evals = [
        {"evaluated_at": (now - timedelta(days=6)).isoformat(), "score": 30},
        {"evaluated_at": (now - timedelta(days=5)).isoformat(), "score": 35},
        {"evaluated_at": (now - timedelta(days=4)).isoformat(), "score": 40},
        {"evaluated_at": (now - timedelta(days=1)).isoformat(), "score": 80},
        {"evaluated_at": (now - timedelta(hours=12)).isoformat(), "score": 85},
        {"evaluated_at": now.isoformat(), "score": 90},
    ]
    with patch("core.services.agent_self_evaluation.load_json", return_value=evals):
        s = tick_quality_summary(days=7)
    assert s["count"] == 6
    assert s["trend"] == "improving"


def test_detect_stale_goals_returns_old_ones():
    old_iso = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    fresh_iso = datetime.now(UTC).isoformat()
    with patch("core.services.autonomous_goals.list_goals", return_value=[
        {"goal_id": "g1", "title": "stale one", "priority": "high",
         "updated_at": old_iso, "created_at": old_iso},
        {"goal_id": "g2", "title": "fresh one", "priority": "low",
         "updated_at": fresh_iso, "created_at": fresh_iso},
    ]):
        stale = detect_stale_goals(stale_days=3)
    assert len(stale) == 1
    assert stale[0]["title"] == "stale one"


def test_stale_goals_section_returns_none_when_clean():
    with patch("core.services.agent_self_evaluation.detect_stale_goals", return_value=[]):
        assert stale_goals_section() is None


def test_stale_goals_section_lists_when_present():
    with patch("core.services.agent_self_evaluation.detect_stale_goals", return_value=[
        {"goal_id": "g1", "title": "stagnerer", "priority": "high",
         "last_update": "2026-04-20T00:00:00Z", "days_stale": 3},
    ]):
        section = stale_goals_section()
    assert section is not None
    assert "stagnerer" in section


def test_adherence_returns_none_when_no_decisions():
    with patch("core.runtime.db.list_cognitive_decisions", return_value=[]):
        result = decision_adherence_summary()
    assert result["score"] is None


def test_adherence_calculates_score():
    with patch("core.runtime.db.list_cognitive_decisions", return_value=[
        {"status": "applied"}, {"status": "applied"}, {"status": "applied"},
        {"status": "revoked"},
    ]):
        result = decision_adherence_summary()
    assert result["score"] == 75.0
    assert result["flag"] is False  # 75 > 60


def test_adherence_flags_low_score():
    with patch("core.runtime.db.list_cognitive_decisions", return_value=[
        {"status": "revoked"}, {"status": "revoked"}, {"status": "applied"},
    ]):
        result = decision_adherence_summary()
    assert result["flag"] is True


def test_self_evaluation_section_combines_all():
    with patch("core.services.agent_self_evaluation.tick_quality_summary",
               return_value={"avg_score": 65, "trend": "stable", "count": 10}), \
         patch("core.services.agent_self_evaluation.decision_adherence_summary",
               return_value={"score": 50, "flag": True}), \
         patch("core.services.agent_self_evaluation.detect_stale_goals",
               return_value=[{"goal_id": "g1"}]):
        section = self_evaluation_section()
    assert section is not None
    assert "65" in section
    assert "50%" in section
    assert "stagnerer" in section
