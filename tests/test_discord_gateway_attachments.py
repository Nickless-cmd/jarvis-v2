# tests/test_discord_gateway_attachments.py
from __future__ import annotations
import pytest


def _make_fake_attachment(filename="photo.jpg", content_type="image/jpeg", size=1000,
                           url="https://cdn.discord.com/photo.jpg"):
    class FakeAttachment:
        pass
    a = FakeAttachment()
    a.filename = filename
    a.content_type = content_type
    a.size = size
    a.url = url
    return a


# ---------------------------------------------------------------------------
# _build_attachment_prefix
# ---------------------------------------------------------------------------

def test_build_attachment_prefix_ok(monkeypatch):
    import core.services.discord_gateway as gw
    monkeypatch.setattr(
        gw, "_download_attachment",
        lambda att, session_id: {"status": "ok", "attachment_id": "abc-123"},
    )
    att = _make_fake_attachment()
    prefix = gw._build_attachment_prefix([att], session_id="sess-1")
    assert "abc-123" in prefix
    assert "photo.jpg" in prefix
    assert "[Fil modtaget:" in prefix


def test_build_attachment_prefix_download_failure(monkeypatch):
    import core.services.discord_gateway as gw
    monkeypatch.setattr(
        gw, "_download_attachment",
        lambda att, session_id: {"status": "error", "reason": "download_failed"},
    )
    att = _make_fake_attachment()
    prefix = gw._build_attachment_prefix([att], session_id="sess-1")
    assert "[Fil kunne ikke hentes:" in prefix
    assert "photo.jpg" in prefix


def test_build_attachment_prefix_empty_list():
    import core.services.discord_gateway as gw
    assert gw._build_attachment_prefix([], session_id="sess-1") == ""


# ---------------------------------------------------------------------------
# send_discord_file
# ---------------------------------------------------------------------------

def test_send_discord_file_validates_path(monkeypatch):
    import core.services.discord_gateway as gw
    monkeypatch.setattr(gw, "_validate_send_path", lambda path: (False, "not-allowed"))
    result = gw.send_discord_file(channel_id=123, text="hi", file_path="/etc/passwd")
    assert result["status"] == "error"
    assert "not-allowed" in result["reason"]


def test_send_discord_file_queues_on_valid_path(monkeypatch, tmp_path):
    import core.services.discord_gateway as gw
    f = tmp_path / "file.jpg"
    f.write_bytes(b"data")
    monkeypatch.setattr(gw, "_validate_send_path", lambda path: (True, ""))
    queued = []
    monkeypatch.setattr(gw._outbound_queue, "put_nowait", lambda item: queued.append(item))
    result = gw.send_discord_file(channel_id=456, text="here", file_path=str(f))
    assert result["status"] == "queued"
    assert len(queued) == 1
    assert queued[0]["file_path"] == str(f)
    assert queued[0]["channel_id"] == 456
