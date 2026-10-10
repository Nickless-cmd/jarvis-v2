from __future__ import annotations

import asyncio

import pytest

from core.services.jarvisx_bridge import BridgeConnection, bridge_registry


@pytest.mark.asyncio
async def test_deliver_output_accepts_only_increasing_live_sequences():
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    seen = []
    conn = BridgeConnection(user_id="owner")
    conn.register_pending("c1", future, loop, lambda **delta: seen.append(delta))

    await conn.deliver_output(correlation_id="unknown", stream="stdout", seq=1, chunk="x")
    await conn.deliver_output(correlation_id="c1", stream="stdout", seq=2, chunk="B")
    await conn.deliver_output(correlation_id="c1", stream="stdout", seq=2, chunk="dup")
    await conn.deliver_output(correlation_id="c1", stream="stdout", seq=1, chunk="old")
    await asyncio.sleep(0)
    assert seen == [{"stream": "stdout", "seq": 2, "chunk": "B"}]

    await conn.deliver_result(correlation_id="c1", status="ok", result={})
    await conn.deliver_output(correlation_id="c1", stream="stdout", seq=3, chunk="late")
    await asyncio.sleep(0)
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_dispatch_requests_streaming_and_delivers_deltas_before_result():
    bridge_registry.clear()
    sent = []

    class WS:
        async def send_json(self, message):
            sent.append(message)

    conn = BridgeConnection(user_id="owner", client="desk", ws=WS())
    bridge_registry.register(conn)
    seen = []

    async def reply():
        while not sent:
            await asyncio.sleep(0)
        correlation_id = sent[0]["correlation_id"]
        await conn.deliver_output(
            correlation_id=correlation_id, stream="stdout", seq=1, chunk="nu\n"
        )
        await conn.deliver_result(
            correlation_id=correlation_id,
            status="ok",
            result={"stdout": "nu\n"},
            timing={"route": "operator_bridge", "process_ms": 4},
        )

    task = asyncio.create_task(reply())
    result = await bridge_registry.dispatch(
        user_id="owner",
        tool="operator_bash",
        args={"command": "printf nu"},
        timeout_s=2,
        on_output=lambda **delta: seen.append(delta),
    )
    await task
    assert sent[0]["stream_output"] is True
    assert seen == [{"stream": "stdout", "seq": 1, "chunk": "nu\n"}]
    assert result["timing"]["process_ms"] == 4
    bridge_registry.clear()


@pytest.mark.asyncio
async def test_final_only_dispatch_keeps_stream_flag_false():
    conn = BridgeConnection(user_id="owner")
    captured = {}

    async def send_raw(message, *, timeout_s=10.0):
        captured.update(message)

    conn.send_raw = send_raw  # type: ignore[assignment]
    await conn.send_invoke(
        correlation_id="c1", tool="operator_bash", args={}, timeout_ms=1000
    )
    assert captured["stream_output"] is False


@pytest.mark.asyncio
async def test_cross_process_ndjson_forwards_deltas_and_terminal_result(monkeypatch):
    from core.services import bridge_presence
    from core.services import jarvisx_bridge as jb
    import httpx

    bridge_registry.clear()
    captured = {}
    seen = []

    class Response:
        status_code = 200

        async def aiter_lines(self):
            yield '{"type":"output_delta","stream":"stdout","seq":1,"chunk":"hej\\n"}'
            yield '{"type":"result","status":"ok","result":{"stdout":"hej\\n"},"error":null}'

    class StreamContext:
        async def __aenter__(self):
            return Response()

        async def __aexit__(self, *_args):
            return False

    class Client:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        def stream(self, method, url, *, json, headers):
            captured.update(method=method, url=url, json=json, headers=headers)
            return StreamContext()

    monkeypatch.setattr(jb, "internal_dispatch_token", lambda: "token")
    monkeypatch.setattr(bridge_presence, "all_presence", lambda: {})
    monkeypatch.setattr(httpx, "AsyncClient", Client)
    def record_then_fail(**delta):
        seen.append(delta)
        raise RuntimeError("projection failed")

    result = await bridge_registry.dispatch(
        user_id="owner",
        tool="operator_bash",
        args={"command": "printf hej"},
        timeout_s=2,
        on_output=record_then_fail,
    )
    assert captured["json"]["stream_output"] is True
    assert seen == [{"stream": "stdout", "seq": 1, "chunk": "hej\n"}]
    assert result["status"] == "ok"
    assert result["result"]["stdout"] == "hej\n"


@pytest.mark.asyncio
async def test_internal_endpoint_streams_ndjson_without_forward_loop(monkeypatch):
    from apps.api.jarvis_api.routes import jarvisx_bridge as route

    class Client:
        host = "127.0.0.1"

    class Request:
        client = Client()
        headers = {route._INTERNAL_TOKEN_HEADER: "token"}

        async def json(self):
            return {
                "user_id": "owner",
                "tool": "operator_bash",
                "args": {"command": "printf hej"},
                "stream_output": True,
            }

    async def dispatch(*, on_output, allow_cross_process, **_kwargs):
        assert allow_cross_process is False
        on_output(stream="stdout", seq=1, chunk="hej\n")
        return {"status": "ok", "result": {"stdout": "hej\n"}, "error": None}

    monkeypatch.setattr(route, "internal_dispatch_token", lambda: "token")
    monkeypatch.setattr(route.bridge_registry, "dispatch", dispatch)
    response = await route.internal_dispatch(Request())
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    assert '"type": "output_delta"' in chunks[0]
    assert '"type": "result"' in chunks[-1]
