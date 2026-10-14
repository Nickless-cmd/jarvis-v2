from __future__ import annotations

import asyncio


def test_gate_omslutter_hele_streamens_levetid(monkeypatch):
    from core.services import visible_stream_gate
    from core.services.visible_stream_gate_wrapper import gate_visible_stream

    haendelser: list[str] = []
    monkeypatch.setattr(
        visible_stream_gate, "enter_visible_stream",
        lambda: haendelser.append("enter"),
    )
    monkeypatch.setattr(
        visible_stream_gate, "exit_visible_stream",
        lambda: haendelser.append("exit"),
    )

    async def kilde():
        haendelser.append("yield")
        yield "frame"

    async def koer():
        return [frame async for frame in gate_visible_stream(kilde())]

    assert asyncio.run(koer()) == ["frame"]
    assert haendelser == ["enter", "yield", "exit"]
