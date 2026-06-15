import asyncio

import apps.api.jarvis_api.routes.account as acc
from apps.api.jarvis_api.routes.account import build_apps_overview


class _M:
    def __init__(self, pid, name, kind):
        self.plugin_id = pid
        self.name = name
        self.kind = kind


def test_build_apps_only_connectors():
    plugins = [_M("gmail", "Gmail", "connector"), _M("discord", "Discord", "channel")]
    ov = build_apps_overview(
        available=lambda: plugins,
        get_status=lambda pid: {"status": "connected", "detail": ""},
    )
    ids = {a["plugin_id"] for a in ov["apps"]}
    assert ids == {"gmail"}
    assert ov["apps"][0]["status"] == "connected"


def test_mcp_add_owner_only(monkeypatch):
    monkeypatch.setattr(acc, "_current_role", lambda uid: "member")
    monkeypatch.setattr(acc, "current_context_snapshot", lambda: {"user_id": "u_m"})
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        asyncio.run(acc.account_mcp_add({"name": "x", "url": "y"}))
    assert ei.value.status_code == 403


def test_mcp_add_applies(monkeypatch):
    monkeypatch.setattr(acc, "_current_role", lambda uid: "owner")
    monkeypatch.setattr(acc, "current_context_snapshot", lambda: {"user_id": ""})
    import core.services.mcp_registry as mr
    captured = {}
    monkeypatch.setattr(mr, "add_mcp_server", lambda name, url: captured.update(n=name, u=url) or {"status": "ok"})
    res = asyncio.run(acc.account_mcp_add({"name": "CF", "url": "https://x"}))
    assert res["status"] == "ok"
    assert captured == {"n": "CF", "u": "https://x"}
