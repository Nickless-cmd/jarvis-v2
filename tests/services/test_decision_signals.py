import pytest
from core.services import decision_signals as ds


def _ctx(**overrides):
    """Build a TriggerContext with sensible defaults for tests."""
    base = dict(
        user_message="hej",
        session_id=None,
        run_id=None,
        consecutive_tool_only_rounds=0,
        recent_tool_calls=[],
        recent_assistant_text="",
        agentic_round_seq=0,
        timestamp="2026-05-07T12:00:00+00:00",
    )
    base.update(overrides)
    return ds.TriggerContext(**base)


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch):
    """Each test starts with a clean registry."""
    monkeypatch.setattr(ds, "_TRIGGER_REGISTRY", {})


def test_register_adds_to_registry():
    ds.register("test_trigger", lambda ctx: True)
    assert "test_trigger" in ds._TRIGGER_REGISTRY


def test_register_duplicate_overwrites():
    ds.register("t", lambda ctx: True)
    ds.register("t", lambda ctx: False, cooldown_seconds=10)
    spec = ds._TRIGGER_REGISTRY["t"]
    assert spec.cooldown_seconds == 10


def test_evaluate_returns_empty_when_no_active_decisions(monkeypatch):
    monkeypatch.setattr(ds, "_active_decisions_with_triggers", lambda: [])
    out = ds.evaluate_decision_triggers(_ctx())
    assert out == []


def test_evaluate_skips_unknown_trigger_name(monkeypatch):
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "d1", "trigger_name": "missing"}],
    )
    out = ds.evaluate_decision_triggers(_ctx())
    assert out == []


def test_evaluate_fires_when_trigger_returns_true(monkeypatch):
    ds.register("always", lambda ctx: True)
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "d1", "trigger_name": "always"}],
    )
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)
    out = ds.evaluate_decision_triggers(_ctx())
    assert len(out) == 1
    assert out[0].decision_id == "d1"
    assert out[0].trigger_name == "always"


def test_evaluate_sandboxes_failing_trigger(monkeypatch):
    def boom(ctx):
        raise RuntimeError("trigger crashed")
    ds.register("boom", boom)
    ds.register("ok", lambda ctx: True)
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [
            {"decision_id": "d_boom", "trigger_name": "boom"},
            {"decision_id": "d_ok", "trigger_name": "ok"},
        ],
    )
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)
    out = ds.evaluate_decision_triggers(_ctx())
    # boom is skipped, ok still fires
    assert len(out) == 1
    assert out[0].decision_id == "d_ok"


def test_killswitch_off_returns_empty(monkeypatch):
    class FakeS:
        decision_signals_enabled = False
    monkeypatch.setattr(ds, "RuntimeSettings", lambda: FakeS())
    out = ds.evaluate_decision_triggers(_ctx())
    assert out == []


def test_cooldown_seconds_blocks_within_window(monkeypatch):
    ds.register("t", lambda ctx: True, cooldown_seconds=600)
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "d1", "trigger_name": "t"}],
    )
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)

    # First call: never fired before, fires
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: None)
    out1 = ds.evaluate_decision_triggers(_ctx())
    assert len(out1) == 1

    # Second call: fired 60 seconds ago, blocked
    from datetime import datetime, timezone, timedelta
    recent_iso = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: recent_iso)
    out2 = ds.evaluate_decision_triggers(_ctx())
    assert out2 == []

    # Third call: fired 10 minutes ago, fires again
    long_ago = (datetime.now(timezone.utc) - timedelta(seconds=601)).isoformat()
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: long_ago)
    out3 = ds.evaluate_decision_triggers(_ctx())
    assert len(out3) == 1


def test_cooldown_turns_blocks_within_window(monkeypatch):
    ds.register("t", lambda ctx: True, cooldown_turns=2)
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "d1", "trigger_name": "t"}],
    )
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_write_last_fired_seq", lambda d_id, seq, ts: None)

    # First call at round 5: fires
    monkeypatch.setattr(ds, "_read_last_fired_seq", lambda d_id: None)
    out1 = ds.evaluate_decision_triggers(_ctx(agentic_round_seq=5))
    assert len(out1) == 1

    # Round 6: 1 turn after fire, blocked (cooldown_turns=2)
    monkeypatch.setattr(ds, "_read_last_fired_seq", lambda d_id: 5)
    out2 = ds.evaluate_decision_triggers(_ctx(agentic_round_seq=6))
    assert out2 == []

    # Round 7: 2 turns after fire, fires
    out3 = ds.evaluate_decision_triggers(_ctx(agentic_round_seq=7))
    assert len(out3) == 1


def test_fired_decisions_section_returns_none_when_no_fires(monkeypatch):
    monkeypatch.setattr(ds, "_active_decisions_with_triggers", lambda: [])
    out = ds.fired_decisions_section(_ctx())
    assert out is None


def test_fired_decisions_section_format_when_fired(monkeypatch):
    ds.register("loop_nudge_5_rounds", lambda ctx: True, cooldown_turns=1)
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "dec_xxx", "trigger_name": "loop_nudge_5_rounds"}],
    )
    monkeypatch.setattr(ds, "_read_last_fired_seq", lambda d_id: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_write_last_fired_seq", lambda d_id, seq, ts: None)
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)

    section = ds.fired_decisions_section(_ctx(consecutive_tool_only_rounds=5, agentic_round_seq=5))
    assert section is not None
    assert "decision:dec_xxx" in section
    assert "loop_nudge_5_rounds" in section
    assert "round 5" in section
