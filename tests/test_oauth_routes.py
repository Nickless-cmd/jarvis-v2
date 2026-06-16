"""OAuth-routes: /start (auth) + /callback (public, signeret state)."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.api.jarvis_api.routes.oauth import router

app = FastAPI(); app.include_router(router); client = TestClient(app)


def test_start_requires_auth(monkeypatch):
    import core.identity.workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: "")
    assert client.get("/api/oauth/github/start").status_code == 401


def test_start_returns_authorize_url(monkeypatch):
    import core.identity.workspace_context as wc
    import core.services.oauth_flow as of
    monkeypatch.setattr(wc, "current_user_id", lambda: "u1")
    monkeypatch.setattr(of, "_secret", lambda k, d="": "CID" if k.endswith("client_id") else d)
    r = client.get("/api/oauth/github/start")
    assert r.status_code == 200 and "github.com/login/oauth/authorize" in r.json()["authorize_url"]


def test_start_unknown_provider(monkeypatch):
    import core.identity.workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: "u1")
    assert client.get("/api/oauth/nope/start").status_code == 404


def test_callback_bad_state():
    assert client.get("/api/oauth/github/callback?code=c&state=bad").status_code == 400


def test_callback_success(monkeypatch):
    import core.services.oauth_flow as of
    import core.services.oauth_store as ostore
    state = of.sign_state("u1", "github")
    monkeypatch.setattr(of, "exchange_code", lambda prov, code: {"access_token": "gho_z"})
    saved: dict = {}
    monkeypatch.setattr(ostore, "save_token",
                        lambda uid, prov, tok: saved.update(uid=uid, prov=prov, tok=tok) or True)
    r = client.get(f"/api/oauth/github/callback?code=abc&state={state}")
    assert r.status_code == 200
    assert saved.get("uid") == "u1" and saved.get("prov") == "github"
