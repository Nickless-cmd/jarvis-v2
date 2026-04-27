"""Unit tests for heartbeat_phases — Sense / Reflect / Act."""
from __future__ import annotations

from unittest.mock import patch

from core.services.heartbeat_phases import (
    sense_phase,
    reflect_phase,
    act_phase,
    productive_idle,
    tick_with_phases,
    _classify_activity,
    _identify_priorities,
)


def test_sense_returns_structured_signals():
    signals = sense_phase()
    assert "captured_at" in signals
    assert "active_goals" in signals
    assert "events_last_hour" in signals
    assert "context_pressure_level" in signals or signals.get("context_pressure_level") is None


def test_classify_activity_idle():
    assert _classify_activity({"tool_invocations_last_hour": 0}) == "idle"


def test_classify_activity_normal():
    assert _classify_activity({"tool_invocations_last_hour": 200}) == "normal"


def test_classify_activity_high():
    assert _classify_activity({"tool_invocations_last_hour": 1000}) == "high"


def test_priorities_empty_when_calm():
    p = _identify_priorities({
        "failed_verifies": 0, "unverified_mutations": 0,
        "context_pressure_level": "comfortable", "active_goals": [],
        "errors_last_hour": 0,
    })
    assert p == []


def test_priorities_failed_verify_triggers():
    p = _identify_priorities({"failed_verifies": 1, "unverified_mutations": 0,
                              "context_pressure_level": "comfortable",
                              "active_goals": [], "errors_last_hour": 0})
    assert "address_failed_verifications" in p


def test_priorities_high_context_triggers_compact():
    p = _identify_priorities({"failed_verifies": 0, "unverified_mutations": 0,
                              "context_pressure_level": "high",
                              "active_goals": [], "errors_last_hour": 0})
    assert "compact_context" in p


def test_reflect_picks_5min_for_high_activity():
    refl = reflect_phase({"tool_invocations_last_hour": 1000})
    assert refl["suggested_next_interval_seconds"] == 300


def test_reflect_picks_30min_for_idle():
    refl = reflect_phase({"tool_invocations_last_hour": 0})
    assert refl["suggested_next_interval_seconds"] == 1800


def test_reflect_picks_15min_for_normal():
    refl = reflect_phase({"tool_invocations_last_hour": 200})
    assert refl["suggested_next_interval_seconds"] == 900


def test_act_dispatches_to_tick_when_priorities():
    with patch("core.services.heartbeat_runtime.run_heartbeat_tick") as fake_tick:
        fake_tick.return_value = type("R", (), {"status": "ok"})()
        result = act_phase(
            signals={},
            reflection={"activity_level": "high", "priorities": ["x"]},
        )
    assert result["kind"] == "tick_dispatched"
    fake_tick.assert_called_once()


def test_act_runs_idle_when_no_priorities():
    with patch("core.services.heartbeat_phases.productive_idle",
               return_value={"kind": "productive_idle", "actions": []}):
        result = act_phase(
            signals={},
            reflection={"activity_level": "idle", "priorities": []},
        )
    assert result["kind"] == "productive_idle"


def test_productive_idle_completes_within_budget():
    result = productive_idle(budget_seconds=2.0)
    assert "actions" in result
    assert result["elapsed_seconds"] <= 5.0  # generous slack for slow CI


def test_tick_with_phases_full_pipeline():
    with patch("core.services.heartbeat_phases.sense_phase",
               return_value={"tool_invocations_last_hour": 1000, "active_goals": []}), \
         patch("core.services.heartbeat_runtime.run_heartbeat_tick") as fake_tick:
        fake_tick.return_value = type("R", (), {"status": "ok"})()
        result = tick_with_phases()
    assert result["status"] == "ok"
    assert "sense" in result["phases"]
    assert "reflect" in result["phases"]
    assert "act" in result["phases"]
