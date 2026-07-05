from __future__ import annotations
from fastapi import FastAPI
from fastapi.testclient import TestClient
import apps.api.jarvis_api.routes.central_breakers as route


def _client(monkeypatch):
    monkeypatch.setattr(route, "_require_owner", lambda: None)
    calls = {}
    monkeypatch.setattr(route, "_reset_breaker", lambda nerve: calls.update({"reset": nerve}))
    monkeypatch.setattr("core.services.central_governance.record_mutation",
                        lambda area, key, value: calls.update({"audit": (area, key, value)}))
    app = FastAPI(); app.include_router(route.router)
    return TestClient(app), calls


def test_reset_requires_confirm(monkeypatch):
    client, calls = _client(monkeypatch)
    r = client.post("/central/breakers/network%2Fhealth/reset", json={"confirm": False})
    assert r.status_code == 200
    assert r.json()["ok"] is False and r.json()["needs_confirm"] is True
    assert "reset" not in calls


def test_reset_with_confirm_resets_and_audits(monkeypatch):
    client, calls = _client(monkeypatch)
    r = client.post("/central/breakers/network%2Fhealth/reset", json={"confirm": True})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert calls["reset"] == "network/health"
    assert calls["audit"] == ("breaker", "network/health", "reset")
