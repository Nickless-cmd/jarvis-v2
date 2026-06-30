"""Tests for cross-process bridge dispatch (runtime-proces → api-proces).

bridge_registry er PER-PROCES. Desk-broen registreres KUN i api-procesen
(port 8080); autonome/wakeup-runs kører i runtime-procesen (port 8011) med
sit eget tomme registry → bridge_not_connected. Fixet: når en proces ikke
har en lokal bro, HTTP-forwarder den dispatchen til api-procesen over
localhost, beskyttet af localhost-only + shared-secret-header.

Alle tests er hermetiske: broen + httpx mockes, ingen rigtige sockets.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest


def _run(coro):
    return asyncio.run(coro)


# ── (a) lokal bro til stede → direkte dispatch, INGEN HTTP ─────────────────


def test_local_bridge_dispatches_directly_no_http():
    from core.services import jarvisx_bridge as jb
    from core.services.jarvisx_bridge import bridge_registry, BridgeConnection

    bridge_registry.clear()
    conn = BridgeConnection(user_id="owner", client="test")
    bridge_registry.register(conn)

    async def fake_send_invoke(*, correlation_id, tool, args, timeout_ms):
        # Lever resultatet med det samme, som broen ville.
        await conn.deliver_result(
            correlation_id=correlation_id, status="ok", result={"ok": True},
        )

    forwarded = {"called": False}

    async def fake_forward(**_kw):
        forwarded["called"] = True
        return {"status": "error", "result": None, "error": "should_not_be_called"}

    with patch.object(conn, "send_invoke", side_effect=fake_send_invoke), \
            patch.object(bridge_registry, "_forward_cross_process", side_effect=fake_forward):
        res = _run(bridge_registry.dispatch(
            user_id="owner", tool="operator_read_file", args={"path": "/x"}, timeout_s=5.0,
        ))

    assert res["status"] == "ok"
    assert res["result"] == {"ok": True}
    assert forwarded["called"] is False
    bridge_registry.clear()


# ── (b) ingen lokal bro + allow_cross_process=True → HTTP POST forward ──────


def test_no_local_bridge_forwards_http():
    from core.services import jarvisx_bridge as jb
    from core.services.jarvisx_bridge import bridge_registry

    bridge_registry.clear()

    captured = {}

    class _FakeResp:
        status_code = 200

        def json(self):
            return {"status": "ok", "result": {"via": "api"}, "error": None}

    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, *, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _FakeResp()

    import httpx

    with patch.object(jb, "internal_dispatch_token", return_value="secret-token"), \
            patch.object(httpx, "AsyncClient", _FakeClient):
        res = _run(bridge_registry.dispatch(
            user_id="owner", tool="operator_read_file", args={"path": "/x"}, timeout_s=5.0,
        ))

    assert res["status"] == "ok"
    assert res["result"] == {"via": "api"}
    assert captured["url"].endswith("/api/internal/jarvisx-bridge/dispatch")
    assert "127.0.0.1" in captured["url"]
    assert captured["json"]["user_id"] == "owner"
    assert captured["json"]["tool"] == "operator_read_file"
    assert captured["headers"][jb._INTERNAL_TOKEN_HEADER] == "secret-token"
    bridge_registry.clear()


# ── (c) HTTP forward fejler → bridge_not_connected (uændret adfærd) ─────────


def test_http_forward_failure_degrades_to_bridge_not_connected():
    from core.services import jarvisx_bridge as jb
    from core.services.jarvisx_bridge import bridge_registry

    bridge_registry.clear()

    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            raise ConnectionRefusedError("api down")

    import httpx

    with patch.object(jb, "internal_dispatch_token", return_value="secret-token"), \
            patch.object(httpx, "AsyncClient", _FakeClient):
        res = _run(bridge_registry.dispatch(
            user_id="owner", tool="operator_read_file", args={}, timeout_s=2.0,
        ))

    assert res["status"] == "error"
    assert res["error"] == "bridge_not_connected"
    bridge_registry.clear()


def test_http_forward_non_200_degrades_to_bridge_not_connected():
    from core.services import jarvisx_bridge as jb
    from core.services.jarvisx_bridge import bridge_registry

    bridge_registry.clear()

    class _FakeResp:
        status_code = 500

        def json(self):
            return {}

    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            return _FakeResp()

    import httpx

    with patch.object(jb, "internal_dispatch_token", return_value="secret-token"), \
            patch.object(httpx, "AsyncClient", _FakeClient):
        res = _run(bridge_registry.dispatch(
            user_id="owner", tool="operator_read_file", args={}, timeout_s=2.0,
        ))

    assert res["status"] == "error"
    assert res["error"] == "bridge_not_connected"
    bridge_registry.clear()


# ── (d) allow_cross_process=False + ingen bro → bridge_not_connected, INGEN HTTP


def test_no_cross_process_no_bridge_immediate_not_connected():
    from core.services.jarvisx_bridge import bridge_registry

    bridge_registry.clear()

    forwarded = {"called": False}

    async def fake_forward(**_kw):
        forwarded["called"] = True
        return {"status": "ok", "result": None, "error": None}

    with patch.object(bridge_registry, "_forward_cross_process", side_effect=fake_forward):
        res = _run(bridge_registry.dispatch(
            user_id="owner", tool="operator_read_file", args={},
            timeout_s=2.0, allow_cross_process=False,
        ))

    assert res["status"] == "error"
    assert res["error"] == "bridge_not_connected"
    assert forwarded["called"] is False
    bridge_registry.clear()


# ── (e) internt endpoint afviser ikke-localhost / forkert token ─────────────


def _make_request(*, host, headers, body):
    """Minimal fake Starlette Request med .client, .headers, .json()."""
    class _Client:
        def __init__(self, h):
            self.host = h

    class _Req:
        def __init__(self):
            self.client = _Client(host) if host is not None else None
            self.headers = headers

        async def json(self):
            return body

    return _Req()


def test_internal_endpoint_rejects_non_localhost():
    from apps.api.jarvis_api.routes import jarvisx_bridge as route

    req = _make_request(
        host="10.0.0.99",
        headers={route._INTERNAL_TOKEN_HEADER: "whatever"},
        body={"user_id": "owner", "tool": "operator_read_file", "args": {}},
    )
    resp = _run(route.internal_dispatch(req))
    assert resp.status_code == 403


def test_internal_endpoint_rejects_bad_token():
    from apps.api.jarvis_api.routes import jarvisx_bridge as route

    with patch.object(route, "internal_dispatch_token", return_value="the-real-token"):
        req = _make_request(
            host="127.0.0.1",
            headers={route._INTERNAL_TOKEN_HEADER: "wrong-token"},
            body={"user_id": "owner", "tool": "operator_read_file", "args": {}},
        )
        resp = _run(route.internal_dispatch(req))
    assert resp.status_code == 401


def test_internal_endpoint_rejects_missing_token():
    from apps.api.jarvis_api.routes import jarvisx_bridge as route

    with patch.object(route, "internal_dispatch_token", return_value="the-real-token"):
        req = _make_request(
            host="127.0.0.1",
            headers={},  # ingen token-header
            body={"user_id": "owner", "tool": "operator_read_file", "args": {}},
        )
        resp = _run(route.internal_dispatch(req))
    assert resp.status_code == 401


def test_internal_endpoint_accepts_localhost_with_token_and_dispatches_no_loop():
    """Lokalhost + korrekt token → dispatch kaldes med allow_cross_process=False."""
    from apps.api.jarvis_api.routes import jarvisx_bridge as route
    from core.services.jarvisx_bridge import bridge_registry

    captured = {}

    async def fake_dispatch(*, user_id, tool, args, timeout_s, allow_cross_process):
        captured["allow_cross_process"] = allow_cross_process
        captured["user_id"] = user_id
        return {"status": "ok", "result": {"done": True}, "error": None}

    with patch.object(route, "internal_dispatch_token", return_value="tok"), \
            patch.object(bridge_registry, "dispatch", side_effect=fake_dispatch):
        req = _make_request(
            host="127.0.0.1",
            headers={route._INTERNAL_TOKEN_HEADER: "tok"},
            body={"user_id": "owner", "tool": "operator_read_file", "args": {"path": "/x"}, "timeout_s": 7},
        )
        resp = _run(route.internal_dispatch(req))

    assert resp.status_code == 200
    # Løkke-spærre: api må ALDRIG forwarde videre.
    assert captured["allow_cross_process"] is False
    assert captured["user_id"] == "owner"
