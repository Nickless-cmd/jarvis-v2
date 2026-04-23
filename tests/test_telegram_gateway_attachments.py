# tests/test_telegram_gateway_attachments.py
from __future__ import annotations
import pytest


# ---------------------------------------------------------------------------
# _resolve_telegram_file_url
# ---------------------------------------------------------------------------

def test_resolve_telegram_file_url(monkeypatch):
    import core.services.telegram_gateway as gw
    monkeypatch.setattr(gw, "_api_get",
        lambda token, method, payload: {"ok": True, "result": {"file_path": "photos/file_42.jpg"}})
    url = gw._resolve_telegram_file_url(token="tok123", file_id="FILE_ID_X")
    assert url == "https://api.telegram.org/file/bottok123/photos/file_42.jpg"


def test_resolve_telegram_file_url_api_failure(monkeypatch):
    import core.services.telegram_gateway as gw
    monkeypatch.setattr(gw, "_api_get", lambda t, m, p: {"ok": False})
    result = gw._resolve_telegram_file_url(token="tok", file_id="bad")
    assert result is None


# ---------------------------------------------------------------------------
# _extract_telegram_media
# ---------------------------------------------------------------------------

def test_extract_telegram_media_photo():
    import core.services.telegram_gateway as gw
    msg = {
        "photo": [
            {"file_id": "small", "file_size": 100},
            {"file_id": "large", "file_size": 5000},
        ]
    }
    items = gw._extract_telegram_media(msg)
    assert len(items) == 1
    assert items[0]["file_id"] == "large"
    assert items[0]["mime_type"] == "image/jpeg"
    assert items[0]["filename"] == "photo.jpg"


def test_extract_telegram_media_document():
    import core.services.telegram_gateway as gw
    msg = {
        "document": {
            "file_id": "doc123",
            "file_name": "report.pdf",
            "mime_type": "application/pdf",
            "file_size": 50000,
        }
    }
    items = gw._extract_telegram_media(msg)
    assert len(items) == 1
    assert items[0]["file_id"] == "doc123"
    assert items[0]["filename"] == "report.pdf"
    assert items[0]["mime_type"] == "application/pdf"


def test_extract_telegram_media_text_only():
    import core.services.telegram_gateway as gw
    msg = {"text": "hello world"}
    assert gw._extract_telegram_media(msg) == []


# ---------------------------------------------------------------------------
# _build_telegram_attachment_prefix
# ---------------------------------------------------------------------------

def test_build_telegram_attachment_prefix_ok(monkeypatch):
    import core.services.telegram_gateway as gw
    monkeypatch.setattr(gw, "_resolve_telegram_file_url",
        lambda token, file_id: "https://api.telegram.org/file/botX/f.jpg")
    monkeypatch.setattr(gw, "_download_tg_attachment",
        lambda url, filename, mime, size, session_id: {"status": "ok", "attachment_id": "tg-abc"})
    items = [{"file_id": "F1", "filename": "pic.jpg", "mime_type": "image/jpeg", "file_size": 1000}]
    prefix = gw._build_telegram_attachment_prefix(items, token="tok", session_id="sess-t")
    assert "[Fil modtaget:" in prefix
    assert "tg-abc" in prefix
    assert "pic.jpg" in prefix


# ---------------------------------------------------------------------------
# send_telegram_file
# ---------------------------------------------------------------------------

def test_send_telegram_file_rejects_invalid_path(monkeypatch):
    import core.services.telegram_gateway as gw
    monkeypatch.setattr(gw, "_validate_send_path", lambda path: (False, "not-allowed"))
    result = gw.send_telegram_file(text="hi", file_path="/etc/passwd")
    assert result["status"] == "error"


def test_send_telegram_file_sends_photo(monkeypatch, tmp_path):
    import core.services.telegram_gateway as gw
    f = tmp_path / "pic.jpg"
    f.write_bytes(b"\xff\xd8\xff")
    monkeypatch.setattr(gw, "_validate_send_path", lambda path: (True, ""))
    sent = {}
    def fake_post(token, method, data, files):
        sent["method"] = method
        sent["files"] = list(files.keys())
        return {"ok": True, "result": {"message_id": 99}}
    monkeypatch.setattr(gw, "_api_post_file", fake_post)
    monkeypatch.setattr(gw, "_load_config", lambda: {"token": "T", "chat_id": "123"})
    result = gw.send_telegram_file(text="here", file_path=str(f))
    assert result["status"] == "sent"
    assert sent["method"] == "sendPhoto"
    assert "photo" in sent["files"]
