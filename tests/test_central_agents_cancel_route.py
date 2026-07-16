from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import apps.api.jarvis_api.routes.central as route
import apps.api.jarvis_api.routes.central_auth as central_auth


def _client(monkeypatch, *, owner_ok=True, cancel_sink=None, cancel_ret=None,
            cancel_exc=None):
    if owner_ok:
        monkeypatch.setattr(central_auth, "require_central_owner", lambda: None)
    else:
        def _deny():
            raise HTTPException(status_code=403, detail="nej")
        monkeypatch.setattr(central_auth, "require_central_owner", _deny)

    def _fake_cancel(agent_id, *, note=""):
        if cancel_sink is not None:
            cancel_sink.append({"agent_id": agent_id, "note": note})
        if cancel_exc is not None:
            raise cancel_exc
        return cancel_ret if cancel_ret is not None else {
            "status": "cancelled", "agent_id": agent_id,
        }
    monkeypatch.setattr(
        "core.services.agent_runtime_spawn.cancel_agent", _fake_cancel
    )

    app = FastAPI()
    app.include_router(route.router)
    return TestClient(app, raise_server_exceptions=False)


def test_cancel_owner_gated(monkeypatch):
    client = _client(monkeypatch, owner_ok=False)
    r = client.post("/central/agents/agent-123/cancel")
    assert r.status_code == 403


def test_cancel_calls_cancel_agent(monkeypatch):
    sink: list = []
    client = _client(monkeypatch, cancel_sink=sink)
    r = client.post("/central/agents/agent-123/cancel")
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "cancel"
    assert body["agent_id"] == "agent-123"
    assert body["status"] == "cancelled"
    assert sink == [{"agent_id": "agent-123", "note": ""}]


def test_cancel_passes_note_from_body(monkeypatch):
    sink: list = []
    client = _client(monkeypatch, cancel_sink=sink)
    r = client.post("/central/agents/agent-123/cancel", json={"note": "stop it"})
    assert r.status_code == 200
    assert sink == [{"agent_id": "agent-123", "note": "stop it"}]


def test_cancel_self_safe_on_error(monkeypatch):
    client = _client(monkeypatch, cancel_exc=RuntimeError("boom"))
    r = client.post("/central/agents/agent-123/cancel")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["agent_id"] == "agent-123"
    assert "boom" in body["detail"]


def test_pause_maps_to_cancel_with_note(monkeypatch):
    sink: list = []
    client = _client(monkeypatch, cancel_sink=sink)
    r = client.post("/central/agents/agent-123/pause")
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "pause"
    assert body["agent_id"] == "agent-123"
    assert sink == [{"agent_id": "agent-123", "note": "paused via central"}]


def test_pause_owner_gated(monkeypatch):
    client = _client(monkeypatch, owner_ok=False)
    r = client.post("/central/agents/agent-123/pause")
    assert r.status_code == 403
