"""Integration tests: bridge posts to chat only when trigger present."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.runtime import heartbeat_triggers
from core.services import heartbeat_runtime


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspaces" / "default"
    (ws / "runtime").mkdir(parents=True)
    return ws


def _base_policy(workspace: Path, ping_channel: str = "none") -> dict:
    return {
        "workspace": str(workspace),
        "ping_channel": ping_channel,
        "allow_ping": True,
        "kill_switch": "enabled",
    }


def test_propose_silent_when_channel_none_and_no_trigger(workspace: Path) -> None:
    result = heartbeat_runtime._deliver_heartbeat_proposal(
        policy=_base_policy(workspace),
        tick_id="t1",
        summary="summary",
        proposed_action="proposed text",
    )
    assert result["status"] == "recorded"
    assert result["blocked_reason"] == ""


def test_propose_posts_when_trigger_present(workspace: Path, monkeypatch) -> None:
    heartbeat_triggers.set_trigger(
        workspace, reason="project-need", source="test", text="project ping"
    )
    calls: list[dict] = []

    def fake_append(*, session_id, role, content):
        calls.append({"session_id": session_id, "role": role, "content": content})
        return {"id": "msg-1"}

    def fake_list():
        return [{"id": "sess-1"}]

    def fake_get(sid):
        return {"id": sid}

    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "append_chat_message", fake_append)
    monkeypatch.setattr(cs, "list_chat_sessions", fake_list)
    monkeypatch.setattr(cs, "get_chat_session", fake_get)

    result = heartbeat_runtime._deliver_heartbeat_proposal(
        policy=_base_policy(workspace),
        tick_id="t2",
        summary="summary",
        proposed_action="real proposal text",
    )
    assert result["status"] == "sent"
    assert len(calls) == 1
    assert calls[0]["content"] == "real proposal text"
    # Trigger was consumed (queue is empty again)
    assert heartbeat_triggers.peek_trigger(workspace) is None


def test_ping_silent_when_channel_none_and_no_trigger(workspace: Path) -> None:
    result = heartbeat_runtime._deliver_heartbeat_ping_directly(
        policy=_base_policy(workspace),
        tick_id="t3",
        ping_text="a real question from Jarvis",
        summary="summary",
    )
    assert result["status"] == "recorded"


def test_ping_posts_when_trigger_present(workspace: Path, monkeypatch) -> None:
    heartbeat_triggers.set_trigger(
        workspace, reason="user-question", source="test"
    )

    def fake_append(*, session_id, role, content):
        return {"id": "msg-2"}

    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "append_chat_message", fake_append)
    monkeypatch.setattr(cs, "list_chat_sessions", lambda: [{"id": "sess-1"}])
    monkeypatch.setattr(cs, "get_chat_session", lambda sid: {"id": sid})

    result = heartbeat_runtime._deliver_heartbeat_ping_directly(
        policy=_base_policy(workspace),
        tick_id="t4",
        ping_text="a real, non-templated question",
        summary="summary",
    )
    assert result["status"] == "sent"
    assert heartbeat_triggers.peek_trigger(workspace) is None
