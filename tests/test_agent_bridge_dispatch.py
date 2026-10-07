"""E: fastlaast dispatch til EN klient - aldrig failover, aldrig en anden klient, aldrig containeren."""
from __future__ import annotations

import asyncio

import pytest

USER = "u1"


class FakeWS:
    """send_json logger; ``reply`` besvarer kaldet (som WS-handleren ville) eller tier stille."""

    def __init__(self, conn_ref, reply="ok", fail=None):
        self.sent, self.reply, self.fail, self.conn_ref = [], reply, fail, conn_ref

    async def send_json(self, data):
        if self.fail:
            raise RuntimeError(self.fail)
        self.sent.append(data)
        if self.reply == "ok":
            await self.conn_ref[0].deliver_result(correlation_id=data["correlation_id"], status="ok",
                                                  result={"echo": data["tool"]})
        elif self.reply == "handler_error":
            await self.conn_ref[0].deliver_result(correlation_id=data["correlation_id"], status="error",
                                                  error="ENOENT")
        elif self.reply == "disconnect":
            self.conn_ref[0].cancel_all_pending(reason="bridge_disconnected")


@pytest.fixture
def reg(monkeypatch):
    from core.services import agent_bridge_dispatch as D
    from core.services.jarvisx_bridge import BridgeConnection, bridge_registry
    bridge_registry.clear()
    monkeypatch.setattr("core.services.bridge_presence.all_presence", lambda: {})

    class H:
        D_ = D
        reg_ = bridge_registry

        def add(self, client_id, caps=("operator_read_file", "operator_bash"), **ws_kw):
            ref = [None]
            c = BridgeConnection(user_id=USER, client="desk", client_id=client_id, capabilities=list(caps),
                                 ws=FakeWS(ref, **ws_kw))
            ref[0] = c
            bridge_registry.register(c)
            return c

        def call(self, client_id, tool="operator_read_file", timeout_s=2.0, **kw):
            return asyncio.run(D.dispatch_pinned(user_id=USER, client_id=client_id, tool=tool,
                                                 args={"path": "/x"}, timeout_s=timeout_s, **kw))
    yield H()
    bridge_registry.clear()


def test_the_call_goes_to_the_named_client_and_carries_the_invocation_envelope(reg):
    other = reg.add("telefon-1")
    desk = reg.add("desk-1")
    out = reg.call("desk-1", extra={"invocation_id": "inv-1", "run_id": "r1", "idempotency_class": "read"})
    assert out == {"status": "ok", "result": {"echo": "operator_read_file"}, "error": None, "sent": True}
    assert other.ws.sent == []
    assert desk.ws.sent[0]["agent_invocation"] == {"invocation_id": "inv-1", "run_id": "r1",
                                                    "idempotency_class": "read"}


def test_a_client_that_is_not_connected_never_falls_back_to_another_client(reg):
    other = reg.add("telefon-1")
    out = reg.call("desk-1", allow_cross_process=False)
    assert (out["status"], out["error"]) == ("error", "client_not_connected")
    assert other.ws.sent == []


def test_a_failed_send_reports_not_sent_and_does_not_try_a_second_client(reg):
    broken = reg.add("desk-1", fail="boom")
    spare = reg.add("desk-2")                                   # bruger har en ANDEN klient med samme vaerktoej
    out = reg.call("desk-1")
    assert (out["error"], out["sent"]) == ("bridge_send_failed", False)
    assert spare.ws.sent == [] and broken.ws.sent == []


def test_a_timeout_after_sending_is_reported_as_sent(reg):
    desk = reg.add("desk-1", reply="silent")
    out = reg.call("desk-1", timeout_s=0.2)
    assert (out["error"], out["sent"]) == ("bridge_timeout", True) and len(desk.ws.sent) == 1


def test_a_disconnect_mid_call_is_sent_and_disconnected(reg):
    reg.add("desk-1", reply="disconnect")
    out = reg.call("desk-1")
    assert (out["error"], out["sent"], out["reason"]) == ("bridge_disconnected", True, "bridge_disconnected")


def test_a_handler_error_is_a_normal_known_outcome(reg):
    reg.add("desk-1", reply="handler_error")
    out = reg.call("desk-1")
    assert (out["status"], out["error"], out["sent"]) == ("error", "ENOENT", True)


def test_client_info_reads_local_registrations_and_falls_back_to_presence(reg, monkeypatch):
    reg.add("desk-1", caps=("operator_bash",))
    info = reg.D_.client_info(USER, "desk-1")
    assert (info["process"], info["capabilities"]) == ("local", ["operator_bash"])
    assert reg.D_.client_info(USER, "findes-ikke") is None
    monkeypatch.setattr("core.services.bridge_presence.all_presence", lambda: {
        USER: {"process": "api", "clients": {"mobil-1": {"client": "mobil", "capabilities": ["phone_location"]}}}})
    assert reg.D_.client_info(USER, "mobil-1")["process"] == "api"


def test_forward_goes_only_to_the_process_that_holds_that_client(reg, monkeypatch):
    posted = {}

    class Resp:
        status_code = 200
        def json(self): return {"status": "ok", "result": "fra-api", "error": None, "sent": True}

    class Http:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, headers=None):
            posted.update(url=url, body=json, headers=headers)
            return Resp()

    monkeypatch.setattr("core.services.bridge_presence.all_presence", lambda: {
        USER: {"process": "api", "clients": {"desk-1": {"capabilities": ["operator_bash"]}}}})
    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "runtime")
    monkeypatch.setattr("core.services.jarvisx_bridge.internal_dispatch_token", lambda: "hemmeligt-token")
    monkeypatch.setattr("httpx.AsyncClient", Http)
    out = reg.call("desk-1", extra={"invocation_id": "inv-9"})
    assert out["result"] == "fra-api"
    assert posted["body"]["client_id"] == "desk-1" and posted["body"]["extra"] == {"invocation_id": "inv-9"}
    assert posted["headers"] and posted["url"].endswith("/api/internal/jarvisx-bridge/dispatch")


def test_forward_failure_after_the_post_is_unknown_not_unsent(reg, monkeypatch):
    class Boom:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): raise OSError("reset by peer")

    monkeypatch.setattr("core.services.bridge_presence.all_presence", lambda: {
        USER: {"process": "api", "clients": {"desk-1": {"capabilities": []}}}})
    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "runtime")
    monkeypatch.setattr("core.services.jarvisx_bridge.internal_dispatch_token", lambda: "t")
    monkeypatch.setattr("httpx.AsyncClient", Boom)
    out = reg.call("desk-1")
    assert (out["error"], out["sent"]) == ("bridge_forward_failed", None)


def test_presence_pointing_at_our_own_process_without_a_local_bridge_is_not_connected(reg, monkeypatch):
    monkeypatch.setattr("core.services.bridge_presence.all_presence", lambda: {
        USER: {"process": "api", "clients": {"desk-1": {"capabilities": []}}}})
    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "api")
    assert reg.call("desk-1")["error"] == "client_not_connected"
