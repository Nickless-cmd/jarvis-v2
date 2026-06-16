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


def test_tree_workstation_forwards_request_uid_to_bridge(monkeypatch):
    # REGRESSION (Mikkel 502): workstation-tree MÅ videregive den autentificerede
    # brugers uid til operator-broen. Ellers falder _operator_user_id tilbage til
    # owner-id'et og rammer den forkerte/fraværende bro → bridge_not_connected → 502.
    import apps.api.jarvis_api.routes.chat as chatmod
    import core.identity.workspace_context as wsctx

    monkeypatch.setattr(wsctx, "current_user_id", lambda: "238975101381378048")
    captured: dict = {}

    def fake_exec(name, args):
        captured["args"] = dict(args)
        return {"status": "ok", "result": []}
    monkeypatch.setattr(chatmod, "_operator_exec", fake_exec)

    r = client.get("/chat/tree", params={"kind": "workstation", "root": "C:\\Jarvis", "path": ""})
    assert r.status_code == 200
    assert captured["args"].get("_user_id") == "238975101381378048"


def test_git_status_workstation_forwards_request_uid_to_bridge(monkeypatch):
    # Samme rod-årsag som tree: git-chip i code-mode skal ramme brugerens egen bro.
    import apps.api.jarvis_api.routes.chat as chatmod
    import core.identity.workspace_context as wsctx

    monkeypatch.setattr(wsctx, "current_user_id", lambda: "238975101381378048")
    captured: dict = {}

    def fake_exec(name, args):
        captured["args"] = dict(args)
        return {"status": "ok", "stdout": "main\n@@@\n@@@\n"}
    monkeypatch.setattr(chatmod, "_operator_exec", fake_exec)

    r = client.get("/chat/git-status", params={"kind": "workstation", "root": "C:\\Jarvis"})
    assert r.status_code == 200
    assert captured["args"].get("_user_id") == "238975101381378048"


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
