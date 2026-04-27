"""Unit tests for wakeup_dispatcher."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.wakeup_dispatcher import dispatch_due_wakeups


def test_dispatch_no_fired_returns_zero():
    with patch("core.services.self_wakeup.due_wakeups", return_value=[]):
        result = dispatch_due_wakeups()
    assert result["dispatched"] == 0


def test_dispatch_fires_webchat_and_marks_dispatched():
    fired = [{"wakeup_id": "w1", "prompt": "check confidence", "reason": "test"}]
    state = [{"wakeup_id": "w1", "prompt": "check confidence", "reason": "test", "status": "fired"}]
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save") as fake_save, \
         patch("core.services.notification_bridge.send_session_notification") as fake_send, \
         patch("core.services.heartbeat_phases.tick_with_phases") as fake_tick:
        result = dispatch_due_wakeups()
    assert result["dispatched"] == 1
    assert "w1" in result["dispatched_ids"]
    fake_send.assert_called_once()
    fake_tick.assert_called_once()
    # Should have set dispatched=True and saved
    assert state[0].get("dispatched") is True
    fake_save.assert_called()


def test_dispatch_skips_already_dispatched():
    fired = [{"wakeup_id": "w1", "prompt": "p", "reason": "r"}]
    state = [{"wakeup_id": "w1", "prompt": "p", "reason": "r", "status": "fired", "dispatched": True}]
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.notification_bridge.send_session_notification") as fake_send:
        result = dispatch_due_wakeups()
    assert result["dispatched"] == 0
    fake_send.assert_not_called()


def test_dispatch_continues_if_webchat_fails():
    fired = [{"wakeup_id": "w1", "prompt": "p", "reason": "r"}]
    state = [{"wakeup_id": "w1", "prompt": "p", "reason": "r", "status": "fired"}]
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.notification_bridge.send_session_notification",
               side_effect=Exception("webchat down")), \
         patch("core.services.heartbeat_phases.tick_with_phases"):
        result = dispatch_due_wakeups()
    # Should still mark dispatched even if webchat fails
    assert result["dispatched"] == 1
    assert state[0].get("dispatched") is True


def test_dispatch_handles_multiple_fired():
    fired = [
        {"wakeup_id": "w1", "prompt": "p1", "reason": "r1"},
        {"wakeup_id": "w2", "prompt": "p2", "reason": "r2"},
    ]
    state = [dict(w, status="fired") for w in fired]
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.notification_bridge.send_session_notification"), \
         patch("core.services.heartbeat_phases.tick_with_phases"):
        result = dispatch_due_wakeups()
    assert result["dispatched"] == 2
