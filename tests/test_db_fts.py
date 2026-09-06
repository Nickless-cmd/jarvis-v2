"""Task 4 (memory repair 2026-09-04): FTS5 over session summaries + chat messages."""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime import db_fts


def _mem_db() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.execute(
        "CREATE TABLE session_summaries (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, "
        "run_id TEXT NOT NULL DEFAULT '', summary TEXT NOT NULL, key_topics TEXT NOT NULL DEFAULT '', "
        "decisions_made TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL)"
    )
    c.execute(
        "CREATE TABLE chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, message_id TEXT NOT NULL UNIQUE, "
        "session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, user_id TEXT NOT NULL DEFAULT '', "
        "workspace_name TEXT NOT NULL DEFAULT '', reasoning_content TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL)"
    )
    return c


@pytest.fixture
def conn(monkeypatch):
    c = _mem_db()

    class _Ctx:
        def __enter__(self):
            return c

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(db_fts, "connect", lambda: _Ctx())
    return c


def test_to_match_query_prefix_or():
    assert db_fts.to_match_query("pfsense nøgle .env") == '"pfsense"* OR "nøgle"* OR "env"*'
    assert db_fts.to_match_query("?") == ""


def test_ensure_creates_tables_and_backfills_existing_rows(conn):
    conn.execute(
        "INSERT INTO session_summaries (session_id, summary, created_at) VALUES ('s1', "
        "'Emne: pfsense api-nøgle flyttet til .env. Resultat: python-dotenv tilføjet.', '2026-09-03T10:00:00')"
    )
    ready = db_fts.ensure_fts_tables(conn)
    assert "session_summaries_fts" in ready and "chat_messages_fts" in ready
    hits = db_fts.search_session_summaries("pfsense nøgle")
    assert hits and hits[0]["session_id"] == "s1"
    assert 0 < hits[0]["score"] <= 1


def test_triggers_keep_fts_in_sync(conn):
    db_fts.ensure_fts_tables(conn)
    conn.execute(
        "INSERT INTO chat_messages (message_id, session_id, role, content, created_at) VALUES "
        "('m1', 'chat-1', 'assistant', 'Vi besluttede at flytte pfsense-nøglen til .env i går.', '2026-09-03T10:00:00')"
    )
    conn.execute(
        "INSERT INTO chat_messages (message_id, session_id, role, content, created_at) VALUES "
        "('m2', 'chat-2', 'user', 'hvad med vejret i Svendborg?', '2026-09-03T10:01:00')"
    )
    hits = db_fts.search_chat_messages("pfsense nøgle")
    assert [h["message_id"] for h in hits] == ["m1"]
    hits = db_fts.search_chat_messages("pfsense", session_id="chat-2")
    assert hits == []
    conn.execute("UPDATE chat_messages SET content = 'helt andet indhold' WHERE message_id = 'm1'")
    assert db_fts.search_chat_messages("pfsense") == []
    conn.execute("DELETE FROM chat_messages WHERE message_id = 'm2'")
    assert db_fts.search_chat_messages("vejret") == []


def test_ensure_is_idempotent(conn):
    a = db_fts.ensure_fts_tables(conn)
    b = db_fts.ensure_fts_tables(conn)
    assert a == b
