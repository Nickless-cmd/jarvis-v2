"""End-to-end: verify decision-signal events fire and prompts no longer
contain the legacy escalation language.

After the 2026-05-07 pivot, signals are delivered as chat-delta during
the agentic loop, not as a prompt section. So we test:
1. fired_decisions_section() works correctly when triggers match (the
   underlying mechanism that the agentic-loop emit-block uses)
2. decision_signal.fired events get published with correct payload
3. The legacy enforcement_section is suppressed by the killswitch
"""
import pytest

from core.services import decision_signals as ds
import core.services.decision_triggers  # populate registry  # noqa: F401


def _ctx(**overrides):
    base = dict(
        user_message="hvad sker der?", session_id=None, run_id=None,
        consecutive_tool_only_rounds=0, recent_tool_calls=[],
        recent_assistant_text="", agentic_round_seq=0,
        timestamp="2026-05-07T12:00:00+00:00",
    )
    base.update(overrides)
    return ds.TriggerContext(**base)


def test_loop_nudge_fires_via_registry_pipeline(monkeypatch):
    """When consecutive_tool_only_rounds == 5, the registry-driven
    loop_nudge_5_rounds trigger fires and emits a FiredDecision."""
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "dec_d56d89ceec24", "trigger_name": "loop_nudge_5_rounds"}],
    )
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: None)
    monkeypatch.setattr(ds, "_read_last_fired_seq", lambda d_id: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_write_last_fired_seq", lambda d_id, seq, ts: None)
    published: list[dict] = []
    monkeypatch.setattr(
        ds, "_publish_fired_event",
        lambda **kwargs: published.append(kwargs),
    )

    fired = ds.evaluate_decision_triggers(_ctx(consecutive_tool_only_rounds=5, agentic_round_seq=5))
    assert len(fired) == 1
    assert fired[0].decision_id == "dec_d56d89ceec24"
    assert fired[0].trigger_name == "loop_nudge_5_rounds"
    assert "round 5" in fired[0].context_summary

    assert len(published) == 1
    assert published[0]["decision_id"] == "dec_d56d89ceec24"
    assert published[0]["trigger_name"] == "loop_nudge_5_rounds"


def test_backend_unresolved_fires_via_registry_pipeline(monkeypatch):
    """3 consecutive Jarvis-backend tool calls without resolution → fires."""
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "dec_56d4dbb03e22", "trigger_name": "backend_unresolved_3_calls"}],
    )
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: None)
    monkeypatch.setattr(ds, "_read_last_fired_seq", lambda d_id: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)

    calls = [
        {"function": {"name": "read_file", "arguments": {"path": "/media/projects/jarvis-v2/core/services/x.py"}}},
        {"function": {"name": "grep", "arguments": {"path": "/media/projects/jarvis-v2/core"}}},
        {"function": {"name": "read_file", "arguments": {"path": "/media/projects/jarvis-v2/apps/api/y.py"}}},
    ]
    fired = ds.evaluate_decision_triggers(_ctx(recent_tool_calls=calls))
    assert len(fired) == 1
    assert fired[0].decision_id == "dec_56d4dbb03e22"


def test_killswitch_suppresses_all_signals(monkeypatch):
    """When decision_signals_enabled is False, nothing fires."""
    class FakeS:
        decision_signals_enabled = False
    monkeypatch.setattr(ds, "RuntimeSettings", lambda: FakeS())
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "dec_d56d89ceec24", "trigger_name": "loop_nudge_5_rounds"}],
    )
    fired = ds.evaluate_decision_triggers(_ctx(consecutive_tool_only_rounds=5))
    assert fired == []


def test_legacy_enforcement_section_suppressed_when_killswitch_on():
    """The killswitch must remove the legacy escalation language from prompt."""
    from core.services.decision_enforcement import enforcement_section
    out = enforcement_section()
    # With default settings (decision_signals_enabled=True), legacy returns None
    assert out is None
