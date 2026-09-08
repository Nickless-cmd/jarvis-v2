"""Connector-katalog: per-bruger status + enable + delete (revoke+wipe)."""
from __future__ import annotations

import core.services.connectors as cx


def _patch_state(monkeypatch):
    store: dict = {}
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "get_runtime_state_value", lambda k, d=None: store.get(k, d))
    monkeypatch.setattr(dbc, "set_runtime_state_value", lambda k, v, **kw: store.__setitem__(k, v))
    return store


def test_catalog_status(monkeypatch):
    _patch_state(monkeypatch)
    monkeypatch.setattr(cx, "has_token", lambda uid, pid: pid == "github")
    items = cx.list_for_user("alice")
    gh = next(i for i in items if i["id"] == "github")
    assert gh["connected"] is True and gh["kind"] == "oauth"
    assert gh["enabled"] is True  # default on
    # available lokale connectors er altid "connected" (coming_soon ikke)
    local = [i for i in items if i["kind"] == "local" and i["status"] == "available"]
    assert local and all(i["connected"] is True for i in local)


def test_coming_soon_visible_but_not_connectable(monkeypatch):
    _patch_state(monkeypatch)
    # selv hvis et token skulle findes, må coming_soon ALDRIG vise connected.
    monkeypatch.setattr(cx, "has_token", lambda uid, pid: True)
    items = cx.list_for_user("alice")
    ids = {i["id"] for i in items}
    assert {"gmail", "google-calendar", "google-drive", "google-docs",
            "google-sheets", "google-slides"} <= ids
    assert {"build-web-apps", "huggingface", "pdf", "spotify", "slack", "notion"} <= ids
    # spotify er stadig coming_soon → aldrig connected, selv med token.
    sp = next(i for i in items if i["id"] == "spotify")
    assert sp["status"] == "coming_soon"
    assert sp["connected"] is False
    gh = next(i for i in items if i["id"] == "github")
    assert gh["status"] == "available"


def test_oauth_request_maps_gmail_to_google(monkeypatch):
    # gmail-connector deler Google-OAuth: id 'gmail' → provider 'google' + gmail-scopes.
    req = cx.oauth_request_for("gmail")
    assert req is not None
    provider, scopes = req
    assert provider == "google"
    assert any("gmail.readonly" in s for s in scopes)
    # github falder tilbage til sit eget id som provider, ingen eksplicitte scopes.
    assert cx.oauth_request_for("github") == ("github", [])
    # lokal connector er ikke oauth → None.
    assert cx.oauth_request_for("browser") is None


def _google_token(monkeypatch, scope: str):
    """Token gemt under provider 'google' — connectoren hedder 'gmail'."""
    monkeypatch.setattr(cx, "has_token", lambda uid, pid: pid == "google")
    monkeypatch.setattr(cx, "get_token", lambda uid, pid: {"scope": scope})


def test_gmail_connected_uses_google_token(monkeypatch):
    _patch_state(monkeypatch)
    # token gemt under provider 'google' (ikke 'gmail') → gmail viser connected.
    _patch = next(c for c in cx._CATALOG if c["id"] == "gmail")
    _google_token(monkeypatch, " ".join(_patch.get("oauth_scopes") or []))
    items = cx.list_for_user("alice")
    gmail = next(i for i in items if i["id"] == "gmail")
    assert gmail["status"] == "available" and gmail["connected"] is True


def test_en_google_token_UDEN_kalender_scope_forbinder_ikke_kalenderen(monkeypatch):
    """Syv connectors deler tre udbydere. Før 8/9-2026 gjorde én gmail-token
    alle fem andre Google-apps «forbundne» — og så viste Marketplace ingen
    «Forbind»-knap, så de kunne heller ikke gen-godkendes."""
    _patch_state(monkeypatch)
    gmail = next(c for c in cx._CATALOG if c["id"] == "gmail")
    _google_token(monkeypatch, " ".join(gmail.get("oauth_scopes") or []))
    items = {i["id"]: i for i in cx.list_for_user("alice")}
    assert items["gmail"]["connected"] is True
    assert items["google-calendar"]["connected"] is False
    assert items["google-drive"]["connected"] is False


def test_set_enabled_roundtrip(monkeypatch):
    _patch_state(monkeypatch)
    monkeypatch.setattr(cx, "has_token", lambda uid, pid: False)
    assert cx.is_enabled("alice", "github") is True  # default
    cx.set_enabled("alice", "github", False)
    assert cx.is_enabled("alice", "github") is False
    # isolation: bob upåvirket
    assert cx.is_enabled("bob", "github") is True


def test_delete_revokes_then_wipes(monkeypatch):
    _patch_state(monkeypatch)
    calls = {}
    monkeypatch.setattr(cx, "get_fresh_token", lambda uid, pid: {"access_token": "t"})
    import core.services.oauth_flow as of
    monkeypatch.setattr(of, "revoke_remote", lambda prov, tok: calls.setdefault("revoked", True) or True)
    import core.services.oauth_store as ov
    monkeypatch.setattr(ov, "revoke_token", lambda uid, pid: calls.setdefault("wiped", True) or True)
    assert cx.delete_for_user("alice", "github") is True
    assert calls == {"revoked": True, "wiped": True}
