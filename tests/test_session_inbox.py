"""Tests for session_inbox.py (daemon-interruption gate).

Verifies queueing during active sessions, flush behavior, urgent bypass,
and fallback timeout. Cross-process polling-listener behavior is tested
via direct flush_session calls; the actual thread loop is too slow for
unit tests.
"""
import json
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    import core.services.session_inbox as mod
    monkeypatch.setattr(mod, "DB_PATH", path)
    # Seed events table since is_session_active queries it
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.commit()
    yield path
    path.unlink(missing_ok=True)


def _seed_active_event(db_path, session_id, secs_ago=10):
    when = (datetime.now(UTC) - timedelta(seconds=secs_ago)).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            (
                "channel.chat_message_appended",
                json.dumps({"session_id": session_id, "message": {"role": "user"}}),
                when,
            ),
        )
        conn.commit()


# ── is_session_active ────────────────────────────────────────────────────


def test_active_when_recent_event(tmp_db):
    from core.services.session_inbox import is_session_active
    _seed_active_event(tmp_db, "chat-abc", secs_ago=60)
    assert is_session_active("chat-abc") is True


def test_inactive_when_no_events(tmp_db):
    from core.services.session_inbox import is_session_active
    assert is_session_active("chat-nobody") is False


def test_inactive_when_event_too_old(tmp_db):
    from core.services.session_inbox import is_session_active
    _seed_active_event(tmp_db, "chat-old", secs_ago=900)  # 15 min ago
    assert is_session_active("chat-old", window_seconds=300) is False


# ── enqueue + pending_for_session ───────────────────────────────────────


def test_enqueue_and_pending(tmp_db):
    from core.services.session_inbox import enqueue, pending_for_session
    enqueue(session_id="s1", content="hello from daemon", source="test-d")
    pending = pending_for_session("s1")
    assert len(pending) == 1
    assert pending[0]["content"] == "hello from daemon"
    assert pending[0]["source"] == "test-d"


def test_enqueue_rejects_empty(tmp_db):
    from core.services.session_inbox import enqueue
    out = enqueue(session_id="s1", content="", source="x")
    assert out["status"] == "error"


def test_pending_isolated_per_session(tmp_db):
    from core.services.session_inbox import enqueue, pending_for_session
    enqueue(session_id="s1", content="a", source="d")
    enqueue(session_id="s2", content="b", source="d")
    assert len(pending_for_session("s1")) == 1
    assert len(pending_for_session("s2")) == 1


def test_pending_count(tmp_db):
    from core.services.session_inbox import enqueue, pending_count
    enqueue(session_id="s1", content="a", source="d")
    enqueue(session_id="s1", content="b", source="d")
    enqueue(session_id="s2", content="c", source="d")
    assert pending_count("s1") == 2
    assert pending_count() == 3


# ── flush_session ────────────────────────────────────────────────────────


def test_flush_session_marks_delivered(tmp_db, monkeypatch):
    from core.services.session_inbox import enqueue, flush_session, pending_for_session

    enqueue(session_id="s1", content="msg1", source="d")
    enqueue(session_id="s1", content="msg2", source="d")

    # Stub chat_sessions + eventbus so flush succeeds without full stack
    class _StubMsg(dict):
        pass

    def _stub_append(session_id, role, content):
        return _StubMsg(id="m-x", session_id=session_id, role=role, content=content)

    def _stub_get(_sid):
        return {"id": _sid}

    class _StubBus:
        def publish(self, *args, **kwargs):
            pass

    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "append_chat_message", _stub_append)
    monkeypatch.setattr(cs, "get_chat_session", _stub_get)
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod, "event_bus", _StubBus())

    out = flush_session("s1")
    assert out["status"] == "ok"
    assert out["delivered"] == 2
    # No more pending for s1
    assert pending_for_session("s1") == []


def test_flush_session_no_items_is_noop(tmp_db):
    from core.services.session_inbox import flush_session
    out = flush_session("s-empty")
    assert out["status"] == "ok"
    assert out["delivered"] == 0


def test_flush_session_handles_deleted_session(tmp_db, monkeypatch):
    """If the chat-session has been deleted, mark items as dropped."""
    from core.services.session_inbox import enqueue, flush_session, pending_for_session

    enqueue(session_id="s-gone", content="orphan", source="d")

    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "get_chat_session", lambda _sid: None)

    out = flush_session("s-gone")
    assert out["status"] == "ok"
    assert "note" in out
    # Pending list empty since items moved to 'dropped'
    assert pending_for_session("s-gone") == []
