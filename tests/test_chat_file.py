"""Path-jailed GET /chat/file til preview-panelet i jarvis-desk."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.jarvis_api.app import app

client = TestClient(app)


def test_reads_whitelisted_doc():
    r = client.get(
        "/chat/file",
        params={"path": "docs/superpowers/specs/2026-06-11-jarvis-desk-preview-panel-design.md"},
    )
    assert r.status_code == 200
    assert "Preview-panel" in r.json()["content"]


def test_rejects_path_traversal():
    r = client.get("/chat/file", params={"path": "../../etc/passwd"})
    assert r.status_code == 403


def test_rejects_outside_whitelist():
    r = client.get("/chat/file", params={"path": "/etc/hosts"})
    assert r.status_code == 403


def test_404_for_missing_whitelisted():
    r = client.get("/chat/file", params={"path": "docs/does-not-exist-xyz.md"})
    assert r.status_code == 404
