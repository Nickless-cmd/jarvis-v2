from __future__ import annotations
from fastapi import FastAPI
from fastapi.testclient import TestClient
import apps.api.jarvis_api.routes.central_governance as route


def _client(monkeypatch):
    monkeypatch.setattr(route, "_require_owner", lambda: None)  # bypass auth i test
    monkeypatch.setattr(route, "_require_owner_strict", lambda: None)  # bypass strict gate i test
    monkeypatch.setattr("core.services.central_governance.list_flags",
                        lambda: [{"key": "self_prompt", "label": "x", "kind": "bool",
                                  "dangerous": False, "value": True, "options": None}])
    captured = {}
    def _fake_set(key, value, confirm):
        captured["args"] = (key, value, confirm)
        return {"ok": True, "key": key, "value": value}
    monkeypatch.setattr("core.services.central_governance.set_flag", _fake_set)
    app = FastAPI(); app.include_router(route.router)
    return TestClient(app), captured


def test_get_governance_lists_flags(monkeypatch):
    client, _ = _client(monkeypatch)
    r = client.get("/central/governance")
    assert r.status_code == 200
    assert r.json()["flags"][0]["key"] == "self_prompt"


def test_post_set_forwards_to_set_flag(monkeypatch):
    client, captured = _client(monkeypatch)
    r = client.post("/central/governance/set", json={"key": "self_prompt", "value": True, "confirm": True})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert captured["args"] == ("self_prompt", True, True)


def test_post_set_needs_confirm_returns_ok_false(monkeypatch):
    client, _ = _client(monkeypatch)
    monkeypatch.setattr("core.services.central_governance.set_flag",
                        lambda key, value, confirm: {"ok": False, "needs_confirm": True})
    r = client.post("/central/governance/set", json={"key": "lag4_live", "value": False, "confirm": False})
    assert r.status_code == 200
    assert r.json()["ok"] is False and r.json()["needs_confirm"] is True
