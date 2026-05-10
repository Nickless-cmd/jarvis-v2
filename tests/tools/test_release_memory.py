"""Tests for the release_memory tool."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """Same fresh-db pattern as test_forgetting_engine.py."""
    db_path = tmp_path / "jarvis.db"
    from core.runtime import db as db_mod

    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()
    with db_mod.connect() as conn:
        db_mod._ensure_cognitive_chronicle_entries_table(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_personal_project_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                entry_text TEXT NOT NULL,
                source TEXT,
                mood_tone TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        db_mod._ensure_soft_deleted_at_columns(conn)
    return db_path


def test_release_memory_tool_happy_path(fresh_db):
    from core.runtime.db import connect
    from core.tools.forgetting_tools import _exec_release_memory

    with connect() as conn:
        old = (datetime.now(UTC) - timedelta(days=92)).isoformat().replace("+00:00", "Z")
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries "
            "(entry_id, period, narrative, created_at, updated_at) "
            "VALUES ('e1', 'day-old', 'private', ?, ?)",
            (old, old),
        )

    result = _exec_release_memory({
        "memory_kind": "chronicle_entry",
        "memory_id": "e1",
        "why": "test reason — should not be persisted",
    })
    assert result["status"] == "released", result
    assert "måneder siden" in result["period_label"]


def test_release_memory_rejects_unknown_kind(fresh_db):
    from core.tools.forgetting_tools import _exec_release_memory
    result = _exec_release_memory({
        "memory_kind": "soul",
        "memory_id": "x",
    })
    assert result["status"] == "rejected"


def test_release_memory_returns_disabled_when_killswitched(fresh_db, monkeypatch):
    from core.tools.forgetting_tools import _exec_release_memory

    class _FakeSettings:
        forgetting_enabled = False

    monkeypatch.setattr(
        "core.services.forgetting_engine.load_settings",
        lambda: _FakeSettings(),
    )
    result = _exec_release_memory({
        "memory_kind": "chronicle_entry",
        "memory_id": "anything",
    })
    assert result["status"] == "disabled"


def test_release_memory_validates_required_args(fresh_db):
    from core.tools.forgetting_tools import _exec_release_memory
    result = _exec_release_memory({"memory_kind": "chronicle_entry"})
    assert result["status"] == "rejected"
    assert "required" in result["reason"]
