import asyncio

import apps.api.jarvis_api.routes.cowork as cw


def test_create_todo_owner(monkeypatch):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    captured = {}
    import core.services.agent_todos as at
    monkeypatch.setattr(at, "add_cowork_todo", lambda c: captured.update(content=c) or {"status": "ok"})
    res = asyncio.run(cw.cowork_create_todo({"content": "ny opgave"}))
    assert res["status"] == "ok"
    assert captured["content"] == "ny opgave"


def test_create_todo_member_forbidden(monkeypatch):
    monkeypatch.setattr(cw, "_role_owner", lambda: (False, "u_m"))
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        asyncio.run(cw.cowork_create_todo({"content": "x"}))
    assert ei.value.status_code == 403


def test_set_status_validates(monkeypatch):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    res = asyncio.run(cw.cowork_set_todo_status("td-1", {"status": "bogus"}))
    assert res["status"] == "error"
