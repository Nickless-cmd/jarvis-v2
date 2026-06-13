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


# ---------------------------------------------------------------------------
# ToolEchoFilter — backstop mod model-ekko af rå tool-output ([read_file]: …)
# ---------------------------------------------------------------------------
class TestToolEchoFilter:
    """Streaming-filter: dropper hele linjer der starter med [kendt_tool]:,
    beholder al anden tekst token-for-token. Bygger echo-mønstret fra de
    faktisk registrerede tool-navne."""

    def _filter(self, names=None):
        from core.services.visible_runs_sse_v2 import ToolEchoFilter
        return ToolEchoFilter(tool_names=names or ["read_file", "search", "bash"])

    def _run(self, chunks, names=None):
        f = self._filter(names)
        out = "".join(f.feed(c) for c in chunks)
        out += f.flush()
        return out

    def test_plain_text_passthrough(self):
        assert self._run(["Hej Bjørn, alt er grønt."]) == "Hej Bjørn, alt er grønt."

    def test_token_by_token_low_latency(self):
        # Almindelig tekst må ikke bufres til newline — den skal flyde ud.
        f = self._filter()
        emitted = [f.feed(c) for c in ["H", "e", "j"]]
        assert "".join(emitted) + f.flush() == "Hej"
        assert emitted[0] == "H"  # første token kom straks ud (ingen hold)

    def test_drops_echo_line(self):
        chunks = ["Jeg læste filen.\n", "[read_file]: kæmpe indhold her\n", "Færdig.\n"]
        assert self._run(chunks) == "Jeg læste filen.\nFærdig.\n"

    def test_echo_line_split_across_chunks(self):
        chunks = ["[read_", "file]: ", "noget rod\n", "rest"]
        assert self._run(chunks) == "rest"

    def test_echo_at_end_without_newline(self):
        assert self._run(["[read_file]: ", "dump uden newline"]) == ""

    def test_markdown_link_not_dropped(self):
        # [docs](url) er IKKE en tool-echo — skal bevares.
        assert self._run(["Se [docs](url) her\n"]) == "Se [docs](url) her\n"

    def test_unknown_bracket_tag_not_dropped(self):
        # [note]: er ikke et kendt tool-navn → bevares.
        assert self._run(["[note]: vigtig pointe\n"]) == "[note]: vigtig pointe\n"

    def test_bracket_at_line_start_then_normal(self):
        # En linje der starter med [ men diverger fra echo-mønstret.
        assert self._run(["[vigtigt] husk dette\n"]) == "[vigtigt] husk dette\n"

    def test_multiple_echo_lines(self):
        chunks = ["[read_file]: a\n", "[search]: b\n", "Svar: 42\n"]
        assert self._run(chunks) == "Svar: 42\n"

    def test_echo_with_leading_whitespace(self):
        assert self._run(["  [bash]: rm -rf\n", "ok\n"]) == "ok\n"


# ---------------------------------------------------------------------------
# Phase 2 — capability → tool_use content blocks + echo-filter integration
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tool_result_becomes_tool_use_block():
    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "Læser fil."})
        yield _legacy_sse("capability", {"type": "tool_result", "tool": "read_file", "status": "ok"})
        yield _legacy_sse("done", {"type": "done", "run_id": "v1", "status": "completed"})

    events = _parse_v2_events(await _collect(translate_to_v2(
        legacy(), session_id="s", ping_interval_s=999.0,
    )))
    starts = [e for e in events if e[0] == "content_block_start"]
    tool_starts = [e for e in starts if e[1]["content_block"]["type"] == "tool_use"]
    assert len(tool_starts) == 1
    assert tool_starts[0][1]["content_block"]["name"] == "read_file"
    # status formidles via system_event tool_result
    tr = [e for e in events if e[0] == "system_event" and e[1]["kind"] == "tool_result"]
    assert tr and tr[0][1]["payload"]["status"] == "ok"


@pytest.mark.asyncio
async def test_capability_exec_becomes_tool_use_with_input():
    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "x"})
        yield _legacy_sse("capability", {
            "type": "capability", "run_id": "v1",
            "capability_id": "cap_42", "capability_name": "read_file",
            "target_path": "docs/x.md", "command_text": None, "status": "executed",
        })
        yield _legacy_sse("done", {"type": "done", "run_id": "v1", "status": "completed"})

    events = _parse_v2_events(await _collect(translate_to_v2(
        legacy(), session_id="s", ping_interval_s=999.0,
    )))
    tool_starts = [
        e for e in events
        if e[0] == "content_block_start" and e[1]["content_block"]["type"] == "tool_use"
    ]
    assert len(tool_starts) == 1
    assert tool_starts[0][1]["content_block"]["id"] == "cap_42"
    # input leveres via input_json_delta
    input_deltas = [
        e for e in events
        if e[0] == "content_block_delta" and e[1]["delta"].get("type") == "input_json_delta"
    ]
    assert input_deltas
    assert "docs/x.md" in input_deltas[0][1]["delta"]["partial_json"]


