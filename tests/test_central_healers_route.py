from __future__ import annotations
from fastapi import FastAPI
from fastapi.testclient import TestClient
import apps.api.jarvis_api.routes.central_healers as route


def _client(monkeypatch):
    monkeypatch.setattr(route, "_require_owner", lambda: None)
    monkeypatch.setattr("core.services.error_healers.build_healer_surface",
                        lambda: {"registry_enabled": False, "healers": []})
    calls = {}
    monkeypatch.setattr("core.services.error_healers.set_healer_flag",
                        lambda name, enabled: calls.update({"set": (name, enabled)}) or {"ok": True, "name": name, "enabled": enabled})
    monkeypatch.setattr("core.services.central_governance.record_mutation",
                        lambda area, key, value: calls.update({"audit": (area, key, value)}))
    app = FastAPI(); app.include_router(route.router)
    return TestClient(app), calls


def test_get_healers_returns_surface(monkeypatch):
    client, _ = _client(monkeypatch)
    r = client.get("/central/healers")
    assert r.status_code == 200
    assert r.json()["registry_enabled"] is False


def test_post_flag_requires_confirm(monkeypatch):
    client, calls = _client(monkeypatch)
    r = client.post("/central/healers/flag", json={"name": "enabled", "enabled": True, "confirm": False})
    assert r.status_code == 200
    assert r.json()["ok"] is False and r.json()["needs_confirm"] is True
    assert "set" not in calls  # ingen write uden confirm


def test_post_flag_with_confirm_sets_and_audits(monkeypatch):
    client, calls = _client(monkeypatch)
    r = client.post("/central/healers/flag", json={"name": "daemon_restart_live", "enabled": True, "confirm": True})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert calls["set"] == ("daemon_restart_live", True)
    assert calls["audit"] == ("healing", "daemon_restart_live", True)


def test_post_flag_unknown_name_rejected(monkeypatch):
    client, _ = _client(monkeypatch)
    r = client.post("/central/healers/flag", json={"name": "bogus", "enabled": True, "confirm": True})
    assert r.status_code == 200
    assert r.json()["ok"] is False
