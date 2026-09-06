"""Task 5 (memory repair 2026-09-04): a correction keeps Bjørn's words and what Jarvis said."""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

from core.runtime import db_lessons as L


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "lessons.sqlite"

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(L, "connect", _connect)
    return path


def test_correction_listener_records_words(db):
    from core.services import experience_correction_listener as ecl

    rows = [
        {"role": "user", "content": "hvor ligger nøglen?"},
        {"role": "assistant", "content": "pfSense-nøglen ligger i .env"},
        {"role": "user", "content": "nej, den ligger i runtime.json"},
    ]
    with patch("core.services.chat_sessions.recent_chat_session_messages", return_value=rows), \
         patch.object(ecl, "_mark_recent_episode_corrected", return_value="ep-1"):
        assert ecl._looks_like_correction("nej, den ligger i runtime.json")
        ecl._record_correction_lesson("chat-1", "nej, den ligger i runtime.json")
    active = L.list_lessons(status="active")
    assert len(active) == 1
    assert "runtime.json" in active[0]["user_words"]
    assert ".env" in active[0]["jarvis_words"]
