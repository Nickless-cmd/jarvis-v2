from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from core.services import visible_runs_learning_signals as LS


def _run_ref():
    return SimpleNamespace(session_id="chat-1", run_id="visible-1", user_message="kør bash og vis output")


def test_tool_names_handles_objects_and_dicts():
    calls = [SimpleNamespace(name="bash"), {"name": "read_file"}, {"function": {"name": "web_fetch"}}, {"nope": 1}]
    assert LS.tool_names(calls) == ["bash", "read_file", "web_fetch"]


def test_records_episode_lesson_and_tom_on_error():
    seen: dict = {}
    with patch("core.services.experience_episodes.record_episode", lambda **kw: seen.setdefault("episode", kw)), \
         patch("core.services.lessons.record_tool_error", lambda **kw: seen.setdefault("lesson", kw)), \
         patch("core.services.theory_of_mind_engine.record_theory_of_mind_update", lambda **kw: seen.setdefault("tom", kw)):
        LS.record_visible_run_learning_signals(
            run_ref=_run_ref(), collected_native_tool_calls=[{"name": "bash"}],
            outcome_status="failed", outcome_error="command not found: foo",
            followup_text="det fejlede", output_tokens=12,
        )
    assert seen["episode"]["tool_sequence"] == ["bash"]
    assert seen["episode"]["outcome_signals"]["tool_errors"] == 1
    assert seen["lesson"]["tool_name"] == "bash" and "command not found" in seen["lesson"]["error_text"]
    assert seen["tom"]["outcome_status"] == "failed"


def test_no_lesson_without_error_and_failsoft():
    seen: dict = {}

    def _boom(**kw):
        raise RuntimeError("episode store down")

    with patch("core.services.experience_episodes.record_episode", _boom), \
         patch("core.services.lessons.record_tool_error", lambda **kw: seen.setdefault("lesson", kw)), \
         patch("core.services.theory_of_mind_engine.record_theory_of_mind_update", lambda **kw: seen.setdefault("tom", kw)):
        LS.record_visible_run_learning_signals(
            run_ref=_run_ref(), collected_native_tool_calls=[], outcome_status="completed",
            outcome_error="", followup_text="ok", output_tokens=1,
        )
    assert "lesson" not in seen
    assert "tom" in seen, "a failing episode store must not block theory-of-mind"
