"""Tests for outreach_composer._send_message routing via notification_router (Bjørn 2026-06-21)."""
import types
import core.services.outreach_composer as oc


def test_send_message_routes_through_notification_router(monkeypatch):
    import core.services.notification_router as nr
    import core.runtime.settings as settings
    monkeypatch.setattr(settings, "load_settings",
                        lambda: types.SimpleNamespace(extra={"owner_user_id": "bjorn"}))
    seen = {}
    monkeypatch.setattr(nr, "deliver_message",
                        lambda uid, text, ntype="reach_out": seen.update(uid=uid, ntype=ntype, text=text)
                        or {"sent": True, "channel": "webchat"})
    r = oc._send_message("Godmorgen", channel="discord")  # channel-hint ignoreres nu
    assert r["sent"] is True
    assert seen == {"uid": "bjorn", "ntype": "reach_out", "text": "Godmorgen"}


def test_send_message_falls_back_when_owner_unknown(monkeypatch):
    import core.runtime.settings as settings
    monkeypatch.setattr(settings, "load_settings",
                        lambda: types.SimpleNamespace(extra={}))  # ingen owner-id
    # fallback: webchat-sti
    import core.services.notification_bridge as nb
    monkeypatch.setattr(nb, "send_session_notification", lambda t, **k: {"status": "ok"})
    r = oc._send_message("hej", channel="webchat")
    assert r["sent"] is True and r["channel"] == "webchat"
