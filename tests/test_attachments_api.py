"""Tests for attachment upload and serve endpoints."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes.attachments import AttachmentMeta, router, _registry

app = FastAPI()
app.include_router(router)
client = TestClient(app)

FAKE_SESSION = "chat-testsession123"


@pytest.fixture(autouse=True)
def clear_registry():
    _registry.clear()
    yield
    _registry.clear()


@pytest.fixture(autouse=True)
def mock_session_and_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.attachments.get_chat_session",
        lambda sid: {"id": sid} if sid == FAKE_SESSION else None,
    )
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.attachments._UPLOAD_DIR",
        tmp_path / "uploads",
    )


def test_upload_image_success():
    data = b"\x89PNG\r\n" + b"x" * 100
    response = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("photo.png", io.BytesIO(data), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "id" in body
    assert body["filename"] == "photo.png"
    assert body["mime_type"] == "image/png"
    assert body["size_bytes"] == len(data)


def test_upload_unknown_session_rejected():
    response = client.post(
        "/attachments/upload",
        data={"session_id": "chat-doesnotexist"},
        files={"file": ("x.txt", io.BytesIO(b"hi"), "text/plain")},
    )
    assert response.status_code == 404


def test_upload_enforces_image_limit():
    for i in range(25):
        _registry[f"fake-{i}"] = AttachmentMeta(
            id=f"fake-{i}", session_id=FAKE_SESSION,
            filename=f"img{i}.jpg", mime_type="image/jpeg",
            size_bytes=100, server_path="/tmp/fake",
        )
    response = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("extra.jpg", io.BytesIO(b"x"), "image/jpeg")},
    )
    assert response.status_code == 400
    assert "25" in response.json()["detail"]


def test_serve_attachment():
    data = b"hello world"
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("note.txt", io.BytesIO(data), "text/plain")},
    )
    assert resp.status_code == 200
    aid = resp.json()["id"]

    serve_resp = client.get(f"/attachments/{aid}?session_id={FAKE_SESSION}")
    assert serve_resp.status_code == 200
    assert serve_resp.content == data


def test_serve_wrong_session_rejected():
    data = b"secret"
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("f.txt", io.BytesIO(data), "text/plain")},
    )
    aid = resp.json()["id"]
    resp2 = client.get(f"/attachments/{aid}?session_id=chat-wrongsession")
    assert resp2.status_code == 403


def test_serve_unknown_id():
    resp = client.get(f"/attachments/doesnotexist?session_id={FAKE_SESSION}")
    assert resp.status_code == 404