@pytest.mark.asyncio
async def test_text_block_reopens_after_tool():
    """Tekst før og efter et tool-kald skal lande i SEPARATE text-blocks
    med stigende index, så klienten kan rekonstruere interleaving."""
    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "før"})
        yield _legacy_sse("capability", {"type": "tool_result", "tool": "search", "status": "ok"})
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "efter"})
        yield _legacy_sse("done", {"type": "done", "run_id": "v1", "status": "completed"})

    events = _parse_v2_events(await _collect(translate_to_v2(
        legacy(), session_id="s", ping_interval_s=999.0,
    )))
    text_starts = [
        e for e in events
        if e[0] == "content_block_start" and e[1]["content_block"]["type"] == "text"
    ]
    assert len(text_starts) == 2
    assert text_starts[0][1]["index"] != text_starts[1][1]["index"]


@pytest.mark.asyncio
async def test_echo_line_filtered_from_text_stream():
    """En delta hvor modellen ekkoer [read_file]: ... skal ikke nå klienten
    som text_delta."""
    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "Resultat:\n[read_file]: kæmpe dump\nFærdig.\n"})
        yield _legacy_sse("done", {"type": "done", "run_id": "v1", "status": "completed"})

    events = _parse_v2_events(await _collect(translate_to_v2(
        legacy(), session_id="s", ping_interval_s=999.0,
    )))
    text = "".join(
        e[1]["delta"]["text"] for e in events
        if e[0] == "content_block_delta" and e[1]["delta"].get("type") == "text_delta"
    )
    assert "[read_file]:" not in text
    assert "Resultat:" in text
    assert "Færdig." in text


@pytest.mark.asyncio
async def test_reasoning_delta_becomes_thinking_block_before_text():
    """Live reasoning_delta → en thinking-block FØR svar-teksten (foldbart felt)."""
    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("reasoning_delta", {"type": "reasoning_delta", "run_id": "r", "delta": "Lad mig tænke… "})
        yield _legacy_sse("reasoning_delta", {"type": "reasoning_delta", "run_id": "r", "delta": "tjek X."})
        yield _legacy_sse("delta", {"type": "delta", "run_id": "r", "delta": "Svaret."})
        yield _legacy_sse("done", {"type": "done", "run_id": "r", "status": "completed", "input_tokens": 1, "output_tokens": 1})

    events = _parse_v2_events(await _collect(translate_to_v2(
        legacy(), run_id="r", model="m", provider="p", lane="l", session_id="s", ping_interval_s=999.0,
    )))

    # Thinking-block åbnes først, med thinking_delta, og lukkes før text-blocken.
    starts = [e for e in events if e[0] == "content_block_start"]
    assert starts[0][1]["content_block"]["type"] == "thinking"
    assert starts[1][1]["content_block"]["type"] == "text"
    think_deltas = [e for e in events if e[0] == "content_block_delta" and e[1]["delta"]["type"] == "thinking_delta"]
    assert "".join(d[1]["delta"]["thinking"] for d in think_deltas) == "Lad mig tænke… tjek X."
    text_deltas = [e for e in events if e[0] == "content_block_delta" and e[1]["delta"]["type"] == "text_delta"]
    assert "".join(d[1]["delta"]["text"] for d in text_deltas) == "Svaret."


@pytest.mark.asyncio
async def test_terminal_guarantee_stream_ends_without_done():
    """Bjørn 2026-06-13 'random hangs': hvis legacy-strømmen slutter UDEN et
    'done'-event (error/exception/unormal slut), skal translatoren ALLIGEVEL
    emitte message_stop — ellers hænger klientens status på 'working' for evigt."""
    async def legacy():
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "Halvt svar"})
        # INGEN done — strømmen slutter bare (som ved en backend-fejl).

    output = await _collect(translate_to_v2(
        legacy(), run_id="v1", model="m", provider="p", lane="l",
        session_id="sess", ping_interval_s=999.0,
    ))
    names = [e[0] for e in _parse_v2_events(output)]
    assert "message_start" in names
    assert "message_stop" in names, "message_stop SKAL emitteres selv uden 'done'"
    # message_stop er sidste meningsfulde event (turen lukkes rent)
    assert names[-1] == "message_stop"


@pytest.mark.asyncio
async def test_terminal_guarantee_legacy_error_event():
    """Et legacy 'error'-event (wrappes som system_event, som klienten ignorerer)
    må ikke efterlade turen uden afslutning — message_stop emitteres i finally."""
    async def legacy():
        yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "Starter"})
        yield _legacy_sse("error", {"type": "error", "run_id": "v1", "message": "boom"})

    output = await _collect(translate_to_v2(
        legacy(), run_id="v1", model="m", provider="p", lane="l",
        session_id="sess", ping_interval_s=999.0,
    ))
    names = [e[0] for e in _parse_v2_events(output)]
    assert "message_stop" in names, "error-afsluttet run skal stadig få message_stop"


@pytest.mark.asyncio
async def test_no_message_stop_when_nothing_started():
    """Hvis intet message_start blev sendt (tom strøm), emitteres heller ikke et
    forældreløst message_stop (ville være malformet uden message_start)."""
    async def legacy():
        if False:
            yield ""  # tom async generator

    output = await _collect(translate_to_v2(
        legacy(), run_id="v1", model="m", provider="p", lane="l",
        session_id="sess", ping_interval_s=999.0,
    ))
    names = [e[0] for e in _parse_v2_events(output)]
    assert "message_stop" not in names
