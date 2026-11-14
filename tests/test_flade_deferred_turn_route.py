from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException


def test_execute_chat_tool_bruger_chat_scope_og_den_normale_gate(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import flade_deferred_turn as route
    from core.tools.tool_scoping import current_tool_scope

    set_scope: list[str] = []

    monkeypatch.setattr(route, "get_tool_definitions", lambda scope=None: [
        {"function": {"name": "weather"}},
    ])

    def fake_execute(name: str, arguments: dict) -> dict:
        set_scope.append(current_tool_scope())
        return {"status": "ok", "name": name, "arguments": arguments}

    monkeypatch.setattr(route, "execute_tool", fake_execute)
    result, allowed = route._execute_chat_tool("weather", {"location": "Svendborg"})

    assert allowed == {"weather"}
    assert set_scope == ["chat"]
    assert result["status"] == "ok"


def test_execute_chat_tool_afviser_ukendt_foer_dispatch(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import flade_deferred_turn as route

    monkeypatch.setattr(route, "get_tool_definitions", lambda scope=None: [])
    monkeypatch.setattr(route, "execute_tool", lambda *_: (_ for _ in ()).throw(AssertionError("bypass")))

    result, allowed = route._execute_chat_tool("bash", {"command": "echo bypass"})
    assert allowed == set()
    assert result is None


def test_deferred_turn_er_bundet_til_kildebeskeden(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import flade_deferred_turn as route

    body = route.DeferredToolTurnBody(address={
        "accountId": "owner-1",
        "conversationId": "chat-1",
        "sourceMessageId": "msg-1",
        "widgetInstanceId": "widget-1",
        "contentRevision": 2,
    }, tool="weather", arguments={"location": "Svendborg"})
    monkeypatch.setattr(route, "_current_user_id", lambda: "owner-1")
    monkeypatch.setattr(route, "_kraev_adgang", lambda _sid: None)
    monkeypatch.setattr(route, "_source_message_belongs", lambda mid, sid: (mid, sid) == ("msg-1", "chat-1"))
    monkeypatch.setattr(route, "_execute_chat_tool", lambda *_: ({"status": "ok", "temperature": 12}, {"weather"}))

    result = asyncio.run(route.flade_deferred_tool_turn(body))
    assert result["status"] == "delivered"
    assert result["address"]["sourceMessageId"] == "msg-1"
    assert result["address"]["contentRevision"] == 3


def test_deferred_turn_afviser_en_besked_fra_en_anden_samtale(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import flade_deferred_turn as route

    body = route.DeferredToolTurnBody(address={
        "conversationId": "chat-1", "sourceMessageId": "foreign",
        "widgetInstanceId": "widget-1", "contentRevision": 0,
    }, tool="weather", arguments={})
    monkeypatch.setattr(route, "_current_user_id", lambda: "owner-1")
    monkeypatch.setattr(route, "_kraev_adgang", lambda _sid: None)
    monkeypatch.setattr(route, "_source_message_belongs", lambda *_: False)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(route.flade_deferred_tool_turn(body))
    assert caught.value.status_code == 404
