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


@pytest.mark.asyncio
async def test_terminal_guarantee_on_blocked_legacy_stream(monkeypatch):
    """D2-leak hang-fix (16. jun): hvis legacy-strømmen BLOKERER uden at sende
    'done' (presentation-invariant-leak afslutter runnet server-side men kilde-
    generatoren hænger), OG runnet ikke længere er aktivt → translatoren skal
    ALLIGEVEL udsende message_stop i stedet for at hænge desk i 'working'."""
    import core.services.visible_runs_sse_v2 as sse2
    monkeypatch.setattr(sse2, "_IDLE_TICK_S", 0.05, raising=False)
    monkeypatch.setattr(sse2, "_run_still_active", lambda rid: False, raising=False)

    async def legacy() -> AsyncIterator[str]:
        # tool-event → message_start sendes (message_started=True)
        yield _legacy_sse("capability", {
            "type": "tool_result", "run_id": "visible-x", "tool": "operator_bash",
            "status": "ok", "tool_use_id": "t1", "result_text": "ok",
        })
        await asyncio.Event().wait()  # blokér for evigt — INTET 'done'

    output = await asyncio.wait_for(_collect(translate_to_v2(
        legacy(), run_id="visible-x", model="m", provider="p", lane="l",
    )), timeout=5)
    kinds = [e[0] for e in _parse_v2_events(output)]
    assert "message_stop" in kinds, f"ingen message_stop — desk ville hænge: {kinds}"


@pytest.mark.asyncio
async def test_live_run_survives_idle_gap_longer_than_tick(monkeypatch):
    """IDLE-CANCEL-ROD (Bjørn 4. jul): FØR cancellerede wait_for() den awaitede
    __anext__ ved hver _IDLE_TICK_S tavshed → CancelledError ind i den LEVENDE
    run-generator midt i et langt tool-/model-kald → svaret gik tabt. Nu: en
    tavs-men-LEVENDE generator (run stadig aktivt) må IKKE afbrydes — dens
    post-gap-content + done SKAL nå igennem. Reproducerer det ægte cutoff:
    et tavst vindue > tick MENS runnet kører."""
    import core.services.visible_runs_sse_v2 as sse2
    # Kort tick, men run RAPPORTERES stadig aktivt → må aldrig afbrydes af idle.
    monkeypatch.setattr(sse2, "_IDLE_TICK_S", 0.05, raising=False)
    monkeypatch.setattr(sse2, "_run_still_active", lambda rid: True, raising=False)

    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "visible-live", "delta": "Før "})
        # Tavst vindue LÆNGERE end flere ticks (simulerer langt tool-/model-kald)
        await asyncio.sleep(0.25)  # 5× _IDLE_TICK_S
        yield _legacy_sse("delta", {"type": "delta", "run_id": "visible-live", "delta": "efter"})
        yield _legacy_sse("done", {
            "type": "done", "run_id": "visible-live", "status": "completed",
            "input_tokens": 10, "output_tokens": 2,
        })

    output = await asyncio.wait_for(_collect(translate_to_v2(
        legacy(), run_id="visible-live", model="m", provider="p", lane="l",
        session_id="sess", ping_interval_s=999.0,
    )), timeout=5)
    events = _parse_v2_events(output)
    # Den POST-gap tekst SKAL være der (blev tabt før fixet), og et rent stop.
    text = "".join(
        str(p.get("delta", {}).get("text", ""))
        for k, p in events if k == "content_block_delta"
    )
    kinds = [e[0] for e in events]
    assert "efter" in text, f"post-gap content tabt (cancelleret levende run): {text!r}"
    assert "message_stop" in kinds, f"intet rent stop: {kinds}"


@pytest.mark.asyncio
async def test_underlying_generator_aclosed_after_done():
    """KRITISK regression (2026-06-21): translate_to_v2 BRYDER ud ved 'done' uden
    at udtømme legacy_iter. Uden eksplicit aclose kører _stream_visible_run's finally
    (der spawner _post_process: fact_gate/diagnosis/claim/memory) ALDRIG for follow-runs.
    Verificér at translator'en lukker den underliggende generator → dens finally kører."""
    finally_ran = {"v": False}

    async def _legacy():
        try:
            yield _legacy_sse("delta", {"type": "delta", "run_id": "v1", "delta": "hej"})
            yield _legacy_sse("done", {"type": "done", "run_id": "v1", "status": "completed"})
            # frames EFTER done (som _post_process-regionens scan_correction) — translate
            # breaker ved done og når aldrig hertil; generatoren efterlades suspenderet.
            yield _legacy_sse("scan_correction", {"type": "scan_correction", "run_id": "v1"})
        finally:
            finally_ran["v"] = True

    await _collect(translate_to_v2(_legacy(), run_id="v1"))
    assert finally_ran["v"] is True, "legacy-generatorens finally kørte ikke — _post_process ville dø"


@pytest.mark.asyncio
async def test_stream_error_observed_and_still_terminates(monkeypatch):
    """Stream-cluster (2026-06-23): en ÆGTE fejl i translations-loopet skal
    OBSERVERES i Centralen (synlig) OG stadig afslutte rent med message_stop
    (finally-garanti). Før forsvandt fejlen tavst."""
    import core.services.stream_sentinel as ss
    events: list[dict] = []
    monkeypatch.setattr(ss, "note_event",
                        lambda rid, kind, sid="", **d: events.append({"rid": rid, "kind": kind, **d}))

    async def legacy() -> AsyncIterator[str]:
        yield _legacy_sse("delta", {"type": "delta", "run_id": "ve", "delta": "hej"})
        raise RuntimeError("provider blæste op midt i stream")

    output = await _collect(translate_to_v2(
        legacy(), run_id="ve", model="m", provider="p", lane="l",
    ))
    kinds = [e[0] for e in _parse_v2_events(output)]
    assert "message_stop" in kinds, f"fejl-stream afsluttede ikke rent: {kinds}"
    errs = [e for e in events if e["kind"] == "error"]
    assert errs and "RuntimeError" in errs[0].get("error", ""), f"fejl ikke observeret: {events}"
