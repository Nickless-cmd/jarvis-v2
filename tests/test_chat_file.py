"""Rolle-scopet GET /chat/file til preview-panelet i jarvis-desk.

`root` er det navngivne server-root (owner: repo/jarvis-v2/workspace), `path`
er relativt inde i det root. Path-jail forhindrer traversal ud af basen.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.jarvis_api.app import app

client = TestClient(app)


def test_reads_doc_under_repo_root():
    r = client.get(
        "/chat/file",
        params={
            "root": "repo",
            "path": "docs/superpowers/specs/2026-06-11-jarvis-desk-preview-panel-design.md",
        },
    )
    assert r.status_code == 200
    assert "Preview-panel" in r.json()["content"]


def test_rejects_path_traversal():
    r = client.get("/chat/file", params={"root": "repo", "path": "../../etc/passwd"})
    assert r.status_code == 403


def test_rejects_unknown_root_name():
    r = client.get("/chat/file", params={"root": "etc", "path": "hosts"})
    assert r.status_code == 403


def test_404_for_missing_under_root():
    r = client.get("/chat/file", params={"root": "repo", "path": "docs/does-not-exist-xyz.md"})
    assert r.status_code == 404


def test_container_write_roundtrip(monkeypatch, tmp_path):
    # In-app editor gemmer en fil i et rolle-tilladt root (jailet).
    import apps.api.jarvis_api.routes.chat as chatmod
    monkeypatch.setattr(chatmod, "_resolve_role", lambda uid: "owner")
    monkeypatch.setattr(chatmod, "_allowed_roots", lambda role, uid: {"workspace": tmp_path})

    r = client.post("/chat/file", json={"root": "workspace", "path": "sub/note.md", "content": "hej\n"})
    assert r.status_code == 200
    assert (tmp_path / "sub" / "note.md").read_text() == "hej\n"


def test_container_write_rejects_path_outside_jail(monkeypatch, tmp_path):
    import apps.api.jarvis_api.routes.chat as chatmod
    monkeypatch.setattr(chatmod, "_resolve_role", lambda uid: "owner")
    monkeypatch.setattr(chatmod, "_allowed_roots", lambda role, uid: {"workspace": tmp_path})

    r = client.post("/chat/file", json={"root": "workspace", "path": "../escape.md", "content": "x"})
    assert r.status_code == 403


def test_open_external_rejects_container():
    # Container har ingen lokal OS-editor — in-app editoren håndterer det.
    r = client.post("/chat/open-external", json={"root": "repo", "path": "x.py", "kind": "container"})
    assert r.status_code == 400


def test_workstation_reads_via_operator_result_shape(monkeypatch):
    # Ægte form: _run_operator_async pakker bro-svaret i {"status","result"};
    # operator_read_file_async returnerer filindholdet som ren streng.
    import apps.api.jarvis_api.routes.chat as chatmod

    def fake_exec(name, args):
        assert name == "operator_read_file"
        assert args["path"] == "/home/bs/proj/main.py"
        return {"status": "ok", "result": "print('hej')\n"}
    monkeypatch.setattr(chatmod, "_operator_exec", fake_exec)

    r = client.get(
        "/chat/file",
        params={"kind": "workstation", "root": "/home/bs/proj", "path": "main.py"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["content"] == "print('hej')\n"
    assert body["language"] == "python"
