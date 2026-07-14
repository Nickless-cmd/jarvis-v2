"""Fase 6 Task 4 — scripted fake replacements for the two openai-compat
provider seams `/v1/agent/step` calls through:
  - `_execute_openai_compatible_chat` (non-stream branch, agent_loop.py:~700)
  - `_iter_openai_compatible_chat_events` (streaming branch, `_stream_step`)

One responsibility: inject finish_reason=length, empty completions, and a
raised provider exception (the forwarded-tool/provider-500 shape) at the
seam — never a real network call.
"""
from __future__ import annotations

from typing import Any, Callable


def fake_chat(*, text: str = "", tool_calls: list | None = None, tin: int = 0,
             tout: int = 0, cost: float = 0.0, fr: str = "stop",
             reasoning: str = "") -> Callable[..., dict[str, Any]]:
    """Returns a stand-in for `_execute_openai_compatible_chat`."""
    def _chat(**kw):
        return {"text": text, "tool_calls": tool_calls or [], "input_tokens": tin,
                "output_tokens": tout, "cost_usd": cost, "finish_reason": fr,
                "reasoning_content": reasoning}
    return _chat


def raising_chat(exc: Exception) -> Callable[..., dict[str, Any]]:
    """Returns a stand-in for `_execute_openai_compatible_chat` that raises —
    models a forwarded provider/tool 500 surfacing at the model-call seam."""
    def _chat(**kw):
        raise exc
    return _chat


def fake_stream(*, text: str = "", tool_calls: list | None = None, tin: int = 0,
                tout: int = 0, cost: float = 0.0, fr: str = "stop"
                ) -> Callable[..., Any]:
    """Returns a stand-in for `_iter_openai_compatible_chat_events`: yields a
    single delta (if text) then a `done` event carrying `finish_reason`."""
    def _iter(**kw):
        if text:
            yield {"kind": "delta", "text": text}
        for tc in (tool_calls or []):
            yield {"kind": "tool_call", **tc}
        yield {"kind": "done", "full_text": text, "input_tokens": tin,
              "output_tokens": tout, "cost_usd": cost, "finish_reason": fr}
    return _iter
