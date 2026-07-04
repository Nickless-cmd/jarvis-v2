"""Tests for backend_unresolved_3_calls decision-trigger.

Dækker den logik der (med cooldown 0) drev decision-signal-runaway'en 4. jul —
og bekræfter exit-betingelsen (resolution-tekst bryder nag'en)."""
from __future__ import annotations

from core.services.decision_triggers.backend_unresolved import (
    backend_unresolved_3_calls,
    _is_jarvis_backend_call,
)
from core.services.decision_signals import TriggerContext


def _ctx(recent_tool_calls, recent_assistant_text=""):
    return TriggerContext(
        user_message="",
        session_id="s",
        run_id="r",
        consecutive_tool_only_rounds=0,
        recent_tool_calls=recent_tool_calls,
        recent_assistant_text=recent_assistant_text,
        agentic_round_seq=1,
        timestamp="2026-07-04T00:00:00+00:00",
    )


def _call(name, path=None):
    fn = {"name": name}
    if path is not None:
        fn["arguments"] = {"path": path}
    return {"function": fn}


def test_fewer_than_3_backend_calls_does_not_fire():
    calls = [_call("read_file", "core/x.py"), _call("read_file", "core/y.py")]
    assert backend_unresolved_3_calls(_ctx(calls)) is False


def test_three_backend_calls_no_resolution_fires():
    calls = [_call("read_file", "core/a.py")] * 3
    assert backend_unresolved_3_calls(_ctx(calls)) is True


def test_three_backend_calls_with_resolution_text_does_not_fire():
    calls = [_call("read_file", "core/a.py")] * 3
    text = (
        "Jeg fandt root cause: cooldown var 0, så nag'en forgiftede sin egen "
        "exit-buffer. Jeg har fikset det og deployet ændringen til containeren nu."
    )
    assert len(text) >= 80  # resolution kræver ≥80 tegn OG et keyword
    assert backend_unresolved_3_calls(_ctx(calls, text)) is False


def test_non_backend_call_breaks_streak():
    calls = [
        _call("read_file", "core/a.py"),
        _call("send_message"),  # not a backend pattern → resets streak
        _call("read_file", "core/b.py"),
        _call("read_file", "core/c.py"),
    ]
    # kun 2 sammenhængende backend-kald til sidst → fyrer ikke
    assert backend_unresolved_3_calls(_ctx(calls)) is False


def test_git_calls_count_as_backend_by_name():
    calls = [_call("git_status"), _call("git_diff"), _call("git_log")]
    assert backend_unresolved_3_calls(_ctx(calls)) is True


def test_path_outside_jarvis_tree_is_not_backend():
    assert _is_jarvis_backend_call(_call("read_file", "/tmp/random.txt")) is False


def test_backend_call_without_path_counts():
    # grep uden dir → behandles som backend
    assert _is_jarvis_backend_call(_call("grep")) is True


def test_short_resolution_text_does_not_count_as_resolution():
    """Resolution kræver ≥80 tegn OG et keyword — kort 'fixed' bryder ikke nag'en."""
    calls = [_call("read_file", "core/a.py")] * 3
    assert backend_unresolved_3_calls(_ctx(calls, "fixed")) is True
