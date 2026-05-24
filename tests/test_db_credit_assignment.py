"""Tests for db_credit_assignment — Lag 1 credit assignment module."""

import sqlite3

from core.runtime.db_credit_assignment import _migrate_table, ensure_credit_assignment_tables


def test_migrate_table_noop_on_missing_table():
    """_migrate_table should not raise when table doesn't exist yet."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Table does not exist — should be silent no-op
    _migrate_table(conn, "nonexistent_table", [("col_a", "TEXT")])
    conn.close()


def test_migrate_table_adds_columns_to_existing_table():
    """_migrate_table should add missing columns to an existing table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE test_t (id INTEGER PRIMARY KEY)")
    conn.commit()

    _migrate_table(conn, "test_t", [("new_col", "TEXT NOT NULL DEFAULT 'x'")])

    # Verify column was added
    cols = {row[1] for row in conn.execute("PRAGMA table_info(test_t)")}
    assert "new_col" in cols
    conn.close()


def test_migrate_table_idempotent():
    """_migrate_table should not fail when column already exists."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE test_t (id INTEGER PRIMARY KEY, existing TEXT)")
    conn.commit()

    # First call adds nothing (column exists)
    _migrate_table(conn, "test_t", [("existing", "TEXT")])
    # Second call should also be fine
    _migrate_table(conn, "test_t", [("existing", "TEXT")])
    conn.close()


def test_ensure_credit_assignment_tables_noop_on_empty_db():
    """ensure_credit_assignment_tables should not raise on a fresh DB with no tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Fresh DB — no cognitive_decisions table exists yet
    ensure_credit_assignment_tables(conn)
    conn.close()


def test_ensure_credit_assignment_tables_with_existing_table():
    """ensure_credit_assignment_tables should add columns when table exists."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Create the table as init_db would (simplified)
    conn.execute(
        """CREATE TABLE cognitive_decisions (
            decision_id TEXT PRIMARY KEY,
            title TEXT, context TEXT, options TEXT, decision TEXT,
            why TEXT, regrets TEXT, refs TEXT, created_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE runtime_self_review_outcomes (
            outcome_id TEXT PRIMARY KEY,
            outcome_type TEXT, canonical_key TEXT, status TEXT,
            title TEXT, summary TEXT, rationale TEXT,
            source_kind TEXT, confidence TEXT, evidence_summary TEXT,
            support_summary TEXT, status_reason TEXT,
            review_run_id TEXT, session_id TEXT,
            support_count INTEGER, session_count INTEGER, merge_count INTEGER,
            created_at TEXT, updated_at TEXT
        )"""
    )
    conn.commit()

    ensure_credit_assignment_tables(conn)

    # Verify columns were added
    cd_cols = {row[1] for row in conn.execute("PRAGMA table_info(cognitive_decisions)")}
    assert "kind" in cd_cols
    assert "outcome_aggregate" in cd_cols

    rsro_cols = {row[1] for row in conn.execute("PRAGMA table_info(runtime_self_review_outcomes)")}
    assert "decision_id" in rsro_cols
    assert "credit_score" in rsro_cols

    conn.close()
