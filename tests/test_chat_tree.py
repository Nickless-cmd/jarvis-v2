"""GET /chat/tree — fil-træ til Code mode (container path-jail + workstation bridge)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes.chat import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_tree_container_lists_root_entries():
    r = client.get("/chat/tree", params={"kind": "container", "root": "core", "path": ""})
    assert r.status_code == 200
    names = {e["name"] for e in r.json()["entries"]}
    assert "services" in names or "tools" in names
    assert all(e["kind"] in ("dir", "file") for e in r.json()["entries"])


def test_tree_container_rejects_outside_jail():
    r = client.get("/chat/tree", params={"kind": "container", "root": "etc", "path": ""})
    assert r.status_code == 403


def test_tree_workstation_routes_through_operator(monkeypatch):
    import apps.api.jarvis_api.routes.chat as chatmod

    def fake_exec(name, args):
        assert name == "operator_list_dir"
        return {"status": "ok", "entries": [
            {"name": "src", "is_dir": True}, {"name": "main.py", "is_dir": False},
        ]}
    monkeypatch.setattr(chatmod, "_operator_exec", fake_exec)

    r = client.get("/chat/tree", params={"kind": "workstation", "root": "/home/bs/proj", "path": ""})
    assert r.status_code == 200
    kinds = {e["name"]: e["kind"] for e in r.json()["entries"]}
    assert kinds["src"] == "dir" and kinds["main.py"] == "file"
