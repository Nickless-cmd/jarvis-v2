"""Translator integration tests — legacy SSE → v2 protokol.

Mocker en sekvens af legacy SSE-events fra start_visible_run() og
verificerer at translate_to_v2() udsender Anthropic-formaterede events
i den rigtige rækkefølge.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import AsyncIterator

import pytest

from core.services.visible_runs_sse_v2 import translate_to_v2


def _legacy_sse(event: str, data: dict) -> str:
    """Byg en legacy SSE-streng som start_visible_run yielder."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _parse_v2_events(stream_output: list[str]) -> list[tuple[str, dict]]:
    """Parse v2 SSE-strenge til liste af (event_name, payload)."""
    events: list[tuple[str, dict]] = []
    for line in stream_output:
        if not line.strip():
            continue
        m = re.match(
            r"event:\s*(\S+)\ndata:\s*([^\n]+)\n\n", line,
        )
        if not m:
            continue
        events.append((m.group(1), json.loads(m.group(2))))
    return events


async def _collect(gen: AsyncIterator[str]) -> list[str]:
    return [item async for item in gen]


@pytest.mark.asyncio
async def test_basic_text_flow():
    """Standard: delta'er + done → message_start, text-block, deltas, stop."""
    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "visible-1", "delta": "Hej "})
        yield _legacy_sse("delta", {"type": "delta", "run_id": "visible-1", "delta": "verden"})
        yield _legacy_sse("done", {
            "type": "done", "run_id": "visible-1", "status": "completed",
            "input_tokens": 100, "output_tokens": 5,
        })

    output = await _collect(translate_to_v2(
        legacy(), run_id="visible-1", model="m", provider="p", lane="l",
        session_id="sess", ping_interval_s=999.0,  # disable ping for test
    ))
    events = _parse_v2_events(output)
    event_names = [e[0] for e in events]

    # Forventet sekvens
    assert event_names[0] == "message_start"
    assert event_names[1] == "content_block_start"
    # Delta-events ind imellem
    delta_events = [e for e in events if e[0] == "content_block_delta"]
    assert len(delta_events) == 2
    assert delta_events[0][1]["delta"]["text"] == "Hej "
    assert delta_events[1][1]["delta"]["text"] == "verden"
    # Afslutning
    assert "content_block_stop" in event_names
    assert "message_delta" in event_names
    assert "message_stop" in event_names

    # message_delta indeholder usage
    msg_delta = next(e for e in events if e[0] == "message_delta")
    assert msg_delta[1]["usage"]["input_tokens"] == 100
    assert msg_delta[1]["usage"]["output_tokens"] == 5


@pytest.mark.asyncio
async def test_working_step_wrapped_as_system_event():
    """working_step → system_event(kind=working_step, payload=...)."""
    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "starter"})
        yield _legacy_sse("working_step", {
            "type": "working_step", "run_id": "v1", "action": "bash_session_run",
            "step": 1, "status": "running",
        })
        yield _legacy_sse("done", {"type": "done", "run_id": "v1", "status": "completed"})

    output = await _collect(translate_to_v2(
        legacy(), session_id="s", ping_interval_s=999.0,
    ))
    events = _parse_v2_events(output)
    sys_events = [e for e in events if e[0] == "system_event"]
    assert len(sys_events) == 1
    assert sys_events[0][1]["kind"] == "working_step"
    assert sys_events[0][1]["payload"]["action"] == "bash_session_run"


@pytest.mark.asyncio
async def test_legacy_heartbeat_dropped():
    """Legacy heartbeat events skal IKKE komme ud — v2 har sin egen ping."""
    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "a"})
        yield _legacy_sse("heartbeat", {
            "type": "heartbeat", "run_id": "v1",
            "phase": "agentic_tools", "elapsed_s": 30, "beat": 2,
        })
        yield _legacy_sse("done", {"type": "done", "run_id": "v1", "status": "completed"})

    output = await _collect(translate_to_v2(
        legacy(), session_id="s", ping_interval_s=999.0,
    ))
    events = _parse_v2_events(output)
    assert not any(e[0] == "ping" for e in events), "ping skal ikke komme i denne test (interval=999)"
    assert not any(
        e[0] == "system_event" and e[1]["kind"] == "heartbeat"
        for e in events
    ), "legacy heartbeat skal ikke wrappes som system_event"


@pytest.mark.asyncio
async def test_capability_event_passes_through():
    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "x"})
        yield _legacy_sse("capability", {
            "type": "tool_approved", "tool": "operator_bash", "auto": True,
        })
        yield _legacy_sse("done", {"type": "done", "run_id": "v1", "status": "completed"})

    output = await _collect(translate_to_v2(
        legacy(), session_id="s", ping_interval_s=999.0,
    ))
    events = _parse_v2_events(output)
    cap_events = [
        e for e in events if e[0] == "system_event" and e[1]["kind"] == "capability"
    ]
    assert len(cap_events) == 1
    assert cap_events[0][1]["payload"]["tool"] == "operator_bash"


@pytest.mark.asyncio
async def test_ping_emitted_on_interval():
    """Når ping_interval_s er lav (eg. 0.05), skal vi se ping events."""
    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "a"})
        await asyncio.sleep(0.2)  # give ping-loop tid til at fire 2-3 gange
        yield _legacy_sse("done", {"type": "done", "run_id": "v1", "status": "completed"})

    output = await _collect(translate_to_v2(
        legacy(), session_id="s", ping_interval_s=0.05,
    ))
    events = _parse_v2_events(output)
    pings = [e for e in events if e[0] == "ping"]
    assert len(pings) >= 1, f"Forventede mindst 1 ping, så {len(pings)}"
