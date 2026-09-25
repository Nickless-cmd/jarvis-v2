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


# ── Livstegnet læste den tomme af to lister (25/9-2026) ─────────────────────


def test_routeren_er_LEVENDE_selv_naar_actions_er_tom():
    """`active` stod som `len(actions) > 0`.

    Målt på CT105 25/9-2026: `actions: 0` mens `proactive_log` havde 217
    poster. Modulet arbejdede påviseligt og meldte sig dødt, fordi nøglen
    læste den ene af to lister.
    """
    import core.services.action_router as AR

    flade = AR.build_action_router_surface()
    assert flade["active"] is True


def test_summaryen_naevner_det_proaktive_naar_actions_er_tom():
    """«Ingen handlinger endnu» var kun halvdelen af sandheden."""
    import core.services.action_router as AR

    tekst = AR._surface_summary([], proactive_today=4, proactive_sent_today=2)
    assert "proaktive" in tekst
    assert "4" in tekst and "2" in tekst

    # Er der intet af nogen slags, står den gamle sætning.
    assert AR._surface_summary([], 0, 0) == "Ingen handlinger endnu"
