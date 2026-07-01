"""Tests for MC dashboard-endpoints (scheduled-tasks / run-detail / daily-costs)."""
from __future__ import annotations

from apps.api.jarvis_api.routes import mission_control_dashboard as mcd


def test_scheduled_tasks_shape(isolated_runtime):
    out = mcd.mc_scheduled_tasks(limit=5)
    assert isinstance(out["items"], list)
    assert "pending_count" in out["summary"]


def test_costs_daily_shape(isolated_runtime):
    out = mcd.mc_costs_daily(days=7)
    assert isinstance(out["days"], list)
    assert len(out["days"]) <= 7


def test_run_detail_missing_run_is_safe(isolated_runtime):
    out = mcd.mc_run_detail("does-not-exist")
    assert out["found"] is False
    assert out["run"] is None
    assert out["steps"] == []


def test_event_to_step_picks_summary():
    class _Row(dict):
        def __getitem__(self, k):
            return dict.__getitem__(self, k)

    row = _Row(kind="tool.invoked", created_at="2026-07-01T00:00:00Z",
               payload_json='{"run_id": "r1", "tool": "operator_bash", "reason": "kør ls"}')
    step = mcd._event_to_step(row)
    assert step["tool"] == "operator_bash"
    assert step["summary"] == "kør ls"
    assert step["kind"] == "tool.invoked"
