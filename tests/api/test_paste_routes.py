"""Verify /paste endpoints save + resolve pastes.

Tests the route directly (minimal app) to stay fast and independent.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes.paste import router as paste_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(paste_router)
    return TestClient(app)


def test_post_paste_returns_id_and_reference(isolated_runtime):
    with _client() as c:
        r = c.post("/paste", json={"text": "line 1\nline 2\nline 3"})
        assert r.status_code == 200
        body = r.json()
        assert body["paste_id"]
        assert body["line_count"] == 3
        assert body["reference"] == f"[paste:{body['paste_id']} +3 linjer]"


def test_post_paste_is_idempotent(isolated_runtime):
    with _client() as c:
        a = c.post("/paste", json={"text": "same content\nhere"}).json()
        b = c.post("/paste", json={"text": "same content\nhere"}).json()
        assert a["paste_id"] == b["paste_id"]


def test_post_empty_paste_rejected(isolated_runtime):
    with _client() as c:
        r = c.post("/paste", json={"text": "   "})
        assert r.status_code == 400


def test_get_paste_returns_full_text(isolated_runtime):
    with _client() as c:
        text = "def foo():\n    return 42"
        paste_id = c.post("/paste", json={"text": text}).json()["paste_id"]
        r = c.get(f"/paste/{paste_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == paste_id
        assert body["text"] == text
        assert body["line_count"] == 2


def test_get_unknown_paste_404(isolated_runtime):
    with _client() as c:
        r = c.get("/paste/doesnotexist")
        assert r.status_code == 404
