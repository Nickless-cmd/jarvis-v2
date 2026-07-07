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
    # Notification now routes through the nudge system when nudge_system_enabled
    # (the default); send_session_notification is only the disabled-nudge fallback.
    fired = [{"wakeup_id": "w1", "prompt": "check confidence", "reason": "test"}]
    state = [{"wakeup_id": "w1", "prompt": "check confidence", "reason": "test", "status": "fired"}]
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save") as fake_save, \
         patch("core.services.outbound_nudges.push_nudge") as fake_push, \
         patch("core.services.heartbeat_phases.tick_with_phases") as fake_tick:
        result = dispatch_due_wakeups()
    assert result["dispatched"] == 1
    assert "w1" in result["dispatched_ids"]
    fake_push.assert_called_once()
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


# ── Discord-routing-guard (Bjørn 2026-06-13: wakeup landede på Discord) ──
from core.services.wakeup_dispatcher import pick_wakeup_run_target


def _ext(sid):
    """Test-stub: sessioner der starter med 'disc-' er Discord-kanaler."""
    return str(sid).startswith("disc-")


def test_app_wakeup_never_routes_to_discord_via_owner_resolver():
    # owner-resolveren ville vælge en Discord-session, men app-resolveren
    # (guardet) returnerer en app-session → app-wakeup lander i app.
    target = pick_wakeup_run_target(
        channel="app", record_session="",
        app_resolver=lambda: "app-42",
        owner_resolver=lambda: "disc-99",  # ville lække til Discord
        is_external=_ext,
    )
    assert target == "app-42"
    assert not _ext(target)


def test_app_wakeup_rejects_explicit_discord_session():
    # Selv en eksplicit Discord-session_id afvises for app-wakeups.
    target = pick_wakeup_run_target(
        channel="app", record_session="disc-7",
        app_resolver=lambda: "app-1",
        owner_resolver=lambda: "disc-7",
        is_external=_ext,
    )
    assert target == "app-1"
    assert not _ext(target)


def test_app_wakeup_falls_back_to_fresh_when_no_app_session():
    # Ingen app-session findes → None (kalderen opretter en frisk app-session),
    # ALDRIG en Discord-session.
    target = pick_wakeup_run_target(
        channel="app", record_session="",
        app_resolver=lambda: "",
        owner_resolver=lambda: "disc-3",
        is_external=_ext,
    )
    assert target is None


def test_default_channel_is_app_guarded():
    # Tom/ukendt channel behandles som app → guardet.
    target = pick_wakeup_run_target(
        channel="", record_session="disc-x",
        app_resolver=lambda: "app-9",
        owner_resolver=lambda: "disc-x",
        is_external=_ext,
    )
    assert target == "app-9"


def test_explicit_discord_channel_still_allowed():
    # Eksplicit channel=="discord" må stadig levere til Discord (separat kanal).
    target = pick_wakeup_run_target(
        channel="discord", record_session="disc-5",
        app_resolver=lambda: "app-1",
        owner_resolver=lambda: "disc-9",
        is_external=_ext,
    )
    assert target == "disc-5"
