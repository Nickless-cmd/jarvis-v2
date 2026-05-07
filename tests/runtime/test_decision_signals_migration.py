"""Verify trigger_name column gets added and known decisions get wired."""
import sqlite3

from core.runtime.db import _ensure_decision_trigger_column


def _setup_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS behavioral_decisions (
          decision_id TEXT PRIMARY KEY,
          directive TEXT, rationale TEXT, trigger_cue TEXT,
          status TEXT, priority INTEGER,
          created_at TEXT, updated_at TEXT, last_reviewed_at TEXT,
          adherence_score REAL,
          source_record_id TEXT, source_type TEXT, created_by TEXT
        )
    """)
    conn.execute(
        "INSERT INTO behavioral_decisions(decision_id, directive, status) VALUES "
        "('dec_d56d89ceec24', 'loop nudge directive', 'active'), "
        "('dec_56d4dbb03e22', 'backend directive', 'active'), "
        "('dec_2ac499e2de29', 'memorable info directive', 'active'), "
        "('dec_other', 'unrelated directive', 'active')"
    )


def test_migration_adds_trigger_name_column():
    conn = sqlite3.connect(":memory:")
    _setup_tables(conn)
    _ensure_decision_trigger_column(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(behavioral_decisions)").fetchall()]
    assert "trigger_name" in cols


def test_migration_updates_known_decisions():
    conn = sqlite3.connect(":memory:")
    _setup_tables(conn)
    _ensure_decision_trigger_column(conn)
    triggers = dict(conn.execute(
        "SELECT decision_id, trigger_name FROM behavioral_decisions"
    ).fetchall())
    assert triggers["dec_d56d89ceec24"] == "loop_nudge_5_rounds"
    assert triggers["dec_56d4dbb03e22"] == "backend_unresolved_3_calls"
    assert triggers["dec_2ac499e2de29"] is None  # passive in v1
    assert triggers["dec_other"] is None  # unrelated, untouched


def test_migration_idempotent():
    conn = sqlite3.connect(":memory:")
    _setup_tables(conn)
    _ensure_decision_trigger_column(conn)
    _ensure_decision_trigger_column(conn)  # second run must not raise
    cols = [r[1] for r in conn.execute("PRAGMA table_info(behavioral_decisions)").fetchall()]
    assert cols.count("trigger_name") == 1
