# tests/test_channel_attachments_db.py
from __future__ import annotations
import pytest


def _get_db():
    from core.runtime.db import connect, _ensure_channel_attachments_table
    conn = connect()
    _ensure_channel_attachments_table(conn)
    return conn


def test_store_and_get_attachment():
    from core.runtime.db import store_channel_attachment, get_channel_attachment
    conn = _get_db()
    store_channel_attachment(
        conn=conn,
        attachment_id="abc-123",
        session_id="sess-1",
        channel_type="discord",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=12345,
        local_path="/tmp/photo.jpg",
        source_url="https://cdn.discord.com/photo.jpg",
    )
    conn.commit()
    row = get_channel_attachment(conn=conn, attachment_id="abc-123")
    assert row is not None
    assert row["filename"] == "photo.jpg"
    assert row["channel_type"] == "discord"
    assert row["size_bytes"] == 12345


def test_get_unknown_returns_none():
    from core.runtime.db import get_channel_attachment
    conn = _get_db()
    assert get_channel_attachment(conn=conn, attachment_id="does-not-exist") is None


def test_list_channel_attachments_scoped_to_session():
    from core.runtime.db import store_channel_attachment, list_channel_attachments
    conn = _get_db()
    store_channel_attachment(
        conn=conn, attachment_id="s1-a-unique", session_id="sess-AA", channel_type="discord",
        filename="a.jpg", mime_type="image/jpeg", size_bytes=100,
        local_path="/tmp/a.jpg", source_url="",
    )
    store_channel_attachment(
        conn=conn, attachment_id="s2-b-unique", session_id="sess-BB", channel_type="telegram",
        filename="b.pdf", mime_type="application/pdf", size_bytes=200,
        local_path="/tmp/b.pdf", source_url="",
    )
    conn.commit()
    rows_a = list_channel_attachments(conn=conn, session_id="sess-AA")
    assert all(r["session_id"] == "sess-AA" for r in rows_a)
    ids_a = [r["attachment_id"] for r in rows_a]
    assert "s1-a-unique" in ids_a
    assert "s2-b-unique" not in ids_a
