"""Connectors-routes: auth-gating + list/enable/delete bundet til indlogget bruger."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes.connectors import router

app = FastAPI(); app.include_router(router); client = TestClient(app)


def test_get_connectors_requires_auth(monkeypatch):
    import core.identity.workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: "")
    assert client.get("/api/connectors").status_code == 401


def test_get_connectors_lists(monkeypatch):
    import core.identity.workspace_context as wc
    import apps.api.jarvis_api.routes.connectors as cr
    monkeypatch.setattr(wc, "current_user_id", lambda: "u1")
    monkeypatch.setattr(cr, "list_for_user", lambda uid: [{"id": "github", "connected": True}])
    r = client.get("/api/connectors")
    assert r.status_code == 200 and r.json()["connectors"][0]["id"] == "github"


def test_set_enabled(monkeypatch):
    import core.identity.workspace_context as wc
    import apps.api.jarvis_api.routes.connectors as cr
    monkeypatch.setattr(wc, "current_user_id", lambda: "u1")
    seen = {}
    monkeypatch.setattr(cr, "set_enabled", lambda uid, cid, en: seen.update(uid=uid, cid=cid, en=en) or True)
    r = client.post("/api/connectors/github/enabled", json={"enabled": False})
    assert r.status_code == 200 and seen == {"uid": "u1", "cid": "github", "en": False}


def test_delete_connector(monkeypatch):
    import core.identity.workspace_context as wc
    import apps.api.jarvis_api.routes.connectors as cr
    monkeypatch.setattr(wc, "current_user_id", lambda: "u1")
    seen = {}
    monkeypatch.setattr(cr, "delete_for_user", lambda uid, cid: seen.update(uid=uid, cid=cid) or True)
    r = client.delete("/api/connectors/github")
    assert r.status_code == 200 and seen == {"uid": "u1", "cid": "github"}
