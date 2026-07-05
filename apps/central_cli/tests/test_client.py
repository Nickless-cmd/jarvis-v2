from __future__ import annotations
import httpx
import pytest
from central_cli.client import CentralClient, CentralError


def _client(handler) -> CentralClient:
    transport = httpx.MockTransport(handler)
    return CentralClient(base_url="http://x", token="T", _transport=transport)


def test_get_json_sends_bearer_and_returns_body():
    seen = {}
    def handler(req: httpx.Request) -> httpx.Response:
        seen["auth"] = req.headers.get("authorization")
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"ok": True})
    c = _client(handler)
    assert c.get_json("/central/realtime") == {"ok": True}
    assert seen["auth"] == "Bearer T"
    assert seen["url"].endswith("/central/realtime")


def test_post_json_sends_body():
    seen = {}
    def handler(req: httpx.Request) -> httpx.Response:
        seen["body"] = req.content
        return httpx.Response(200, json={"done": True})
    c = _client(handler)
    assert c.post_json("/central/command", {"line": "status"}) == {"done": True}
    assert b"status" in seen["body"]


def test_403_raises_permission_error():
    c = _client(lambda req: httpx.Response(403, json={"detail": "owner-only"}))
    with pytest.raises(CentralError) as e:
        c.get_json("/central/realtime")
    assert e.value.category == "permission"


def test_500_raises_server_error():
    c = _client(lambda req: httpx.Response(500, text="boom"))
    with pytest.raises(CentralError) as e:
        c.get_json("/central/realtime")
    assert e.value.category == "server"
