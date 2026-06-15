"""GET /chat/tree — fil-træ til Code mode (rolle-scopede navngivne roots + bridge)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes.chat import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_tree_owner_repo_lists_core_as_child():
    # Owner-session (ingen uid) → named root "repo"; "core" er en undermappe.
    r = client.get("/chat/tree", params={"kind": "container", "root": "repo", "path": "core"})
    assert r.status_code == 200
    names = {e["name"] for e in r.json()["entries"]}
    assert "services" in names or "tools" in names
    assert all(e["kind"] in ("dir", "file") for e in r.json()["entries"])


def test_tree_rejects_unknown_root_name():
    r = client.get("/chat/tree", params={"kind": "container", "root": "etc", "path": ""})
    assert r.status_code == 403


def test_tree_rejects_path_traversal_out_of_jail():
    r = client.get("/chat/tree", params={"kind": "container", "root": "repo", "path": "../../etc"})
    assert r.status_code == 403


def test_tree_member_cannot_browse_repo(monkeypatch):
    # Member-bruger må KUN se eget workspace — repo er ikke et tilladt root.
    import apps.api.jarvis_api.routes.chat as chatmod

    monkeypatch.setattr(chatmod, "_resolve_role", lambda uid: "member")

    r = client.get("/chat/tree", params={"kind": "container", "root": "repo", "path": ""})
    assert r.status_code == 403


def test_tree_member_can_browse_own_workspace(monkeypatch, tmp_path):
    import apps.api.jarvis_api.routes.chat as chatmod

    (tmp_path / "notes.md").write_text("hej")
    monkeypatch.setattr(chatmod, "_resolve_role", lambda uid: "member")
    monkeypatch.setattr(
        chatmod, "_allowed_roots", lambda role, uid: {"workspace": tmp_path}
    )

    r = client.get("/chat/tree", params={"kind": "container", "root": "workspace", "path": ""})
    assert r.status_code == 200
    names = {e["name"] for e in r.json()["entries"]}
    assert "notes.md" in names


def test_tree_workstation_routes_through_operator(monkeypatch):
    import apps.api.jarvis_api.routes.chat as chatmod

    def fake_exec(name, args):
        # Ægte form: _run_operator_async pakker bro-listen i {"status","result"}.
        # operator_list_dir_async returnerer [{name, type, size}] (type, ikke is_dir).
        assert name == "operator_list_dir"
        return {"status": "ok", "result": [
            {"name": "src", "type": "dir"}, {"name": "main.py", "type": "file"},
            {"name": ".git", "type": "dir"},
        ]}
    monkeypatch.setattr(chatmod, "_operator_exec", fake_exec)

    r = client.get("/chat/tree", params={"kind": "workstation", "root": "/home/bs/proj", "path": ""})
    assert r.status_code == 200
    kinds = {e["name"]: e["kind"] for e in r.json()["entries"]}
    assert kinds["src"] == "dir" and kinds["main.py"] == "file"
