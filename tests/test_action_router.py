"""Tests for action_router._reach_out direct-send routing (Phase 2 notif-routing)."""
import types

import core.services.action_router as ar


def _stub_common(monkeypatch, *, owner="bjorn"):
    """Neutralisér cap/cooldown/log-fil-I/O så vi kun tester leverings-stien."""
    monkeypatch.setattr(ar, "_proactive_messages_today", lambda: 0)
    monkeypatch.setattr(ar, "_within_cooldown", lambda: False)
    monkeypatch.setattr(ar, "_append_proactive", lambda entry: None)
    import core.runtime.settings as settings
    monkeypatch.setattr(settings, "load_settings",
                        lambda: types.SimpleNamespace(extra={"owner_user_id": owner}))


def test_reach_out_routes_via_notification_router(monkeypatch):
    _stub_common(monkeypatch)
    import core.services.notification_router as nr
    seen = {}
    monkeypatch.setattr(nr, "route_proactive_notification",
                        lambda uid, t, p, **k: seen.update(uid=uid, t=t) or {"delivered": True})
    # ntfy må IKKE kaldes når routeren leverer:
    monkeypatch.setattr(ar, "_send_ntfy", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ntfy ramt")))
    entry = ar._reach_out(message="hej", importance="normal", bypass_nudge=True, source="test")
    assert entry["outcome"] == "sent"
    assert seen == {"uid": "bjorn", "t": "reach_out"}


def test_reach_out_falls_back_to_ntfy_when_router_fails(monkeypatch):
    _stub_common(monkeypatch)
    import core.services.notification_router as nr
    monkeypatch.setattr(nr, "route_proactive_notification", lambda *a, **k: {"delivered": False})
    ntfy_called = {}
    monkeypatch.setattr(ar, "_send_ntfy", lambda msg, **k: ntfy_called.update(msg=msg) or True)
    entry = ar._reach_out(message="vigtigt", importance="high", bypass_nudge=True, source="test")
    assert entry["outcome"] == "sent"
    assert ntfy_called.get("msg") == "vigtigt"  # fallback brugt
