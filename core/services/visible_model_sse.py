"""SSE / Chat-Completions stream parsing + small cost/token utilities.

Split out of ``core.services.visible_model`` (boy-scout, 2026-07-07). These are
provider-agnostic, pure-ish helpers (the only side effect is a self-safe
Central observe on malformed SSE). Re-exported verbatim from
``core.services.visible_model``; ``core.services.visible_followup`` imports the
chat-completion delta/reasoning/tool-call helpers directly.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Iterator

from core.services.stream_failure_kind import (
    MalformedStreamPayload,
    safe_decode_line,
    try_parse_json_line,
)
from core.services.visible_model_observe import _observe_malformed_stream_payload

OPENAI_TEXT_PRICING_PER_1M_TOKENS: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-5": (Decimal("1.25"), Decimal("10.00")),
    "gpt-5-mini": (Decimal("0.25"), Decimal("2.00")),
    "gpt-5-nano": (Decimal("0.05"), Decimal("0.40")),
    # DeepSeek V4 — May 2026 promotional pricing (75% off Pro until end of May)
    "deepseek-v4-flash": (Decimal("0.14"), Decimal("0.28")),
    "deepseek-v4-pro": (Decimal("0.435"), Decimal("0.87")),
}


def _estimate_tokens(text: str) -> int:
    words = [part for part in text.strip().split() if part]
    return max(1, len(words))


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _calculate_openai_cost_usd(
    *, model: str, input_tokens: int, output_tokens: int
) -> float:
    pricing = OPENAI_TEXT_PRICING_PER_1M_TOKENS.get(model.strip().lower())
    if pricing is None:
        return 0.0

    input_rate, output_rate = pricing
    total = Decimal(int(input_tokens)) * input_rate / Decimal(1_000_000) + Decimal(
        int(output_tokens)
    ) * output_rate / Decimal(1_000_000)
    return float(total.quantize(Decimal("0.00000001")))


def _chunk_text(text: str, size: int = 48) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def _extract_chat_completion_delta(event: dict) -> str:
    choices = event.get("choices") or []
    parts: list[str] = []
    for item in choices:
        if not isinstance(item, dict):
            continue
        delta = item.get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            if content:
                parts.append(content)
            continue
        if isinstance(content, list):
            for chunk in content:
                if not isinstance(chunk, dict):
                    continue
                text = str(chunk.get("text") or "").strip()
                if text:
                    parts.append(text)
    return "".join(parts)


def _extract_chat_completion_reasoning(event: dict) -> str:
    """Pull reasoning_content delta from a streaming Chat Completions chunk.

    Deepseek thinking-mode emits reasoning as ``delta.reasoning_content``
    alongside (or instead of) ``delta.content``. Must be captured so we
    can replay it on the next assistant turn.
    """
    choices = event.get("choices") or []
    parts: list[str] = []
    for item in choices:
        if not isinstance(item, dict):
            continue
        delta = item.get("delta") or {}
        reasoning = delta.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning:
            parts.append(reasoning)
    return "".join(parts)


def _finalize_openai_tool_calls(tool_calls: list[dict]) -> list[dict]:
    """Normalize OpenAI-style tool_calls so arguments is a dict, not a JSON string.

    OpenAI Chat Completions returns ``function.arguments`` as a JSON-encoded
    string. Downstream executors (execute_tool) expect a dict, matching how
    Ollama returns tool_calls. Parse once here so consumers see one shape.
    """
    finalized: list[dict] = []
    for tc in tool_calls:
        if not isinstance(tc, dict):
            continue
        fn = dict(tc.get("function") or {})
        args = fn.get("arguments")
        if isinstance(args, str):
            stripped = args.strip()
            if stripped:
                try:
                    fn["arguments"] = json.loads(stripped)
                except (json.JSONDecodeError, ValueError):
                    fn["arguments"] = {}
            else:
                fn["arguments"] = {}
        elif args is None:
            fn["arguments"] = {}
        finalized.append({**tc, "function": fn})
    return finalized


def _merge_openai_tool_call_deltas(
    accumulator: dict[int, dict], event: dict
) -> None:
    """Merge OpenAI SSE tool_calls delta chunks into a per-index accumulator.

    Tool calls stream as partial objects keyed by `index`: the first chunk
    carries id/name, later chunks append to `function.arguments`. This merges
    them in-place so the caller can yield complete tool calls once the stream
    terminates.
    """
    for item in event.get("choices") or []:
        if not isinstance(item, dict):
            continue
        delta = item.get("delta") or {}
        for tc in delta.get("tool_calls") or []:
            if not isinstance(tc, dict):
                continue
            idx = int(tc.get("index") or 0)
            slot = accumulator.setdefault(
                idx,
                {
                    "id": None,
                    "type": "function",
                    "function": {"name": None, "arguments": ""},
                },
            )
            if tc.get("id"):
                slot["id"] = tc["id"]
            if tc.get("type"):
                slot["type"] = tc["type"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                slot["function"]["name"] = fn["name"]
            if "arguments" in fn and fn["arguments"] is not None:
                slot["function"]["arguments"] += str(fn["arguments"])


def _chat_completion_stream_is_terminal(event: dict) -> bool:
    choices = event.get("choices") or []
    if not choices:
        return False
    return all(
        isinstance(item, dict) and str(item.get("finish_reason") or "").strip()
        for item in choices
    )


def _iter_sse_events(
    response, *, provider: str = "openai", model: str = "",
) -> Iterator[dict]:
    """Hærdet SSE-decoder (spec §1A + §11.1 A11).

    Buffer'er ``data:``-linjer til en komplet event-blok før parse (multi-line
    data) og — afgørende — dræber ALDRIG streamen mid-turn:
      - decode med ``errors="replace"`` så et split UTF-8-codepoint (æøå/emoji)
        bliver til U+FFFD i stedet for en ``UnicodeDecodeError`` ud af generatoren.
      - ``json.loads`` i try/except: en enkelt malformet ``data:``-blok midt i en
        ellers sund stream → SKIP + let observe; men slutter streamen uden
        ``[DONE]`` EFTER et skip → typed retryable :class:`MalformedStreamPayload`."""
    event_name = "message"
    data_lines: list[str] = []
    saw_done = False
    saw_malformed = False

    for raw_line in response:
        # A11 pkt. 1: decode UDEN at rejse.
        line = safe_decode_line(raw_line).strip()
        if not line:
            if not data_lines:
                event_name = "message"
                continue
            data = "\n".join(data_lines)
            data_lines = []
            if data == "[DONE]":
                saw_done = True
                break
            # A11 pkt. 2: én malformet event-blok må IKKE dræbe streamen.
            payload, _ok = try_parse_json_line(data)
            if not _ok:
                saw_malformed = True
                _observe_malformed_stream_payload(
                    provider, model, "sse_decoder",
                    ended_malformed=False, detail=data[:120])
                event_name = "message"
                continue
            if payload is None:
                event_name = "message"
                continue
            if "type" not in payload:
                payload["type"] = event_name
            yield payload
            event_name = "message"
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())

    # A11: streamen sluttede uden [DONE] EFTER et malformet-skip → trunkeret
    # final-event. Bær op som typed retryable (caller's except → fejl-stien).
    if not saw_done and saw_malformed:
        _observe_malformed_stream_payload(
            provider, model, "sse_decoder", ended_malformed=True,
            detail="stream ended without [DONE] after malformed block")
        raise MalformedStreamPayload(
            "OpenAI SSE stream ended malformed (truncated final event)")
