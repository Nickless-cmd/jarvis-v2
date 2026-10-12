from __future__ import annotations

import pytest


def test_notification_bridge_rejects_routine_session_delivery(monkeypatch):
    from core.services.notification_bridge import send_session_notification

    monkeypatch.setattr(
        "core.services.chat_sessions.append_chat_message",
        lambda **_kw: pytest.fail("routine content reached a chat session"),
    )
    assert send_session_notification("private", source="routine-result") == {
        "status": "blocked",
        "error": "routine-session-delivery-forbidden",
    }


def test_heartbeat_delivery_is_blocked_when_cutover_is_active(monkeypatch):
    from core.services.heartbeat_delivery import _deliver_heartbeat_ping_directly

    monkeypatch.setenv("JARVIS_ROUTINES_CUTOVER", "1")
    result = _deliver_heartbeat_ping_directly(
        policy={}, tick_id="tick-1", ping_text="private", summary="private"
    )
    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "routine-session-delivery-forbidden"
