# tests/test_attachment_service.py
from __future__ import annotations
import pytest


# ---------------------------------------------------------------------------
# download_and_store
# ---------------------------------------------------------------------------

def test_download_and_store_returns_ok(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_UPLOAD_ROOT", tmp_path)

    def fake_download(url, headers):
        return b"fake image data"

    monkeypatch.setattr(svc, "_http_download", fake_download)
    monkeypatch.setattr(svc, "_db_store", lambda **kw: None)

    result = svc.download_and_store(
        url="https://cdn.discord.com/photo.jpg",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=100,
        session_id="sess-1",
        channel_type="discord",
    )
    assert result["status"] == "ok"
    assert "attachment_id" in result
    saved = tmp_path / "sess-1" / f"{result['attachment_id']}_photo.jpg"
    assert saved.exists()
    assert saved.read_bytes() == b"fake image data"


def test_download_and_store_rejects_too_large(monkeypatch):
    import core.services.attachment_service as svc
    result = svc.download_and_store(
        url="https://cdn.discord.com/big.zip",
        filename="big.zip",
        mime_type="application/zip",
        size_bytes=svc.MAX_SIZE_BYTES + 1,
        session_id="sess-1",
        channel_type="discord",
    )
    assert result["status"] == "error"
    assert result["reason"] == "too_large"


def test_download_and_store_handles_download_failure(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_UPLOAD_ROOT", tmp_path)

    def fail_download(url, headers):
        raise OSError("timeout")

    monkeypatch.setattr(svc, "_http_download", fail_download)

    result = svc.download_and_store(
        url="https://cdn.discord.com/photo.jpg",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=100,
        session_id="sess-1",
        channel_type="discord",
    )
    assert result["status"] == "error"
    assert result["reason"] == "download_failed"


# ---------------------------------------------------------------------------
# get_attachment / list_attachments
# ---------------------------------------------------------------------------

def test_get_attachment_returns_metadata(monkeypatch):
    import core.services.attachment_service as svc
    fake_row = {
        "attachment_id": "abc-123", "session_id": "sess-1",
        "channel_type": "discord", "filename": "photo.jpg",
        "mime_type": "image/jpeg", "size_bytes": 100,
        "local_path": "/tmp/photo.jpg", "source_url": "", "created_at": "2026-04-23T00:00:00",
    }
    monkeypatch.setattr(svc, "_db_get", lambda attachment_id: fake_row)
    result = svc.get_attachment("abc-123")
    assert result["filename"] == "photo.jpg"


def test_get_attachment_returns_none_for_unknown(monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_db_get", lambda attachment_id: None)
    assert svc.get_attachment("unknown-id") is None


def test_list_attachments_returns_list(monkeypatch):
    import core.services.attachment_service as svc
    fake_rows = [
        {"attachment_id": "x1", "filename": "a.jpg", "session_id": "sess-1",
         "channel_type": "discord", "mime_type": "image/jpeg", "size_bytes": 1,
         "local_path": "", "source_url": "", "created_at": ""},
    ]
    monkeypatch.setattr(svc, "_db_list", lambda session_id, limit: fake_rows)
    rows = svc.list_attachments("sess-1")
    assert len(rows) == 1
    assert rows[0]["filename"] == "a.jpg"


# ---------------------------------------------------------------------------
# read_attachment_content
# ---------------------------------------------------------------------------

def test_read_attachment_content_unknown_id(monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_db_get", lambda attachment_id: None)
    result = svc.read_attachment_content("unknown")
    assert result["status"] == "error"
    assert result["reason"] == "not-found"


def test_read_attachment_content_text_file(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    txt = tmp_path / "note.txt"
    txt.write_text("hello world")
    row = {
        "attachment_id": "t1", "filename": "note.txt", "mime_type": "text/plain",
        "local_path": str(txt), "session_id": "s", "channel_type": "discord",
        "size_bytes": 11, "source_url": "", "created_at": "",
    }
    monkeypatch.setattr(svc, "_db_get", lambda aid: row)
    result = svc.read_attachment_content("t1")
    assert result["status"] == "ok"
    assert result["type"] == "text"
    assert "hello world" in result["content"]


def test_read_attachment_content_image_calls_vision(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    img = tmp_path / "pic.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    row = {
        "attachment_id": "i1", "filename": "pic.jpg", "mime_type": "image/jpeg",
        "local_path": str(img), "session_id": "s", "channel_type": "discord",
        "size_bytes": 3, "source_url": "", "created_at": "",
    }
    monkeypatch.setattr(svc, "_db_get", lambda aid: row)
    called = {}
    def fake_vision(b64, *, model, prompt=None):
        called["b64"] = b64
        return "a nice photo"
    monkeypatch.setattr(svc, "_call_vision", fake_vision)
    result = svc.read_attachment_content("i1")
    assert result["status"] == "ok"
    assert result["type"] == "image"
    assert "a nice photo" in result["content"]
    assert "b64" in called


# ---------------------------------------------------------------------------
# validate_send_path
# ---------------------------------------------------------------------------

def test_validate_send_path_rejects_outside_roots(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_ALLOWED_SEND_ROOTS", [tmp_path / "uploads"])
    ok, err = svc.validate_send_path("/etc/passwd")
    assert not ok
    assert "not-allowed" in err


def test_validate_send_path_rejects_missing_file(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(svc, "_ALLOWED_SEND_ROOTS", [uploads])
    ok, err = svc.validate_send_path(str(uploads / "missing.jpg"))
    assert not ok
    assert "not-found" in err


def test_validate_send_path_accepts_valid_file(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    f = uploads / "file.jpg"
    f.write_bytes(b"data")
    monkeypatch.setattr(svc, "_ALLOWED_SEND_ROOTS", [uploads])
    ok, err = svc.validate_send_path(str(f))
    assert ok
    assert err == ""
