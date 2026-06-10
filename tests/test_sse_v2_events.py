"""Unit tests for SSE v2 event-dataclasses.

Validerer at hver event-type serialiserer korrekt til Anthropic-style
SSE wire-format.
"""
from __future__ import annotations

import json

from apps.api.jarvis_api.sse_v2_events import (
    ContentBlockDelta,
    ContentBlockStart,
    ContentBlockStop,
    MessageDelta,
    MessageStart,
    MessageStop,
    Ping,
    SystemEvent,
)


def _parse_sse(line: str) -> tuple[str, dict]:
    """Parse en SSE-block til (event_name, payload_dict)."""
    parts = line.strip().split("\n")
    event_name = parts[0].split(": ", 1)[1]
    data_str = parts[1].split(": ", 1)[1]
    return event_name, json.loads(data_str)


class TestMessageStart:
    def test_serialization(self):
        evt = MessageStart(
            run_id="visible-abc", model="deepseek-v4-flash",
            provider="deepseek", lane="primary", session_id="chat-xyz",
        )
        name, payload = _parse_sse(evt.to_sse_line())
        assert name == "message_start"
        assert payload["type"] == "message_start"
        assert payload["message"]["id"] == "visible-abc"
        assert payload["message"]["model"] == "deepseek-v4-flash"
        assert payload["message"]["session_id"] == "chat-xyz"
        assert payload["message"]["usage"]["input_tokens"] == 0

    def test_session_id_optional(self):
        evt = MessageStart(
            run_id="visible-abc", model="m", provider="p", lane="l",
        )
        _, payload = _parse_sse(evt.to_sse_line())
        assert payload["message"]["session_id"] is None


class TestContentBlockStart:
    def test_text_block(self):
        evt = ContentBlockStart(index=0, block_type="text")
        name, payload = _parse_sse(evt.to_sse_line())
        assert name == "content_block_start"
        assert payload["index"] == 0
        assert payload["content_block"]["type"] == "text"
        assert payload["content_block"]["text"] == ""

    def test_thinking_block(self):
        evt = ContentBlockStart(index=1, block_type="thinking")
        _, payload = _parse_sse(evt.to_sse_line())
        assert payload["content_block"]["type"] == "thinking"
        assert payload["content_block"]["thinking"] == ""

    def test_tool_use_block(self):
        evt = ContentBlockStart(
            index=2, block_type="tool_use",
            tool_id="toolu_abc", tool_name="bash_session_run",
        )
        _, payload = _parse_sse(evt.to_sse_line())
        assert payload["content_block"]["type"] == "tool_use"
        assert payload["content_block"]["id"] == "toolu_abc"
        assert payload["content_block"]["name"] == "bash_session_run"
        assert payload["content_block"]["input"] == {}


class TestContentBlockDelta:
    def test_text_delta(self):
        evt = ContentBlockDelta(index=0, delta_type="text_delta", content="Hej ")
        name, payload = _parse_sse(evt.to_sse_line())
        assert name == "content_block_delta"
        assert payload["index"] == 0
        assert payload["delta"]["type"] == "text_delta"
        assert payload["delta"]["text"] == "Hej "

    def test_thinking_delta(self):
        evt = ContentBlockDelta(
            index=1, delta_type="thinking_delta", content="overvejer ...",
        )
        _, payload = _parse_sse(evt.to_sse_line())
        assert payload["delta"]["type"] == "thinking_delta"
        assert payload["delta"]["thinking"] == "overvejer ..."

    def test_input_json_delta(self):
        evt = ContentBlockDelta(
            index=2, delta_type="input_json_delta",
            content='{"command":"ls',
        )
        _, payload = _parse_sse(evt.to_sse_line())
        assert payload["delta"]["type"] == "input_json_delta"
        assert payload["delta"]["partial_json"] == '{"command":"ls'

    def test_unicode_preserved(self):
        evt = ContentBlockDelta(index=0, delta_type="text_delta", content="åøæ 😊")
        _, payload = _parse_sse(evt.to_sse_line())
        assert payload["delta"]["text"] == "åøæ 😊"


class TestContentBlockStop:
    def test_serialization(self):
        evt = ContentBlockStop(index=3)
        name, payload = _parse_sse(evt.to_sse_line())
        assert name == "content_block_stop"
        assert payload["index"] == 3


class TestMessageDelta:
    def test_with_usage(self):
        evt = MessageDelta(
            stop_reason="end_turn",
            input_tokens=1000, output_tokens=200,
            cache_hit_tokens=800, cache_miss_tokens=200,
        )
        name, payload = _parse_sse(evt.to_sse_line())
        assert name == "message_delta"
        assert payload["delta"]["stop_reason"] == "end_turn"
        assert payload["usage"]["input_tokens"] == 1000
        assert payload["usage"]["cache_hit_tokens"] == 800

    def test_defaults_zero_tokens(self):
        evt = MessageDelta(stop_reason="cancelled")
        _, payload = _parse_sse(evt.to_sse_line())
        assert payload["usage"]["input_tokens"] == 0
        assert payload["usage"]["output_tokens"] == 0


class TestMessageStop:
    def test_serialization(self):
        evt = MessageStop()
        name, payload = _parse_sse(evt.to_sse_line())
        assert name == "message_stop"
        assert payload == {"type": "message_stop"}


class TestPing:
    def test_serialization(self):
        evt = Ping()
        name, payload = _parse_sse(evt.to_sse_line())
        assert name == "ping"
        assert payload == {"type": "ping"}


class TestSystemEvent:
    def test_working_step(self):
        evt = SystemEvent(
            kind="working_step",
            payload={"action": "bash_session_run", "step": 3, "status": "running"},
        )
        name, payload = _parse_sse(evt.to_sse_line())
        assert name == "system_event"
        assert payload["kind"] == "working_step"
        assert payload["payload"]["action"] == "bash_session_run"

    def test_capability(self):
        evt = SystemEvent(
            kind="capability",
            payload={"type": "tool_approved", "tool": "operator_bash", "auto": True},
        )
        _, payload = _parse_sse(evt.to_sse_line())
        assert payload["kind"] == "capability"
        assert payload["payload"]["auto"] is True
