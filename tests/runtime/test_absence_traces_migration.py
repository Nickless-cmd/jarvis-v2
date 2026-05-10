"""Schema migrations for forgetting (Lag 11 Phase 1)."""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime.db import (
    _ensure_absence_traces_table,
    _ensure_soft_deleted_at_columns,
)


def _bare_chronicle_entries(conn: sqlite3.Connection) -> None:
    """Create a minimal cognitive_chronicle_entries table for migration testing."""
    conn.execute(
        """
        CREATE TABLE cognitive_chronicle_entries (
            entry_id TEXT NOT NULL,
            workspace_id TEXT,
            kind TEXT,
            body TEXT,
            created_at TEXT
        )
        """
    )


def _bare_journal(conn: sqlite3.Connection) -> None:
    """Create a minimal cognitive_personal_project_journal for testing."""
    conn.execute(
        """
        CREATE TABLE cognitive_personal_project_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            entry_text TEXT NOT NULL,
            created_at TEXT
        )
        """
    )


def test_absence_traces_table_created() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_absence_traces_table(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='absence_traces'"
    ).fetchone()
    assert row is not None


def test_absence_traces_has_expected_columns() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_absence_traces_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(absence_traces)").fetchall()}
    expected = {
        "trace_id", "track_kind", "workspace_id",
        "month_key", "auto_count",
        "released_at", "period_label", "is_self_released",
        "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_absence_traces_unique_constraint() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_absence_traces_table(conn)
    conn.execute(
        "INSERT INTO absence_traces (trace_id, track_kind, workspace_id, "
        "month_key, auto_count, created_at, updated_at) VALUES "
        "('a', 'auto_counter', 'default', '2026-05', 1, 'now', 'now')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO absence_traces (trace_id, track_kind, workspace_id, "
            "month_key, auto_count, created_at, updated_at) VALUES "
            "('b', 'auto_counter', 'default', '2026-05', 1, 'now', 'now')"
        )


def test_absence_traces_table_creation_is_idempotent() -> None:
    """Re-running _ensure_absence_traces_table is a no-op."""
    conn = sqlite3.connect(":memory:")
    _ensure_absence_traces_table(conn)
    _ensure_absence_traces_table(conn)  # must not raise
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='absence_traces'"
    ).fetchone()
    assert row is not None


def test_soft_deleted_at_added_to_chronicle_entries() -> None:
    conn = sqlite3.connect(":memory:")
    _bare_chronicle_entries(conn)
    _ensure_soft_deleted_at_columns(conn)
    cols = [r[1] for r in conn.execute(
        "PRAGMA table_info(cognitive_chronicle_entries)"
    ).fetchall()]
    assert "soft_deleted_at" in cols


def test_soft_deleted_at_added_to_journal() -> None:
    conn = sqlite3.connect(":memory:")
    _bare_journal(conn)
    _ensure_soft_deleted_at_columns(conn)
    cols = [r[1] for r in conn.execute(
        "PRAGMA table_info(cognitive_personal_project_journal)"
    ).fetchall()]
    assert "soft_deleted_at" in cols


def test_soft_deleted_at_migration_is_idempotent() -> None:
    """Re-running _ensure_soft_deleted_at_columns is a no-op (no duplicate-column errors)."""
    conn = sqlite3.connect(":memory:")
    _bare_chronicle_entries(conn)
    _bare_journal(conn)
    _ensure_soft_deleted_at_columns(conn)
    _ensure_soft_deleted_at_columns(conn)  # must not raise
    cols = [r[1] for r in conn.execute(
        "PRAGMA table_info(cognitive_chronicle_entries)"
    ).fetchall()]
    assert cols.count("soft_deleted_at") == 1


def test_soft_deleted_at_skips_missing_table() -> None:
    """If a target table doesn't exist yet, the migration must NOT raise.

    Defense in depth: caller may run this on a partially-initialized DB
    (test fixtures, recovery) where the target tables haven't been created.
    """
    conn = sqlite3.connect(":memory:")
    # Don't create the tables — they're absent
    _ensure_soft_deleted_at_columns(conn)  # must not raise
