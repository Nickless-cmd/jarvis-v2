"""Anthropic Messages API SSE state machine.

Emits a sequence of `event: <name>\\ndata: <json>\\n\\n` chunks matching
the Anthropic streaming protocol. Tracks current open content block so
text → tool_use transitions emit a `content_block_stop` first.
"""
from __future__ import annotations

import json
from typing import Iterator, Optional


class AnthropicSSEEmitter:
    """Stateful emitter for one streamed message.

    Usage:
        emitter = AnthropicSSEEmitter(message_id="msg_x", model="jarvis")
        yield from emitter.begin_message()
        yield from emitter.text_delta("Hej")
        yield from emitter.tool_use_start("toolu_1", "Bash")
        yield from emitter.tool_use_input_delta('{"cmd":"ls"}')
        yield from emitter.end_message(stop_reason="tool_use")
    """

    def __init__(self, *, message_id: str, model: str):
        self.message_id = message_id
        self.model = model
        self._next_index = 0
        self._open_block_type: Optional[str] = None  # "text" | "tool_use" | None
        self._open_block_index: Optional[int] = None
        self._message_started = False
        self._message_ended = False

    @staticmethod
    def _format(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def begin_message(self) -> Iterator[str]:
        if self._message_started:
            return
        self._message_started = True
        yield self._format("message_start", {
            "type": "message_start",
            "message": {
                "id": self.message_id,
                "type": "message",
                "role": "assistant",
                "model": self.model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        })

    def _close_open_block(self) -> Iterator[str]:
        if self._open_block_type is None:
            return
        idx = self._open_block_index
        self._open_block_type = None
        self._open_block_index = None
        yield self._format("content_block_stop", {
            "type": "content_block_stop",
            "index": idx,
        })

    def _open_text_block(self) -> Iterator[str]:
        idx = self._next_index
        self._next_index += 1
        self._open_block_type = "text"
        self._open_block_index = idx
        yield self._format("content_block_start", {
            "type": "content_block_start",
            "index": idx,
            "content_block": {"type": "text", "text": ""},
        })

    def text_delta(self, text: str) -> Iterator[str]:
        if not text:
            return
        if self._open_block_type != "text":
            yield from self._close_open_block()
            yield from self._open_text_block()
        yield self._format("content_block_delta", {
            "type": "content_block_delta",
            "index": self._open_block_index,
            "delta": {"type": "text_delta", "text": text},
        })

    def tool_use_start(self, tool_call_id: str, name: str) -> Iterator[str]:
        yield from self._close_open_block()
        idx = self._next_index
        self._next_index += 1
        self._open_block_type = "tool_use"
        self._open_block_index = idx
        yield self._format("content_block_start", {
            "type": "content_block_start",
            "index": idx,
            "content_block": {
                "type": "tool_use",
                "id": tool_call_id,
                "name": name,
                "input": {},
            },
        })

    def tool_use_input_delta(self, partial_json: str) -> Iterator[str]:
        if self._open_block_type != "tool_use":
            return
        yield self._format("content_block_delta", {
            "type": "content_block_delta",
            "index": self._open_block_index,
            "delta": {"type": "input_json_delta", "partial_json": partial_json},
        })

    def end_message(self, *, stop_reason: str, output_tokens: int = 0) -> Iterator[str]:
        if self._message_ended:
            return
        yield from self._close_open_block()
        yield self._format("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        })
        yield self._format("message_stop", {"type": "message_stop"})
        self._message_ended = True

    def ping(self) -> Iterator[str]:
        yield self._format("ping", {"type": "ping"})

    def error(self, message: str) -> Iterator[str]:
        """Emit a graceful error: close any open block, emit error stop."""
        yield from self._close_open_block()
        yield self._format("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": "error", "stop_sequence": None},
            "usage": {"output_tokens": 0},
        })
        yield self._format("message_stop", {"type": "message_stop"})
        self._message_ended = True


