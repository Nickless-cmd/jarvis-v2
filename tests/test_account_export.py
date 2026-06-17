"""GDPR-dataeksport: self-scoped bundt, ingen token-lækage."""
from apps.api.jarvis_api.routes import account
from apps.api.jarvis_api.routes.account import build_data_export


def test_export_bundles_profile_connectors_notes(monkeypatch):
    row = {"user_id": "u_b", "email": "b@x.dk", "email_verified": True, "role": "member"}

    import core.services.connectors as cx
    import core.services.notes_connector as nc
    monkeypatch.setattr(cx, "list_for_user", lambda uid: [
        {"id": "gmail", "name": "Gmail", "kind": "oauth", "status": "available",
         "connected": True, "enabled": True, "scopes": ["secret-scope"]},
    ])
    monkeypatch.setattr(nc, "list_notes", lambda uid, limit=100: {"notes": [{"id": "n1", "text": "hej"}]})

    out = build_data_export("u_b", get_user=lambda uid: row, get_tier=lambda uid: "free")
    assert out["exported_for"] == "u_b"
    assert out["profile"]["email"] == "b@x.dk"
    assert out["connectors"][0]["id"] == "gmail" and out["connectors"][0]["connected"] is True
    assert out["notes"][0]["text"] == "hej"


def test_export_never_leaks_tokens_or_scopes(monkeypatch):
    import core.services.connectors as cx
    import core.services.notes_connector as nc
    monkeypatch.setattr(cx, "list_for_user", lambda uid: [
        {"id": "gmail", "name": "Gmail", "kind": "oauth", "status": "available",
         "connected": True, "enabled": True, "scopes": ["x"], "oauth_scopes": ["y"],
         "access_token": "SHOULD_NOT_APPEAR"},
    ])
    monkeypatch.setattr(nc, "list_notes", lambda uid, limit=100: {"notes": []})
    out = build_data_export("u_b", get_user=lambda uid: {}, get_tier=lambda uid: "free")
    c = out["connectors"][0]
    # kun whitelisten — ingen tokens/scopes med ud
    assert set(c.keys()) == {"id", "name", "kind", "status", "connected", "enabled"}


def test_export_resilient_to_connector_errors(monkeypatch):
    import core.services.connectors as cx
    def boom(uid):
        raise RuntimeError("db nede")
    monkeypatch.setattr(cx, "list_for_user", boom)
    out = build_data_export("", get_user=lambda uid: None, get_tier=lambda uid: "owner")
    assert out["connectors"] == [] and out["exported_for"] == "owner"
