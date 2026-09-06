from __future__ import annotations

from types import SimpleNamespace


def test_hollow_post_tool_answer_requires_tool_calls():
    from core.services.post_tool_answer_guard import is_hollow_post_tool_answer

    assert not is_hollow_post_tool_answer("done", [])
    assert is_hollow_post_tool_answer("done", [SimpleNamespace(tool_calls=[{"name": "read_file"}])])


def test_should_replace_with_synthesis_requires_substance():
    from core.services.post_tool_answer_guard import should_replace_with_synthesis

    assert should_replace_with_synthesis("ok", "Jeg fandt resultatet og kan forklare det.")
    assert not should_replace_with_synthesis("ok", "ja")
