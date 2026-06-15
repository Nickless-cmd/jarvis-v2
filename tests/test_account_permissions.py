import asyncio

import apps.api.jarvis_api.routes.account as acc
from apps.api.jarvis_api.routes.account import build_permissions_overview
from core.services.permission_engine import allowed_tools


def test_overview_owner_is_all():
    ov = build_permissions_overview("owner", allowed_tools=allowed_tools)
    chat = next(m for m in ov["modes"] if m["mode"] == "chat")
    assert chat["all"] is True
    assert chat["tools"] == []


def test_overview_member_lists_tools():
    ov = build_permissions_overview("member", allowed_tools=allowed_tools)
    cowork = next(m for m in ov["modes"] if m["mode"] == "cowork")
    assert cowork["all"] is False
    assert "todo_add" in cowork["tools"]


def test_set_computer_use_route(monkeypatch):
    monkeypatch.setattr(acc, "current_context_snapshot", lambda: {"user_id": "u_m"})
    captured = {}
    import core.services.computer_use_policy as cup
    monkeypatch.setattr(cup, "set_computer_use",
                        lambda uid, en: captured.update(uid=uid, en=en) or {"status": "ok", "enabled": en})
    res = asyncio.run(acc.account_set_computer_use({"enabled": False}))
    assert res["enabled"] is False
    assert captured == {"uid": "u_m", "en": False}
