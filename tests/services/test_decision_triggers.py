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


from core.services.decision_triggers import backend_unresolved


def _tc(name: str, **args):
    """Build a tool_call dict matching what visible_runs records."""
    return {
        "function": {
            "name": name,
            "arguments": args or {},
        },
    }


def test_backend_unresolved_fires_after_3_streak_in_repo():
    calls = [
        _tc("read_file", path="/media/projects/jarvis-v2/core/services/foo.py"),
        _tc("grep", path="/media/projects/jarvis-v2/core"),
        _tc("read_file", path="/media/projects/jarvis-v2/apps/api/x.py"),
    ]
    ctx = _ctx(recent_tool_calls=calls, recent_assistant_text="")
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is True


def test_backend_unresolved_does_not_fire_after_2():
    calls = [
        _tc("read_file", path="/media/projects/jarvis-v2/core/services/foo.py"),
        _tc("grep", path="/media/projects/jarvis-v2/core"),
    ]
    ctx = _ctx(recent_tool_calls=calls)
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is False


def test_backend_unresolved_resets_on_non_backend_tool():
    calls = [
        _tc("read_file", path="/media/projects/jarvis-v2/core/x.py"),
        _tc("grep", path="/media/projects/jarvis-v2/core"),
        _tc("web_search", query="something"),  # resets
        _tc("read_file", path="/media/projects/jarvis-v2/core/y.py"),
    ]
    ctx = _ctx(recent_tool_calls=calls)
    # After reset, only 1 backend call → no fire
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is False


def test_backend_unresolved_ignores_non_jarvis_paths():
    calls = [
        _tc("read_file", path="/etc/hosts"),
        _tc("read_file", path="/var/log/syslog"),
        _tc("read_file", path="/tmp/foo.txt"),
    ]
    ctx = _ctx(recent_tool_calls=calls)
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is False


def test_backend_unresolved_accepts_git_calls_without_path():
    calls = [
        _tc("git_status"),
        _tc("git_log"),
        _tc("git_diff"),
    ]
    ctx = _ctx(recent_tool_calls=calls)
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is True


def test_backend_unresolved_suppressed_by_resolution_text():
    calls = [
        _tc("read_file", path="/media/projects/jarvis-v2/core/x.py"),
        _tc("grep", path="/media/projects/jarvis-v2/core"),
        _tc("read_file", path="/media/projects/jarvis-v2/core/y.py"),
    ]
    long_resolution = (
        "Jeg fandt root cause i config-loaderen — den prøvede at læse fra en "
        "path der ikke eksisterede. Fixed nu, deployer ikke før jeg har testet."
    )
    ctx = _ctx(recent_tool_calls=calls, recent_assistant_text=long_resolution)
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is False


def test_backend_unresolved_short_text_does_not_count_as_resolution():
    calls = [
        _tc("read_file", path="/media/projects/jarvis-v2/core/x.py"),
        _tc("grep", path="/media/projects/jarvis-v2/core"),
        _tc("read_file", path="/media/projects/jarvis-v2/core/y.py"),
    ]
    short = "fundet."  # under 80 chars
    ctx = _ctx(recent_tool_calls=calls, recent_assistant_text=short)
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is True


def test_backend_unresolved_module_registers():
    assert "backend_unresolved_3_calls" in ds._TRIGGER_REGISTRY
    spec = ds._TRIGGER_REGISTRY["backend_unresolved_3_calls"]
    assert spec.cooldown_seconds == 0
