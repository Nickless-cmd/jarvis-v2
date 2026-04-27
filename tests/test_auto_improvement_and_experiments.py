"""Unit tests for auto_improvement_proposer + prompt_variant_tracker + experiment_runner."""
from __future__ import annotations

from unittest.mock import patch

import core.services.auto_improvement_proposer as aip
import core.services.prompt_variant_tracker as pvt
import core.services.experiment_runner as exr


# ── auto_improvement_proposer ──


def test_is_safe_target_blocks_protected_files():
    assert aip._is_safe_target("update SOUL.md") is False
    assert aip._is_safe_target("modify IDENTITY.md") is False
    assert aip._is_safe_target("rewrite MANIFEST.md") is False
    assert aip._is_safe_target("change tool description") is True


def test_is_safe_target_blocks_protected_modules():
    assert aip._is_safe_target("core.services.auto_improvement_proposer:foo") is False
    assert aip._is_safe_target("core.services.plan_proposals:bar") is False
    assert aip._is_safe_target("core.services.context_window_manager:baz") is True


def test_check_tick_quality_returns_none_when_stable():
    with patch("core.services.agent_self_evaluation.tick_quality_summary",
               return_value={"trend": "stable", "avg_score": 70, "count": 10}):
        assert aip._check_tick_quality_degraded() is None


def test_check_tick_quality_returns_proposal_when_degrading():
    with patch("core.services.agent_self_evaluation.tick_quality_summary",
               return_value={"trend": "degrading", "avg_score": 45, "count": 10}):
        result = aip._check_tick_quality_degraded()
    assert result is not None
    assert "degraderende" in result["title"]


def test_check_tick_quality_skips_when_too_few_samples():
    with patch("core.services.agent_self_evaluation.tick_quality_summary",
               return_value={"trend": "degrading", "avg_score": 40, "count": 2}):
        assert aip._check_tick_quality_degraded() is None


def test_check_stale_goals_no_op_when_none():
    with patch("core.services.agent_self_evaluation.detect_stale_goals", return_value=[]):
        assert aip._check_stale_goals() is None


def test_check_stale_goals_returns_proposal():
    with patch("core.services.agent_self_evaluation.detect_stale_goals", return_value=[
        {"goal_id": "g1", "title": "stagnerer", "priority": "high"},
    ]):
        result = aip._check_stale_goals()
    assert result is not None
    assert "stagnerer" in result["why"]


def test_generate_proposals_files_via_plan_proposals():
    with patch.object(aip, "_check_tick_quality_degraded", return_value={
        "title": "T", "why": "W", "steps": ["s1", "s2"], "kind": "tick_quality_degraded",
    }), patch.object(aip, "_check_stale_goals", return_value=None), \
       patch.object(aip, "_check_decision_adherence", return_value=None), \
       patch.object(aip, "_check_provider_health_chronic", return_value=None), \
       patch("core.services.plan_proposals.propose_plan",
             return_value={"status": "ok", "plan_id": "plan-x"}):
        result = aip.generate_improvement_proposals()
    assert result["count"] == 1
    assert result["proposed"][0]["plan_id"] == "plan-x"


# ── prompt_variant_tracker ──


def test_log_variant_outcome_validates_inputs(monkeypatch):
    monkeypatch.setattr(pvt, "load_json", lambda *a, **k: [])
    monkeypatch.setattr(pvt, "save_json", lambda *a, **k: None)
    result = pvt.log_variant_outcome(scope="", variant_label="x", outcome_score=50)
    assert result["status"] == "error"
    result = pvt.log_variant_outcome(scope="x", variant_label="", outcome_score=50)
    assert result["status"] == "error"
    result = pvt.log_variant_outcome(scope="x", variant_label="y", outcome_score=200)
    assert result["status"] == "error"


def test_log_variant_outcome_persists(monkeypatch):
    state: list = []
    monkeypatch.setattr(pvt, "load_json", lambda *a, **k: list(state))
    monkeypatch.setattr(pvt, "save_json", lambda k, v: state.clear() or state.extend(v))
    result = pvt.log_variant_outcome(scope="awareness.test", variant_label="A", outcome_score=80)
    assert result["status"] == "ok"
    assert len(state) == 1


def test_variant_performance_filters_by_min_samples(monkeypatch):
    state = [
        {"scope": "x", "variant_label": "A", "outcome_score": 80},
        {"scope": "x", "variant_label": "A", "outcome_score": 70},
        {"scope": "x", "variant_label": "B", "outcome_score": 50},
    ]
    monkeypatch.setattr(pvt, "load_json", lambda *a, **k: list(state))
    perf = pvt.variant_performance(min_samples=3)
    # Only A might qualify with 2 samples — both filtered with min_samples=3
    assert all(v["n_samples"] >= 3 for v in perf["variants"])


def test_winning_variant_returns_best(monkeypatch):
    state = [{"scope": "x", "variant_label": lbl, "outcome_score": s}
             for lbl, s in [("A", 90), ("A", 85), ("A", 88), ("A", 80), ("A", 92),
                            ("B", 60), ("B", 55), ("B", 58), ("B", 50), ("B", 62)]]
    monkeypatch.setattr(pvt, "load_json", lambda *a, **k: list(state))
    winner = pvt.winning_variant("x")
    assert winner is not None
    assert winner["variant_label"] == "A"


# ── experiment_runner ──


def test_start_experiment_creates_active_record(monkeypatch):
    state: dict = {}
    monkeypatch.setattr(exr, "_load", lambda: dict(state))
    monkeypatch.setattr(exr, "_save", lambda d: state.clear() or state.update(d))
    result = exr.start_experiment(
        scope="awareness.x", variant_a_label="A", variant_a_text="text A",
        variant_b_label="B", variant_b_text="text B", trials_target=10,
    )
    assert result["status"] == "ok"
    eid = result["experiment_id"]
    assert state[eid]["status"] == "active"


def test_get_active_variant_alternates(monkeypatch):
    state: dict = {
        "exp-1": {
            "experiment_id": "exp-1", "scope": "x",
            "variant_a": {"label": "A", "text": "ta"},
            "variant_b": {"label": "B", "text": "tb"},
            "trials_target": 10, "trials_done": 0,
            "next_pick": "a", "status": "active",
        }
    }
    monkeypatch.setattr(exr, "_load", lambda: dict(state))
    monkeypatch.setattr(exr, "_save", lambda d: state.clear() or state.update(d))
    first = exr.get_active_variant("x")
    second = exr.get_active_variant("x")
    assert first["variant_pick"] != second["variant_pick"]


def test_get_active_variant_marks_ready_when_target_reached(monkeypatch):
    state: dict = {
        "exp-1": {
            "experiment_id": "exp-1", "scope": "x",
            "variant_a": {"label": "A", "text": "ta"},
            "variant_b": {"label": "B", "text": "tb"},
            "trials_target": 1, "trials_done": 0,
            "next_pick": "a", "status": "active",
        }
    }
    monkeypatch.setattr(exr, "_load", lambda: dict(state))
    monkeypatch.setattr(exr, "_save", lambda d: state.clear() or state.update(d))
    exr.get_active_variant("x")
    assert state["exp-1"]["status"] == "ready_for_analysis"


def test_get_active_variant_returns_none_when_no_active(monkeypatch):
    monkeypatch.setattr(exr, "_load", lambda: {})
    assert exr.get_active_variant("x") is None
