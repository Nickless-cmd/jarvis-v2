"""SSE v2 event-dataclasses — Anthropic-style streaming protocol.

Bygget 2026-06-10 efter Bjørns design-spec (docs/superpowers/specs/
2026-06-10-chat-stream-v2-design.md). Disse dataclasses repræsenterer
hvert event-type på wire-formatet og har `to_sse_line()` metoder der
producerer den faktiske SSE-streng der sendes til klienten.

Wire-format:
  event: <event_name>
  data: <JSON>
  <blank line>

Hver event har:
- En "type" felt der matcher Anthropic's protokol
- En `event` property der mappes til SSE event-navnet
- to_sse_line() der returnerer den komplette SSE-blok

Klient-side bibliotek (apps/jarvis-desk/src/lib/streamClient.ts) konsumerer
disse events. Test-fixtures i tests/test_sse_v2_events.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


def _sse_format(event_name: str, data: dict) -> str:
    """SSE-format: event + data + blank line."""
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@dataclass
class MessageStart:
    """Markerer starten på et nyt assistant-svar.

    Sendes én gang ved begyndelsen af en visible-run, med metadata om
    selve runet (id, model, provider, lane, session_id).
    """
    run_id: str
    model: str
    provider: str
    lane: str
    session_id: str | None = None

    def to_sse_line(self) -> str:
        """Returnér message_start SSE-blokken med run-metadata og nul-usage."""
        return _sse_format("message_start", {
            "type": "message_start",
            "message": {
                "id": self.run_id,
                "model": self.model,
                "provider": self.provider,
                "lane": self.lane,
                "session_id": self.session_id,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        })


@dataclass
class ContentBlockStart:
    """Markerer start på en content-block (text, thinking, eller tool_use).

    Hver block får et stigende `index`. Tekst og thinking har tom start-
    payload; tool_use har et delvist input-objekt der kan suppleres senere
    via input_json_delta.
    """
    index: int
    block_type: str  # "text" | "thinking" | "tool_use"
    tool_id: str | None = None  # kun for tool_use
    tool_name: str | None = None  # kun for tool_use

    def to_sse_line(self) -> str:
        """Returnér content_block_start SSE-blokken; content_block afhænger af block_type."""
        content_block: dict[str, Any]
        if self.block_type == "tool_use":
            content_block = {
                "type": "tool_use",
                "id": self.tool_id or "",
                "name": self.tool_name or "",
                "input": {},
            }
        elif self.block_type == "thinking":
            content_block = {"type": "thinking", "thinking": ""}
        else:
            content_block = {"type": "text", "text": ""}
        return _sse_format("content_block_start", {
            "type": "content_block_start",
            "index": self.index,
            "content_block": content_block,
        })


@dataclass
class ContentBlockDelta:
    """Inkrementelt indhold til en aktiv content-block.

    For text blocks: text_delta med næste tekst-chunk.
    For thinking blocks: thinking_delta med næste reasoning-chunk.
    For tool_use blocks: input_json_delta med partial_json (klienten
      akkumulerer dem til at vise tool-args mens de bliver genereret).
    """
    index: int
    delta_type: str  # "text_delta" | "thinking_delta" | "input_json_delta"
    content: str

    def to_sse_line(self) -> str:
        """Returnér content_block_delta SSE-blokken; delta-feltet afhænger af delta_type."""
        delta: dict[str, Any] = {"type": self.delta_type}
        if self.delta_type == "text_delta":
            delta["text"] = self.content
        elif self.delta_type == "thinking_delta":
            delta["thinking"] = self.content
        elif self.delta_type == "input_json_delta":
            delta["partial_json"] = self.content
        return _sse_format("content_block_delta", {
            "type": "content_block_delta",
            "index": self.index,
            "delta": delta,
        })


@dataclass
class ContentBlockStop:
    """Markerer at en bestemt content-block er færdig.

    Klienten kan nu "låse" indholdet af den block (fx render markdown
    færdigt, parse tool-args som JSON, etc.).
    """
    index: int

    def to_sse_line(self) -> str:
        """Returnér content_block_stop SSE-blokken for den angivne block-index."""
        return _sse_format("content_block_stop", {
            "type": "content_block_stop",
            "index": self.index,
        })


@dataclass
class MessageDelta:
    """Opdaterer message-level metadata mod slutningen.

    Indeholder stop_reason (end_turn / tool_use / max_tokens / stop_sequence /
    cancelled / error) og final usage (input/output tokens + cache info).
    """
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0

    def to_sse_line(self) -> str:
        """Returnér message_delta SSE-blokken med stop_reason og final usage-tal."""
        return _sse_format("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": self.stop_reason},
            "usage": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cache_hit_tokens": self.cache_hit_tokens,
                "cache_miss_tokens": self.cache_miss_tokens,
            },
        })


@dataclass
class MessageStop:
    """Sidste event — assistant-svaret er færdigt."""

    def to_sse_line(self) -> str:
        """Returnér den afsluttende message_stop SSE-blok."""
        return _sse_format("message_stop", {"type": "message_stop"})


@dataclass
class Ping:
    """Keepalive event hver ~5s under streaming.

    Holder TCP-forbindelsen i live gennem proxies/NAT og tillader
    klienten at vise "stadig i live" indikator.
    """

    def to_sse_line(self) -> str:
        """Returnér ping keepalive SSE-blokken."""
        return _sse_format("ping", {"type": "ping"})


@dataclass
class SystemEvent:
    """Jarvis-specifik extension der ikke passer i Anthropic-skema.

    Klienter der ikke kender en bestemt `kind` kan ignorere event'en
    trygt. Aktuelle kinds:
      - working_step: tool-call statusopdatering
      - capability: tool_approved / tool_denied / tool_result
      - approval_request: chat-card popup til at godkende tool-kald
      - steer_received: bruger sendte midway-besked
      - turn_changelog: per-turn ændringsrapport
    """
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_sse_line(self) -> str:
        """Returnér system_event SSE-blokken med kind og payload."""
        return _sse_format("system_event", {
            "type": "system_event",
            "kind": self.kind,
            "payload": self.payload,
        })
