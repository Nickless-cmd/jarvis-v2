"""Final syntese skal beholde providerens stream hele vejen til SSE-kalderen."""

import asyncio
from threading import Event

import pytest

from core.services import visible_followup as vf
from core.services.visible_post_tool_synthesis import (
    SynthesisDelta,
    SynthesisDone,
    stream_final_synthesis,
)


def test_final_synthesis_exposes_provider_deltas(monkeypatch):
    def fake_stream(**_kwargs):
        yield vf.FollowupDelta(delta="Her er ")
        yield vf.FollowupDelta(delta="svaret.")
        yield vf.FollowupDone(text="Her er svaret.", reasoning_content="")

    monkeypatch.setattr(vf, "stream_visible_followup", fake_stream)
    deltas = []
    result = vf.synthesize_final_answer(
        provider="test", model="test", base_messages=[], exchanges=[],
        on_delta=deltas.append,
    )
    assert deltas == ["Her er ", "svaret."]
    assert result == "Her er svaret."


@pytest.mark.asyncio
async def test_first_delta_arrives_before_synthesis_finishes(monkeypatch):
    release = Event()

    def synthesize_final_answer(*, on_delta, **_kwargs):
        on_delta("Første ")
        release.wait(timeout=2)
        on_delta("anden.")
        return "Første anden."

    monkeypatch.setattr(vf, "synthesize_final_answer", synthesize_final_answer)
    stream = stream_final_synthesis(
        provider="test", model="test", base_messages=[], exchanges=[],
    )
    try:
        first = await asyncio.wait_for(anext(stream), timeout=1)
        assert first == SynthesisDelta("Første")
        release.set()
        rest = [event async for event in stream]
    finally:
        release.set()
        await stream.aclose()
    assert rest == [SynthesisDelta(" anden."), SynthesisDone("Første anden.")]


@pytest.mark.asyncio
async def test_hollow_candidate_stays_hidden_until_it_is_substantial(monkeypatch):
    release = Event()

    def synthesize_final_answer(*, on_delta, **_kwargs):
        on_delta("Kort ")
        release.wait(timeout=2)
        on_delta("men nu er hele svaret langt nok.")
        return "Kort men nu er hele svaret langt nok."

    monkeypatch.setattr(vf, "synthesize_final_answer", synthesize_final_answer)
    stream = stream_final_synthesis(
        provider="test", model="test", base_messages=[], exchanges=[], min_chars=24,
    )
    task = asyncio.create_task(anext(stream))
    try:
        await asyncio.sleep(0.03)
        assert not task.done()
        release.set()
        first = await asyncio.wait_for(task, timeout=1)
        rest = [event async for event in stream]
    finally:
        release.set()
        await stream.aclose()
    assert first == SynthesisDelta("Kort men nu er hele svaret langt nok.")
    assert rest == [SynthesisDone("Kort men nu er hele svaret langt nok.")]


@pytest.mark.asyncio
async def test_nonstreaming_provider_result_is_emitted_once(monkeypatch):
    monkeypatch.setattr(vf, "synthesize_final_answer", lambda **_kwargs: "Helt svar.")
    events = [event async for event in stream_final_synthesis(
        provider="test", model="test", base_messages=[], exchanges=[],
    )]
    assert events == [SynthesisDelta("Helt svar."), SynthesisDone("Helt svar.")]


@pytest.mark.asyncio
async def test_short_guard_candidate_is_not_shown(monkeypatch):
    def synthesize_final_answer(*, on_delta, **_kwargs):
        on_delta("ja")
        return "ja"

    monkeypatch.setattr(vf, "synthesize_final_answer", synthesize_final_answer)
    events = [event async for event in stream_final_synthesis(
        provider="test", model="test", base_messages=[], exchanges=[], min_chars=24,
    )]
    assert events == [SynthesisDone("")]


@pytest.mark.asyncio
async def test_split_internal_marker_is_removed_before_streaming(monkeypatch):
    def synthesize_final_answer(*, on_delta, **_kwargs):
        for part in ("Svaret er ", "[decision-", "signal: skjult]", "42."):
            on_delta(part)
        return "Svaret er [decision-signal: skjult]42."

    monkeypatch.setattr(vf, "synthesize_final_answer", synthesize_final_answer)
    events = [event async for event in stream_final_synthesis(
        provider="test", model="test", base_messages=[], exchanges=[],
    )]
    text = "".join(event.text for event in events if isinstance(event, SynthesisDelta))
    assert "decision-signal" not in text
    assert events[-1] == SynthesisDone(text)
