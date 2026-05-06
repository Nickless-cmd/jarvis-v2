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
