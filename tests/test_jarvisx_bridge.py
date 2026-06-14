"""Tests for jarvisx_bridge — bidirectional tool dispatch over WebSocket.

The bridge lets JarvisX-app (running on operator's desktop) execute tools
locally when Jarvis-runtime invokes them. Spec:
docs/superpowers/specs/2026-05-26-jarvisx-tool-bridge.md

Tests use the registry directly (no actual WS); end-to-end test uses
FastAPI TestClient's websocket support.
"""
from __future__ import annotations

import asyncio
import json
import uuid

import pytest


# ── Registry: per-user bridge tracking ──────────────────────────────────


def test_registry_starts_empty():
    from core.services.jarvisx_bridge import bridge_registry
    bridge_registry.clear()
    assert bridge_registry.get_bridge("user-x") is None


def test_register_and_get_bridge():
    """register() makes a bridge findable by user_id."""
    from core.services.jarvisx_bridge import bridge_registry, BridgeConnection
    bridge_registry.clear()

    conn = BridgeConnection(user_id="user-x", client="test", capabilities=["read_file"])
    bridge_registry.register(conn)

    found = bridge_registry.get_bridge("user-x")
    assert found is conn
    assert "read_file" in found.capabilities


def test_register_replaces_existing():
    """Newer registration for same user_id replaces the older."""
    from core.services.jarvisx_bridge import bridge_registry, BridgeConnection
    bridge_registry.clear()

    old = BridgeConnection(user_id="user-x", client="test-old")
    new = BridgeConnection(user_id="user-x", client="test-new")
    bridge_registry.register(old)
    bridge_registry.register(new)

    assert bridge_registry.get_bridge("user-x") is new


def test_unregister_removes_bridge():
    from core.services.jarvisx_bridge import bridge_registry, BridgeConnection
    bridge_registry.clear()

    conn = BridgeConnection(user_id="user-x", client="test")
    bridge_registry.register(conn)
    bridge_registry.unregister(conn)

    assert bridge_registry.get_bridge("user-x") is None


def test_unregister_idempotent():
    """Unregistering a non-registered bridge is a no-op (no error)."""
    from core.services.jarvisx_bridge import bridge_registry, BridgeConnection
    bridge_registry.clear()
    bridge_registry.unregister(BridgeConnection(user_id="nobody", client="test"))


# ── Dispatch: tool-invoke + correlation ─────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_returns_bridge_result():
    """When bridge replies with a result, dispatch_bridge() returns it."""
    from core.services.jarvisx_bridge import bridge_registry, BridgeConnection
    bridge_registry.clear()

    sent_messages = []

    class FakeWS:
        async def send_json(self, msg):
            sent_messages.append(msg)

    ws = FakeWS()
    conn = BridgeConnection(user_id="user-x", client="test", ws=ws)
    bridge_registry.register(conn)

    # Kick off dispatch — it will await pending future.
    async def _reply_after_send():
        # Wait until the invoke message is sent
        while not sent_messages:
            await asyncio.sleep(0.01)
        msg = sent_messages[0]
        assert msg["type"] == "tool_invoke"
        assert msg["tool"] == "operator_read_file"
        # Simulate bridge's reply
        await conn.deliver_result(
            correlation_id=msg["correlation_id"],
            status="ok",
            result="file contents here",
            error=None,
        )

    asyncio.create_task(_reply_after_send())

    result = await bridge_registry.dispatch(
        user_id="user-x",
        tool="operator_read_file",
        args={"path": "/x"},
        timeout_s=2.0,
    )

    assert result["status"] == "ok"
    assert result["result"] == "file contents here"


@pytest.mark.asyncio
async def test_dispatch_times_out_when_bridge_silent():
    """If bridge never responds, dispatch_bridge returns timeout error."""
    from core.services.jarvisx_bridge import bridge_registry, BridgeConnection
    bridge_registry.clear()

    class SilentWS:
        async def send_json(self, msg):
            pass  # swallow, never reply

    conn = BridgeConnection(user_id="user-x", client="test", ws=SilentWS())
    bridge_registry.register(conn)

    result = await bridge_registry.dispatch(
        user_id="user-x", tool="operator_read_file",
        args={"path": "/x"}, timeout_s=0.2,
    )
    assert result["status"] == "error"
    assert "timeout" in result["error"].lower()


@pytest.mark.asyncio
async def test_dispatch_when_no_bridge_registered():
    """Without a registered bridge, dispatch returns error immediately."""
    from core.services.jarvisx_bridge import bridge_registry
    bridge_registry.clear()

    result = await bridge_registry.dispatch(
        user_id="unknown-user", tool="operator_read_file",
        args={"path": "/x"}, timeout_s=2.0,
    )
    assert result["status"] == "error"
    assert "bridge_not_connected" in result["error"]


