"""Translator: legacy SSE-events → Anthropic-style v2-protokol.

Phase 1 (denne fil): basic text-flow translation
- delta → content_block_delta(text_delta) til den aktive text-block
- working_step / capability / approval_request / steer_received /
  turn_changelog → system_event-wrappes
- done → content_block_stop + message_delta + message_stop
- heartbeat → skip (v2 har sin egen ping)

Phase 2 (senere): tool_use blocks, thinking_delta, partial input_json_delta.

Forbruger output fra core.services.visible_runs.start_visible_run() der
yielder SSE-formaterede strenge i legacy-format. Parser dem, oversætter
til v2 dataclasses, serializer som v2 SSE-strenge.

Spec: docs/superpowers/specs/2026-06-10-chat-stream-v2-design.md
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import AsyncIterator

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

# SSE-format regex til at parse legacy events:
#   event: <name>
#   data: <json>
#   (blank line)
_SSE_BLOCK_RE = re.compile(
    r"event:\s*(?P<event>[^\n]+)\n"
    r"data:\s*(?P<data>[^\n]+)\n\n",
)


# System-event kinds vi proxy'er fra legacy event-types.
# Hvis et legacy event-name ikke er kendt, wrappes det også som
# system_event med kind = legacy-navnet (safe fallback).
_KNOWN_SYSTEM_EVENT_KINDS = {
    "working_step",
    "capability",
    "approval_request",
    "steer_received",
    "turn_changelog",
}


def _parse_legacy_sse(chunk: str) -> tuple[str, dict] | None:
    """Parse en legacy SSE event-blok til (event_name, payload_dict).

    Returnerer None hvis chunk ikke er en fuldstændig event-blok eller
    payload ikke er valid JSON.
    """
    m = _SSE_BLOCK_RE.search(chunk)
    if not m:
        return None
    event_name = m.group("event").strip()
    data_str = m.group("data")
    try:
        payload = json.loads(data_str)
    except (ValueError, TypeError):
        return None
    return event_name, payload


async def translate_to_v2(
    legacy_iter: AsyncIterator[str],
    *,
    run_id: str = "",
    model: str = "",
    provider: str = "",
    lane: str = "",
    session_id: str | None = None,
    ping_interval_s: float = 5.0,
) -> AsyncIterator[str]:
    """Konverter legacy SSE-stream til Anthropic-style v2 protokol.

    Yielder Anthropic-formaterede SSE-strenge.

    Translation-state:
      - message_started: True efter message_start er sendt
      - text_block_open: True hvis en text content-block er aktiv
      - text_block_index: index på den aktive text-block (starter 0)
      - last_run_id/model/etc: synkroniseres fra legacy events (overrider
        de tomme defaults vi blev kaldt med)

    Bemærk: ping-loop kører i en separat task der yielder ind i en kø,
    så vi har konkurrence-fri yielding fra både den primære oversættelse
    og ping-eventene.
    """
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    _state = {
        "message_started": False,
        "text_block_open": False,
        "text_block_index": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_hit_tokens": 0,
        "cache_miss_tokens": 0,
        "stop_reason": "end_turn",
        "run_id": run_id,
        "model": model,
        "provider": provider,
        "lane": lane,
        "session_id": session_id,
    }

    async def _emit_message_start_if_needed() -> None:
        if _state["message_started"]:
            return
        _state["message_started"] = True
        await queue.put(MessageStart(
            run_id=str(_state["run_id"] or ""),
            model=str(_state["model"] or ""),
            provider=str(_state["provider"] or ""),
            lane=str(_state["lane"] or ""),
            session_id=(
                str(_state["session_id"]) if _state["session_id"] is not None else None
            ),
        ).to_sse_line())
        # Åbn første text-block straks så delta'er kan lande
        await queue.put(ContentBlockStart(
            index=int(_state["text_block_index"]),
            block_type="text",
        ).to_sse_line())
        _state["text_block_open"] = True

    async def _close_text_block_if_open() -> None:
        if _state["text_block_open"]:
            await queue.put(ContentBlockStop(
                index=int(_state["text_block_index"]),
            ).to_sse_line())
            _state["text_block_open"] = False

    async def _ping_loop() -> None:
        try:
            while True:
                await asyncio.sleep(ping_interval_s)
                await queue.put(Ping().to_sse_line())
        except asyncio.CancelledError:
            pass

    async def _translation_loop() -> None:
        try:
            async for raw in legacy_iter:
                parsed = _parse_legacy_sse(raw)
                if parsed is None:
                    continue
                event_name, payload = parsed

                # Pluk metadata ud af tidlige events så message_start har
                # meningsfulde værdier hvis de ikke blev givet til kaldet.
                if event_name == "delta" and payload.get("run_id"):
                    _state["run_id"] = _state["run_id"] or str(payload.get("run_id") or "")

                if event_name == "delta":
                    await _emit_message_start_if_needed()
                    text = str(payload.get("delta") or "")
                    if text:
                        await queue.put(ContentBlockDelta(
                            index=int(_state["text_block_index"]),
                            delta_type="text_delta",
                            content=text,
                        ).to_sse_line())

                elif event_name == "done":
                    await _emit_message_start_if_needed()
                    await _close_text_block_if_open()
                    _state["input_tokens"] = int(payload.get("input_tokens") or 0)
                    _state["output_tokens"] = int(payload.get("output_tokens") or 0)
                    _state["stop_reason"] = str(payload.get("status") or "end_turn")
                    await queue.put(MessageDelta(
                        stop_reason=str(_state["stop_reason"]),
                        input_tokens=int(_state["input_tokens"]),
                        output_tokens=int(_state["output_tokens"]),
                        cache_hit_tokens=int(_state["cache_hit_tokens"]),
                        cache_miss_tokens=int(_state["cache_miss_tokens"]),
                    ).to_sse_line())
                    await queue.put(MessageStop().to_sse_line())
                    break

                elif event_name == "heartbeat":
                    # v2 har sin egen ping — skip legacy heartbeats
                    continue

                else:
                    # working_step, capability, approval_request,
                    # steer_received, turn_changelog, eller ukendt →
                    # wrap som system_event med kind = event_name
                    await _emit_message_start_if_needed()
                    kind = event_name
                    if kind not in _KNOWN_SYSTEM_EVENT_KINDS:
                        # Ukendt legacy event-type: stadig pass through
                        # som system_event så klienten kan ignorere det
                        # eller logge til debug.
                        pass
                    await queue.put(SystemEvent(
                        kind=kind, payload=payload,
                    ).to_sse_line())
        except asyncio.CancelledError:
            pass
        finally:
            # Signaler at translation er færdig — ping-loop stoppes via
            # outer cancel, og hovedløkken nedenfor breaker når den ser
            # sentinel.
            await queue.put(None)

    ping_task = asyncio.create_task(_ping_loop())
    translation_task = asyncio.create_task(_translation_loop())

    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        ping_task.cancel()
        translation_task.cancel()
        # Drain eventuelle restevents i kø så ressourcer frigives ordentligt.
        try:
            await asyncio.gather(ping_task, translation_task, return_exceptions=True)
        except Exception:
            pass
