from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import apps.api.jarvis_api.routes.central_absorb_routes as route


_SURFACE = {
    "fetched_at": "2026-07-05T00:00:00Z",
    "agents": [
        {"agent_id": "a1", "name": "Scout", "role": "researcher", "status": "active"},
        {"agent_id": "a2", "name": "Builder", "role": "engineer", "status": "completed"},
    ],
    "summary": {"agent_count": 2},
}


def _client(monkeypatch, *, surface=_SURFACE, owner_ok=True, absorb_sink=None):
    if owner_ok:
        monkeypatch.setattr(route, "require_central_owner", lambda: None)
    else:
        def _deny():
            raise HTTPException(status_code=403, detail="nej")
        monkeypatch.setattr(route, "require_central_owner", _deny)

    def _builder(limit=100):
        if isinstance(surface, Exception):
            raise surface
        return surface
    monkeypatch.setattr(
        "core.services.agent_runtime.build_agent_runtime_surface", _builder
    )

    if absorb_sink is not None:
        def _fake_absorb(cluster, nerve, value, **kw):
            absorb_sink.append((cluster, nerve, value, kw))
        monkeypatch.setattr(route, "absorb", _fake_absorb)

    app = FastAPI()
    app.include_router(route.router)
    return TestClient(app, raise_server_exceptions=False)


def test_owner_gated(monkeypatch):
    client = _client(monkeypatch, owner_ok=False)
    r = client.get("/central/agents")
    assert r.status_code == 403


def test_projects_producer(monkeypatch):
    client = _client(monkeypatch)
    r = client.get("/central/agents")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["agents"] == _SURFACE["agents"]


def test_absorb_called_with_agent_cluster(monkeypatch):
    sink: list = []
    client = _client(monkeypatch, absorb_sink=sink)
    r = client.get("/central/agents")
    assert r.status_code == 200
    assert sink, "absorb should have been called"
    cluster, nerve, value, kw = sink[0]
    assert cluster == "agent"
    assert value == {"count": 2}


def test_self_safe_on_builder_error(monkeypatch):
    client = _client(monkeypatch, surface=RuntimeError("boom"))
    r = client.get("/central/agents")
    assert r.status_code == 200
    body = r.json()
    assert body["agents"] == []
    assert body["count"] == 0
