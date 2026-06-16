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
    # lokale connectors er altid "connected"
    local = [i for i in items if i["kind"] == "local"]
    assert local and all(i["connected"] is True for i in local)


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
