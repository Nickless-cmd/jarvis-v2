import asyncio

import apps.api.jarvis_api.routes.push as push_routes
import core.services.device_tokens as dt


def _clear():
    dt._ensure_table()
    from core.runtime.db import connect
    with connect() as c:
        c.execute("DELETE FROM device_tokens")


def test_register_scopes_to_auth_user(monkeypatch):
    _clear()
    monkeypatch.setattr(push_routes, "_current_user", lambda: "bjorn")
    res = asyncio.run(push_routes.register(push_routes.RegisterBody(token="tok-Z", platform="android")))
    assert res == {"ok": True}
    assert dt.list_for_user("bjorn") == ["tok-Z"]
    res2 = asyncio.run(push_routes.unregister(push_routes.UnregisterBody(token="tok-Z")))
    assert res2 == {"ok": True}
    assert dt.list_for_user("bjorn") == []


def test_register_rejects_when_no_user(monkeypatch):
    _clear()
    monkeypatch.setattr(push_routes, "_current_user", lambda: None)
    res = asyncio.run(push_routes.register(push_routes.RegisterBody(token="tok-Q")))
    assert res == {"ok": False}
    assert dt.list_for_user("bjorn") == []