# ── Tool: operator_read_file ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_operator_read_file_routes_via_bridge(monkeypatch):
    """The tool wrapper calls bridge_registry.dispatch with right args."""
    from core.tools import operator_tools

    captured = {}

    async def _fake_dispatch(*, user_id, tool, args, timeout_s):
        captured["tool"] = tool
        captured["args"] = args
        captured["user_id"] = user_id
        return {"status": "ok", "result": "stub content"}

    monkeypatch.setattr(
        "core.services.jarvisx_bridge.bridge_registry.dispatch",
        _fake_dispatch,
    )

    result = await operator_tools.operator_read_file_async(
        path="/home/bs/x.txt", user_id="user-x",
    )

    assert captured["tool"] == "operator_read_file"
    assert captured["args"] == {"path": "/home/bs/x.txt"}
    assert captured["user_id"] == "user-x"
    assert result == "stub content"


@pytest.mark.asyncio
async def test_dispatch_cross_loop_safe():
    """Regression: deliver_result must wake awaiter even when called from
    a different event loop than dispatch().

    Scenario in production: tool-handler runs in a worker thread with its
    own loop (so it can call asyncio.run_until_complete). WS handler runs
    on the main uvicorn loop. Without owning-loop tracking, set_result()
    fires on the wrong loop and the awaiter never wakes — tool times out
    even though the bridge actually replied.
    """
    import asyncio
    from core.services.jarvisx_bridge import bridge_registry, BridgeConnection
    bridge_registry.clear()

    sent = []

    class FakeWS:
        async def send_json(self, msg):
            sent.append(msg)

    conn = BridgeConnection(user_id="user-x", client="test", ws=FakeWS())
    bridge_registry.register(conn)

    # Simulate WS handler arriving on a DIFFERENT loop than the
    # dispatcher. We run dispatch in a thread with its own loop and
    # call deliver_result from THIS test's main loop.
    import threading
    holder = {}

    def _run_dispatch_in_worker():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            holder["result"] = new_loop.run_until_complete(
                bridge_registry.dispatch(
                    user_id="user-x", tool="operator_read_file",
                    args={"path": "/x"}, timeout_s=3.0,
                )
            )
        finally:
            new_loop.close()

    t = threading.Thread(target=_run_dispatch_in_worker, daemon=True)
    t.start()
    # Wait until the worker has sent the invoke
    while not sent:
        await asyncio.sleep(0.01)
    correlation_id = sent[0]["correlation_id"]

    # Call deliver_result from the main test loop (different from worker's)
    await conn.deliver_result(
        correlation_id=correlation_id,
        status="ok",
        result="cross-loop content",
        error=None,
    )

    # Worker should now complete; join with timeout
    t.join(timeout=2.0)
    assert not t.is_alive(), "dispatch thread hung — cross-loop wake-up failed"
    assert holder["result"]["status"] == "ok"
    assert holder["result"]["result"] == "cross-loop content"


@pytest.mark.asyncio
async def test_operator_read_file_propagates_bridge_error():
    """If bridge returns error, tool raises RuntimeError with message."""
    from core.tools import operator_tools
    from core.services.jarvisx_bridge import bridge_registry
    bridge_registry.clear()

    with pytest.raises(RuntimeError, match="bridge_not_connected"):
        await operator_tools.operator_read_file_async(
            path="/x.txt", user_id="no-such-user",
        )


def test_list_user_ids_reflects_registry():
    """list_user_ids() returnerer alle brugere med en aktiv bro (bro_broker)."""
    from core.services.jarvisx_bridge import BridgeConnection, bridge_registry
    bridge_registry.clear()
    assert bridge_registry.list_user_ids() == []

    bridge_registry.register(BridgeConnection(user_id="mikkel"))
    bridge_registry.register(BridgeConnection(user_id="mor"))
    assert set(bridge_registry.list_user_ids()) == {"mikkel", "mor"}
    bridge_registry.clear()


def test_send_invoke_includes_mode():
    # §17.6.1: tool_invoke skal medsende mode så broen kan mode-gate lokalt.
    import asyncio
    from core.services.jarvisx_bridge import BridgeConnection

    conn = BridgeConnection(user_id="user-x", client="test")
    captured = {}

    async def _fake_send_raw(data, *, timeout_s=10.0):
        captured.update(data)

    conn.send_raw = _fake_send_raw  # type: ignore[assignment]

    async def _run():
        await conn.send_invoke(correlation_id="c1", tool="operator_bash",
                               args={"command": "ls"}, timeout_ms=5000)

    asyncio.run(_run())
    assert captured["type"] == "tool_invoke"
    assert "mode" in captured            # feltet medsendes (tom = legacy)
    assert captured["tool"] == "operator_bash"
