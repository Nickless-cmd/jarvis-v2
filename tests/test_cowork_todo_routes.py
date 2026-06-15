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


def test_set_expiry_owner(monkeypatch):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    captured = {}
    import core.services.agent_todos as at
    monkeypatch.setattr(at, "set_todo_expiry_anywhere",
                        lambda tid, exp: captured.update(tid=tid, exp=exp) or {"status": "ok"})
    res = asyncio.run(cw.cowork_set_todo_expiry("td-1", {"expires_at": "2099-01-01T00:00:00+00:00"}))
    assert res["status"] == "ok"
    assert captured["exp"] == "2099-01-01T00:00:00+00:00"


def test_pause_is_accepted_status(monkeypatch):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    import core.services.agent_todos as at
    monkeypatch.setattr(at, "update_todo_status_anywhere", lambda tid, s: {"status": "ok", "to": s})
    res = asyncio.run(cw.cowork_set_todo_status("td-1", {"status": "paused"}))
    assert res["status"] == "ok"
