"""Tests for notification_bridge.py — focus on the session_inbox gate.

2026-05-24 (Claude): send_session_notification now queues proactive
messages when the target session is active, unless urgent=True. Tests
pin the gating contract.
"""
import json
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    """Point both notification_bridge's deps and session_inbox at temp db."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    import core.services.session_inbox as inbox_mod
    monkeypatch.setattr(inbox_mod, "DB_PATH", path)
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


def _seed_active(db_path, session_id):
    when = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            ("channel.chat_message_appended",
             json.dumps({"session_id": session_id, "message": {"role": "user"}}),
             when),
        )
        conn.commit()


def _stub_chat_sessions(monkeypatch, session_id="s-test"):
    delivered = []

    def _append(session_id, role, content):
        delivered.append({"session_id": session_id, "role": role, "content": content})
        return {"id": "m-x", "session_id": session_id, "role": role, "content": content}

    def _get(_sid):
        return {"id": _sid}

    def _list(_limit=None):
        return [{"id": session_id}]

    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "append_chat_message", _append)
    monkeypatch.setattr(cs, "get_chat_session", _get)
    monkeypatch.setattr(cs, "list_chat_sessions", _list)

    # Make get_pinned_session_id return our test session
    import core.services.notification_bridge as nb
    monkeypatch.setattr(nb, "get_pinned_session_id", lambda: session_id)

    class _StubBus:
        def publish(self, *args, **kwargs):
            pass

    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod, "event_bus", _StubBus())
    return delivered


# ── Gate behavior ────────────────────────────────────────────────────────


def test_active_session_queues_non_urgent(tmp_db, monkeypatch):
    delivered = _stub_chat_sessions(monkeypatch, session_id="s-active")
    _seed_active(tmp_db, "s-active")

    from core.services.notification_bridge import send_session_notification
    result = send_session_notification("daemon ping", source="test-d")

    assert result["status"] == "queued"
    assert result["session_id"] == "s-active"
    assert "inbox_id" in result
    # Nothing delivered directly to chat
    assert delivered == []


def test_active_session_urgent_bypasses_queue(tmp_db, monkeypatch):
    delivered = _stub_chat_sessions(monkeypatch, session_id="s-active")
    _seed_active(tmp_db, "s-active")

    from core.services.notification_bridge import send_session_notification
    result = send_session_notification(
        "URGENT: disk full", source="critical", urgent=True,
    )

    assert result["status"] == "ok"
    assert len(delivered) == 1
    assert "URGENT" in delivered[0]["content"]


def test_inactive_session_delivers_directly(tmp_db, monkeypatch):
    """No recent activity → no queueing, immediate delivery."""
    delivered = _stub_chat_sessions(monkeypatch, session_id="s-quiet")
    # Don't seed any events — session is inactive

    from core.services.notification_bridge import send_session_notification
    result = send_session_notification("hello", source="proactive")

    assert result["status"] == "ok"
    assert len(delivered) == 1


def test_empty_content_rejected(tmp_db, monkeypatch):
    _stub_chat_sessions(monkeypatch)
    from core.services.notification_bridge import send_session_notification
    result = send_session_notification("   ", source="d")
    assert result["status"] == "error"


def test_no_session_returns_blocked(tmp_db, monkeypatch):
    """When there's no pinned and no sessions, return blocked status."""
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "get_chat_session", lambda _sid: None)
    monkeypatch.setattr(cs, "list_chat_sessions", lambda *a, **kw: [])
    import core.services.notification_bridge as nb
    monkeypatch.setattr(nb, "get_pinned_session_id", lambda: "")

    from core.services.notification_bridge import send_session_notification
    result = send_session_notification("hi", source="d")
    assert result["status"] == "blocked"
