"""Tests for prosa-tool-call-parseren (tool-leak-fix)."""
from __future__ import annotations

import json

from core.services.prose_tool_calls import extract_prose_tool_calls

_TOOLS = {"bash_session_run", "read_file", "search", "send_mail"}


def test_parses_paren_wrapped_call_with_json_args():
    text = 'Lad mig køre det.\n([bash_session_run]: { "session_id": "bsh-1", "command": "ls -la" })\nFærdig.'
    cleaned, calls = extract_prose_tool_calls(text, _TOOLS)
    assert len(calls) == 1
    fn = calls[0]["function"]
    assert calls[0]["type"] == "function" and fn["name"] == "bash_session_run"
    assert json.loads(fn["arguments"]) == {"session_id": "bsh-1", "command": "ls -la"}
    assert "bash_session_run" not in cleaned and "Lad mig køre det." in cleaned and "Færdig." in cleaned


def test_handles_nested_braces_and_strings():
    text = '[read_file]: {"path": "/x", "opts": {"deep": true}, "q": "a}b"}'
    cleaned, calls = extract_prose_tool_calls(text, _TOOLS)
    assert len(calls) == 1
    assert json.loads(calls[0]["function"]["arguments"]) == {
        "path": "/x", "opts": {"deep": True}, "q": "a}b"}
    assert cleaned == ""


def test_unknown_tool_name_is_ignored():
    text = '[not_a_real_tool]: {"x": 1}'
    cleaned, calls = extract_prose_tool_calls(text, _TOOLS)
    assert calls == [] and cleaned == text


def test_markdown_reference_link_not_converted():
    text = "Se [docs]: https://example.com for mere."
    cleaned, calls = extract_prose_tool_calls(text, _TOOLS)
    assert calls == [] and cleaned == text          # ingen JSON → ikke et kald


def test_narrated_result_not_converted():
    text = "([search]: [no matches])\n([search]: [no matches])"
    cleaned, calls = extract_prose_tool_calls(text, _TOOLS)
    assert calls == [] and cleaned == text          # [..] er ikke et JSON-objekt


def test_multiple_calls_all_extracted():
    text = '[search]: {"q": "a"} og [read_file]: {"path": "/b"}'
    cleaned, calls = extract_prose_tool_calls(text, _TOOLS)
    assert [c["function"]["name"] for c in calls] == ["search", "read_file"]


def test_empty_and_no_tools_safe():
    assert extract_prose_tool_calls("", _TOOLS) == ("", [])
    assert extract_prose_tool_calls("[read_file]: {}", set()) == ("[read_file]: {}", [])


def test_malformed_json_left_as_prose():
    text = '[read_file]: {"path": "/x"'      # mangler afsluttende }
    cleaned, calls = extract_prose_tool_calls(text, _TOOLS)
    assert calls == [] and cleaned == text
