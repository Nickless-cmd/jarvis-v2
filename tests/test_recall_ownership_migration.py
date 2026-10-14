from __future__ import annotations

import sqlite3

import pytest

from core.services import recall_ownership_migration as migration


@pytest.fixture
def migration_db(monkeypatch, tmp_path):
    db_path = tmp_path / "recall.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE cognitive_experiential_memories (
            memory_id TEXT PRIMARY KEY, session_id TEXT, run_id TEXT, user_id TEXT
        );
        CREATE TABLE reasoning_conclusions (
            conclusion_id TEXT PRIMARY KEY, user_id TEXT
        );
        CREATE TABLE chat_messages (
            id INTEGER PRIMARY KEY, message_id TEXT, session_id TEXT,
            role TEXT, content TEXT, user_id TEXT DEFAULT '', created_at TEXT
        );
    """)
    monkeypatch.setenv("JARVISX_ENCRYPTION_KEK", "11" * 32)
    monkeypatch.setattr(migration, "_report_dir", lambda: tmp_path / "reports")
    monkeypatch.setattr("core.runtime.db_core.connect", lambda: sqlite3.connect(db_path))
    yield conn, db_path
    conn.close()


def test_explicit_or_unique_other_user_beats_owner_fallback(migration_db):
    conn, _ = migration_db
    conn.execute("INSERT INTO chat_messages VALUES (1,'m1','s1','user','x','member-1','now')")
    conn.execute("INSERT INTO cognitive_experiential_memories VALUES ('e1','s1','',NULL)")
    conn.commit()

    report = migration.classify_recall_ownership(conn, owner_user_id="owner")

    assert report.destination_for("experience", "e1") == "member-1"


def test_unmatched_legacy_row_uses_owner_fallback(migration_db):
    conn, _ = migration_db
    conn.execute("INSERT INTO reasoning_conclusions VALUES ('r1',NULL)")
    conn.commit()

    report = migration.classify_recall_ownership(conn, owner_user_id="owner")

    assert report.destination_for("reasoning", "r1") == "owner"


def test_conflicting_users_are_quarantined(migration_db):
    conn, _ = migration_db
    conn.execute("INSERT INTO chat_messages VALUES (1,'m1','s2','user','x','member-1','now')")
    conn.execute("INSERT INTO chat_messages VALUES (2,'m2','s2','user','x','member-2','now')")
    conn.execute("INSERT INTO cognitive_experiential_memories VALUES ('e2','s2','',NULL)")
    conn.commit()

    report = migration.classify_recall_ownership(conn, owner_user_id="owner")

    assert report.reason_for("experience", "e2") == "identity_conflict"


def test_unstamped_chat_rows_inherit_unique_user_or_owner(migration_db):
    conn, _ = migration_db
    conn.execute("INSERT INTO chat_messages VALUES (1,'m1','s1','user','x','member-1','now')")
    conn.execute("INSERT INTO chat_messages VALUES (2,'m2','s1','assistant','x','','now')")
    conn.execute("INSERT INTO chat_messages VALUES (3,'m3','legacy','assistant','x','','now')")
    conn.commit()

    report = migration.classify_recall_ownership(conn, owner_user_id="owner")

    assert report.destination_for("chat_session", "s1") == "member-1"
    assert report.destination_for("chat_session", "legacy") == "owner"


def test_apply_requires_gate_and_apply_rollback_are_idempotent(migration_db, monkeypatch):
    conn, db_path = migration_db
    conn.execute("INSERT INTO reasoning_conclusions VALUES ('r1',NULL)")
    conn.commit()
    report = migration.classify_recall_ownership(conn, owner_user_id="owner")

    monkeypatch.setattr(migration.scoped_recall_policy, "recall_migration_enabled", lambda: False)
    with pytest.raises(migration.MigrationDisabled):
        migration.apply_report(report.report_id)

    state = {"enabled": True}
    monkeypatch.setattr(migration.scoped_recall_policy, "recall_migration_enabled", lambda: state["enabled"])
    monkeypatch.setattr(
        migration.scoped_recall_policy, "set_recall_migration_enabled",
        lambda value: state.__setitem__("enabled", value),
    )
    first = migration.apply_report(report.report_id)
    assert first.updated == 1 and state["enabled"] is False

    state["enabled"] = True
    second = migration.apply_report(report.report_id)
    assert second.already_applied == 1

    state["enabled"] = True
    rolled = migration.rollback_report(report.report_id)
    assert rolled.restored == 1 and state["enabled"] is False
    check = sqlite3.connect(db_path).execute(
        "SELECT user_id FROM reasoning_conclusions WHERE conclusion_id='r1'"
    ).fetchone()[0]
    assert check is None


def test_report_file_contains_no_raw_ids_or_user_ids(migration_db):
    conn, _ = migration_db
    conn.execute("INSERT INTO reasoning_conclusions VALUES ('private-record-id',NULL)")
    conn.commit()

    report = migration.classify_recall_ownership(conn, owner_user_id="owner-secret-id")
    raw = migration.report_path(report.report_id).read_text(encoding="utf-8")

    assert "private-record-id" not in raw
    assert "owner-secret-id" not in raw
