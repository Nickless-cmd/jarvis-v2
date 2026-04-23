# tests/test_tools_attachments.py
from __future__ import annotations
import pytest


# ---------------------------------------------------------------------------
# read_attachment tool
# ---------------------------------------------------------------------------

def test_read_attachment_calls_service(monkeypatch):
    import core.tools.simple_tools as st
    monkeypatch.setattr(
        "core.services.attachment_service.read_attachment_content",
        lambda aid: {"status": "ok", "type": "text", "content": "hello", "filename": "f.txt"},
    )
    result = st._exec_read_attachment({"attachment_id": "abc-123"})
    assert result["status"] == "ok"
    assert "hello" in result["text"]


def test_read_attachment_missing_id():
    import core.tools.simple_tools as st
    result = st._exec_read_attachment({})
    assert result["status"] == "error"


def test_read_attachment_not_found(monkeypatch):
    import core.tools.simple_tools as st
    monkeypatch.setattr(
        "core.services.attachment_service.read_attachment_content",
        lambda aid: {"status": "error", "reason": "not-found"},
    )
    result = st._exec_read_attachment({"attachment_id": "bad-id"})
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# list_attachments tool
# ---------------------------------------------------------------------------

def test_list_attachments_returns_items(monkeypatch):
    import core.tools.simple_tools as st
    monkeypatch.setattr(
        "core.services.attachment_service.list_attachments",
        lambda session_id, limit: [{"attachment_id": "x1", "filename": "pic.jpg"}],
    )
    result = st._exec_list_attachments({"session_id": "sess-1"})
    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["attachments"][0]["attachment_id"] == "x1"


def test_list_attachments_empty(monkeypatch):
    import core.tools.simple_tools as st
    monkeypatch.setattr(
        "core.services.attachment_service.list_attachments",
        lambda session_id, limit: [],
    )
    result = st._exec_list_attachments({"session_id": "sess-empty"})
    assert result["status"] == "ok"
    assert result["count"] == 0


# ---------------------------------------------------------------------------
# send_telegram_message with file_path
# ---------------------------------------------------------------------------

def test_send_telegram_message_with_file(monkeypatch):
    import core.tools.simple_tools as st
    sent = {}
    monkeypatch.setattr(
        "core.services.telegram_gateway.send_telegram_file",
        lambda text, file_path: {"status": "sent", "method": "sendPhoto", "message_id": 1},
    )
    result = st._exec_send_telegram_message(
        {"content": "her er filen", "file_path": "/home/bs/.jarvis-v2/uploads/x/pic.jpg"}
    )
    assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# discord_channel send with file_path — queue accepts dict with file_path
# ---------------------------------------------------------------------------

def test_discord_channel_send_file_queued(monkeypatch, tmp_path):
    import core.services.discord_gateway as gw
    f = tmp_path / "img.png"
    f.write_bytes(b"data")
    monkeypatch.setattr(gw, "_validate_send_path", lambda path: (True, ""))
    queued = []
    monkeypatch.setattr(gw._outbound_queue, "put_nowait", lambda item: queued.append(item))
    result = gw.send_discord_file(channel_id=123, text="check this", file_path=str(f))
    assert result["status"] == "queued"
    assert queued[0]["file_path"] == str(f)
