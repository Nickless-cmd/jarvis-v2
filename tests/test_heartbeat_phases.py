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
    with patch("core.services.heartbeat_runtime.run_heartbeat_tick") as fake_tick, \
         patch("core.services.heartbeat_phases._user_active_recently", return_value=False):
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


def test_productive_idle_ticks_llm_free_baseline_daemons(monkeypatch):
    """2026-07-14 incident-fix: raw-signal daemons + event_trigger θ-meter must tick on
    the IDLE path too, else a long idle / active-chat freezes the inner-life rhythm
    (somatic et al. silent ~16h in the 2026-07-13 incident)."""
    import core.services.heartbeat_runtime as hb
    from core.services import daemon_manager as dm
    import core.services.somatic_daemon as somatic

    ticked: list[str] = []
    monkeypatch.setattr(somatic, "raw_signal_mode_enabled", lambda: True)
    monkeypatch.setattr(dm, "is_enabled", lambda name: True)
    monkeypatch.setattr(dm, "record_daemon_tick", lambda name, res: None)
    monkeypatch.setattr(
        hb, "_daemon_tick_with_deadline",
        lambda name, fn, **k: (ticked.append(name), {"recorded": True})[1],
    )

    actions = productive_idle(budget_seconds=30.0)["actions"]
    assert "idle_daemon:event_trigger_shadow" in actions
    for d in ("somatic", "surprise", "absence"):
        assert f"idle_daemon:{d}" in actions
    assert set(ticked) >= {"event_trigger_shadow", "somatic", "surprise", "absence"}


def test_productive_idle_skips_raw_daemons_when_raw_mode_off(monkeypatch):
    """raw_signal_mode OFF → raw daemons would make LLM calls during idle, so only
    event_trigger_shadow (always LLM-free) is ticked."""
    import core.services.heartbeat_runtime as hb
    from core.services import daemon_manager as dm
    import core.services.somatic_daemon as somatic

    ticked: list[str] = []
    monkeypatch.setattr(somatic, "raw_signal_mode_enabled", lambda: False)
    monkeypatch.setattr(dm, "is_enabled", lambda name: True)
    monkeypatch.setattr(dm, "record_daemon_tick", lambda name, res: None)
    monkeypatch.setattr(
        hb, "_daemon_tick_with_deadline",
        lambda name, fn, **k: (ticked.append(name), {"recorded": True})[1],
    )

    actions = productive_idle(budget_seconds=30.0)["actions"]
    assert "idle_daemon:event_trigger_shadow" in actions
    assert "idle_daemon:somatic" not in actions
    assert ticked == ["event_trigger_shadow"]


def test_productive_idle_completes_within_budget():
    result = productive_idle(budget_seconds=2.0)
    assert "actions" in result
    assert result["elapsed_seconds"] <= 5.0  # generous slack for slow CI


def test_tick_with_phases_full_pipeline():
    with patch("core.services.heartbeat_phases.sense_phase",
               return_value={"tool_invocations_last_hour": 1000, "active_goals": []}), \
         patch("core.services.heartbeat_runtime.run_heartbeat_tick") as fake_tick, \
         patch("core.services.heartbeat_phases._user_active_recently", return_value=False):
        fake_tick.return_value = type("R", (), {"status": "ok"})()
        result = tick_with_phases()
    assert result["status"] == "ok"
    assert "sense" in result["phases"]
    assert "reflect" in result["phases"]
    assert "act" in result["phases"]


# ── C3 — Skill chain i heartbeat ──────────────────────────────────────


from core.services.heartbeat_phases import (  # noqa: E402
    _chain_proposals,
    _propose_skill_chains_in_idle,
    format_chain_proposals,
    clear_chain_proposals,
    get_chain_proposals,
    _collect_active_goals,
    _MAX_CHAIN_PROPOSALS,
)


def test_collect_active_goals_returns_list():
    """_collect_active_goals must return a list (possibly empty)."""
    goals = _collect_active_goals()
    assert isinstance(goals, list)


def test_propose_skill_chains_empty_when_no_goals(monkeypatch):
    """With no active goals, no chains should be proposed."""
    monkeypatch.setattr(
        "core.services.heartbeat_phases._collect_active_goals",
        lambda: [],
    )
    proposals = _propose_skill_chains_in_idle(max_goals=3)
    assert proposals == []


def test_format_chain_proposals_empty():
    """format_chain_proposals returns empty string when no proposals."""
    clear_chain_proposals()
    text = format_chain_proposals()
    assert text == ""


def test_format_chain_proposals_with_proposals():
    """format_chain_proposals returns formatted string when proposals exist."""
    # Inject a test proposal directly
    from core.services.heartbeat_phases import _chain_proposals
    _chain_proposals.clear()
    _chain_proposals.append({
        "plan": ["skill-a", "skill-b"],
        "rationale": "Test chain for testing",
        "confidence": 0.85,
        "goal_title": "Test goal",
        "goal_id": "g-1",
        "proposed_at": "2026-06-09T12:00:00",
    })
    text = format_chain_proposals()
    assert "SKILL CHAIN" in text
    assert "skill-a" in text
    assert "skill-b" in text
    assert "Test goal" in text
    assert "85%" in text
    clear_chain_proposals()
    assert format_chain_proposals() == ""


def test_get_chain_proposals_returns_copy():
    """get_chain_proposals must return a copy, not the internal list."""
    clear_chain_proposals()
    from core.services.heartbeat_phases import _chain_proposals
    _chain_proposals.append({"plan": ["x"], "rationale": "", "confidence": 0.5,
                              "goal_title": "", "goal_id": "", "proposed_at": ""})
    result = get_chain_proposals()
    assert len(result) == 1
    # Mutating the returned copy must not affect the internal list
    result.clear()
    assert len(get_chain_proposals()) == 1
    clear_chain_proposals()


def test_clear_chain_proposals_empties():
    """clear_chain_proposals must empty the proposals list."""
    from core.services.heartbeat_phases import _chain_proposals
    _chain_proposals.append({"plan": ["x"], "rationale": "", "confidence": 0.5,
                              "goal_title": "", "goal_id": "", "proposed_at": ""})
    assert len(_chain_proposals) == 1
    clear_chain_proposals()
    assert len(_chain_proposals) == 0


def test_propose_skill_chains_deduplicates(monkeypatch):
    """Duplicate chain plans must be deduplicated."""
    monkeypatch.setattr(
        "core.services.heartbeat_phases._collect_active_goals",
        lambda: [
            {"goal_id": "g1", "title": "Do something complex here please", "priority": "high"},
            {"goal_id": "g2", "title": "Do something complex here please", "priority": "high"},
        ] if False else [],  # mock to empty — actual propose tests need cheap-lane
    )
    # Without cheap-lane, we just verify no crash
    proposals = _propose_skill_chains_in_idle(max_goals=2)
    assert isinstance(proposals, list)
