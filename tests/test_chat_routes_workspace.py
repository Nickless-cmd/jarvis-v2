"""Code-mode: workspace-binding via /chat/sessions + mode→tool_scope mapping."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes.chat import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_create_session_persists_workspace(isolated_runtime):
    r = client.post("/chat/sessions", json={
        "title": "kode", "workspace_kind": "container", "workspace_root": "core",
    })
    assert r.status_code == 200
    sid = r.json()["session"]["id"]
    full = client.get(f"/chat/sessions/{sid}").json()
    assert full["session"]["workspace_kind"] == "container"
    assert full["session"]["workspace_root"] == "core"
