"""OllamaFreeAPI adapter for PUBLIC-SAFE cheap-lane calls.

This wrapper exists to translate the project's Ollama/OpenAI-like call shape
into OllamaFreeAPI's simpler ``chat(prompt, model)`` API. It must not be used
for prompts containing user chat, identity material, chronicle entries, or
other private runtime state.
"""

from __future__ import annotations

import time
from typing import Any

from ollamafreeapi import OllamaFreeAPI

_CLIENT: OllamaFreeAPI | None = None


def _client() -> OllamaFreeAPI:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = OllamaFreeAPI()
    return _CLIENT


def collapse_messages_to_prompt(messages: list[dict[str, object]] | None) -> str:
    parts: list[str] = []
    for item in messages or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "user").strip() or "user"
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        parts.append(f"{role.upper()}: {content}")
    return "\n\n".join(parts).strip()


def list_ollamafreeapi_models() -> list[str]:
    return sorted(set(_client().list_models()))


def call_ollamafreeapi(
    *,
    model: str,
    messages: list[dict[str, object]] | None = None,
    prompt: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Call OllamaFreeAPI and return an Ollama-compatible response shape."""
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        prompt_text = collapse_messages_to_prompt(messages)
    if not prompt_text:
        raise ValueError("call_ollamafreeapi requires prompt or messages")

    started = time.time_ns()
    text = _client().chat(prompt_text, model=model, timeout=timeout)
    content = str(text or "").strip()
    return {
        "message": {"content": content},
        "done": True,
        "total_duration": max(0, time.time_ns() - started),
    }
