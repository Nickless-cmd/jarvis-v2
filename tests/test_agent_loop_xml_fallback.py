"""Tests for the Fase 5 Task 19 provider XML tool-call fallback in
apps/api/jarvis_api/routes/agent_loop.py — flag-gated (jc_xml_toolcall_fallback,
default OFF). Behind the flag, a response with NO native tool_calls but an
XML-tagged <tool_call>{...}</tool_call> convention in the text is parsed and
normalised into the same tool_call structure the client already consumes."""
import json

from apps.api.jarvis_api.routes import agent_loop


class TestParseXmlToolCalls:
    def test_xml_toolcall_parsed_when_native_empty(self, monkeypatch):
        monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: name == "jc_xml_toolcall_fallback")
        text = ('Sure, let me run that.\n<tool_call>{"name": "bash", '
               '"arguments": {"command": "ls"}}</tool_call>')
        content, calls = agent_loop._apply_xml_toolcall_fallback(text, [])
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "bash"
        assert json.loads(calls[0]["function"]["arguments"]) == {"command": "ls"}
        assert "<tool_call>" not in content
        assert "Sure, let me run that." in content

    def test_multiple_xml_toolcalls(self, monkeypatch):
        monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: True)
        text = ('<tool_call>{"name": "read_file", "arguments": {"path": "a.py"}}</tool_call>'
               '<tool_call>{"name": "bash", "arguments": {"command": "ls"}}</tool_call>')
        content, calls = agent_loop._apply_xml_toolcall_fallback(text, [])
        assert len(calls) == 2
        assert calls[0]["function"]["name"] == "read_file"
        assert calls[1]["function"]["name"] == "bash"

    def test_native_toolcalls_untouched(self, monkeypatch):
        monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: True)
        native = [{"id": "1", "type": "function", "function": {"name": "bash", "arguments": "{}"}}]
        content, calls = agent_loop._apply_xml_toolcall_fallback("some text", native)
        assert calls is native
        assert content == "some text"

    def test_flag_off_no_parsing(self, monkeypatch):
        monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: False)
        text = '<tool_call>{"name": "bash", "arguments": {"command": "ls"}}</tool_call>'
        content, calls = agent_loop._apply_xml_toolcall_fallback(text, [])
        assert calls == []
        assert content == text   # untouched — left as content

    def test_malformed_xml_is_content_not_crash(self, monkeypatch):
        monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: True)
        text = "<tool_call>{not valid json at all</tool_call>"
        content, calls = agent_loop._apply_xml_toolcall_fallback(text, [])
        assert calls == []
        assert content == text   # degrades to content, no exception

    def test_no_tool_call_tags_is_noop(self, monkeypatch):
        monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: True)
        content, calls = agent_loop._apply_xml_toolcall_fallback("just plain text", [])
        assert calls == []
        assert content == "just plain text"

    def test_missing_name_key_skipped(self, monkeypatch):
        monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: True)
        text = '<tool_call>{"arguments": {"command": "ls"}}</tool_call>'
        content, calls = agent_loop._apply_xml_toolcall_fallback(text, [])
        assert calls == []
