"""Translate between Anthropic Messages API format and Ollama /api/chat format.

Anthropic format uses content blocks (text, tool_use, tool_result), system
as a top-level field, and `tools` with `input_schema`. Ollama format uses
flat `messages` (with optional `tool_calls` on assistant messages and
separate `tool` role messages for results) and `tools` with `parameters`.
"""
from __future__ import annotations

from typing import Any


def translate_request_to_ollama(
    anthropic_body: dict[str, Any],
    *,
    identity_prefix: str,
    backend_model: str,
) -> dict[str, Any]:
    """Build an Ollama /api/chat payload from an Anthropic Messages request."""
    out: dict[str, Any] = {
        "model": backend_model,
        "messages": [],
        "stream": bool(anthropic_body.get("stream", False)),
    }

    # System message: identity prefix + Anthropic's system parameter
    user_system = str(anthropic_body.get("system") or "").strip()
    sys_parts = [s for s in (identity_prefix.strip(), user_system) if s]
    if sys_parts:
        out["messages"].append({
            "role": "system",
            "content": "\n\n".join(sys_parts),
        })

    # Translate each message
    for msg in anthropic_body.get("messages", []):
        out["messages"].extend(_translate_message(msg))

    # Translate tools (rename input_schema → parameters; wrap in function shape)
    if anthropic_body.get("tools"):
        out["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": str(t.get("name") or ""),
                    "description": str(t.get("description") or ""),
                    "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
                },
            }
            for t in anthropic_body["tools"]
            if t.get("name")
        ]

    # max_tokens → options.num_predict
    if anthropic_body.get("max_tokens"):
        out.setdefault("options", {})["num_predict"] = int(anthropic_body["max_tokens"])

    return out


def _translate_message(msg: dict[str, Any]) -> list[dict[str, Any]]:
    """Translate a single Anthropic message into 1-N Ollama messages.

    A user message with multiple tool_result blocks expands to multiple
    Ollama tool-role messages. An assistant message with text + tool_use
    becomes a single assistant message with text content + tool_calls list.
    """
    role = str(msg.get("role") or "user")
    content = msg.get("content")

    # String content → simple message
    if isinstance(content, str):
        return [{"role": role, "content": content}]

    if not isinstance(content, list):
        return [{"role": role, "content": str(content or "")}]

    if role == "user":
        # User can have text + tool_result blocks
        text_parts = []
        tool_results = []
        for block in content:
            btype = str(block.get("type") or "")
            if btype == "text":
                text_parts.append(str(block.get("text") or ""))
            elif btype == "tool_result":
                tool_results.append(block)
            # Other types (image) ignored in Mode 2

        out_msgs = []
        if text_parts:
            out_msgs.append({"role": "user", "content": "\n".join(text_parts)})
        for tr in tool_results:
            out_msgs.append({
                "role": "tool",
                "tool_call_id": str(tr.get("tool_use_id") or ""),
                "content": _stringify_tool_result_content(tr.get("content")),
            })
        return out_msgs

    if role == "assistant":
        text_parts = []
        tool_calls = []
        for block in content:
            btype = str(block.get("type") or "")
            if btype == "text":
                text_parts.append(str(block.get("text") or ""))
            elif btype == "tool_use":
                tool_calls.append({
                    "id": str(block.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(block.get("name") or ""),
                        "arguments": block.get("input") or {},
                    },
                })

        out: dict[str, Any] = {
            "role": "assistant",
            "content": "\n".join(text_parts),
        }
        if tool_calls:
            out["tool_calls"] = tool_calls
        return [out]

    # Unknown role → passthrough as plain text
    return [{"role": role, "content": str(content)}]


def _stringify_tool_result_content(content: Any) -> str:
    """Anthropic tool_result content can be string or list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content or "")


# ---------------------------------------------------------------------------
# Response side: Ollama → Anthropic
# ---------------------------------------------------------------------------

import json as _json_mod
from typing import Iterator, Iterable


def drive_emitter_from_ollama_chunks(emitter, chunks: Iterable[dict]) -> Iterator[str]:
    """Drive an AnthropicSSEEmitter from a stream of Ollama chat chunks.

    Each chunk has shape:
      {"message": {"role": "assistant", "content": "...", "tool_calls": [...]}, "done": bool, ...}

    Yields SSE-formatted strings. Calls begin_message once, then translates
    each delta into text_delta or tool_use_start + input_json_delta. Ends
    with end_message(stop_reason).
    """
    yield from emitter.begin_message()
    has_tool_call = False
    seen_tool_call_ids: set[str] = set()

    try:
        for chunk in chunks:
            msg = chunk.get("message") or {}
            content = str(msg.get("content") or "")
            if content:
                yield from emitter.text_delta(content)

            tool_calls = msg.get("tool_calls") or []
            for tc in tool_calls:
                tc_id = str(tc.get("id") or "")
                if not tc_id or tc_id in seen_tool_call_ids:
                    continue
                seen_tool_call_ids.add(tc_id)
                fn = tc.get("function") or {}
                name = str(fn.get("name") or "")
                args = fn.get("arguments")
                yield from emitter.tool_use_start(tool_call_id=tc_id, name=name)
                if isinstance(args, dict):
                    yield from emitter.tool_use_input_delta(_json_mod.dumps(args, ensure_ascii=False))
                elif isinstance(args, str):
                    yield from emitter.tool_use_input_delta(args)
                has_tool_call = True

            if chunk.get("done"):
                break
    except Exception as exc:
        yield from emitter.error(str(exc))
        return

    stop_reason = "tool_use" if has_tool_call else "end_turn"
    yield from emitter.end_message(stop_reason=stop_reason)


def build_non_streaming_response(
    *,
    message_id: str,
    model: str,
    text: str,
    tool_calls: list[dict],
) -> dict:
    """Build the final Anthropic Messages response (non-streaming)."""
    content: list[dict] = []
    if text:
        content.append({"type": "text", "text": text})
    for tc in tool_calls:
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = _json_mod.loads(args)
            except Exception:
                args = {}
        content.append({
            "type": "tool_use",
            "id": str(tc.get("id") or ""),
            "name": str(fn.get("name") or ""),
            "input": args or {},
        })
    stop_reason = "tool_use" if tool_calls else "end_turn"
    return {
        "id": message_id,
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


