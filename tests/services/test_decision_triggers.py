import pytest

from core.services import decision_signals as ds
from core.services.decision_triggers import loop_nudge


def _ctx(**overrides):
    base = dict(
        user_message="", session_id=None, run_id=None,
        consecutive_tool_only_rounds=0,
        recent_tool_calls=[], recent_assistant_text="",
        agentic_round_seq=0, timestamp="2026-05-07T12:00:00+00:00",
    )
    base.update(overrides)
    return ds.TriggerContext(**base)


def test_loop_nudge_fires_at_exactly_5():
    assert loop_nudge.loop_nudge_5_rounds(_ctx(consecutive_tool_only_rounds=5)) is True


def test_loop_nudge_does_not_fire_at_4():
    assert loop_nudge.loop_nudge_5_rounds(_ctx(consecutive_tool_only_rounds=4)) is False


def test_loop_nudge_does_not_fire_at_6():
    assert loop_nudge.loop_nudge_5_rounds(_ctx(consecutive_tool_only_rounds=6)) is False


def test_loop_nudge_module_registers_in_registry():
    # Just importing the module should have registered the trigger
    assert "loop_nudge_5_rounds" in ds._TRIGGER_REGISTRY
    spec = ds._TRIGGER_REGISTRY["loop_nudge_5_rounds"]
    assert spec.cooldown_turns == 1
