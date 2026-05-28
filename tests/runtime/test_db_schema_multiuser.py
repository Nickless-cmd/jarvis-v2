"""Tests that DB schema includes multi-user attribution columns.

After Task 2, these columns exist on all listed tables. Each defaults to
NULL so existing rows are still valid and unfiltered queries see them all.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime.db import (
    _ensure_scheduled_tasks_table,
    _ensure_runtime_initiatives_table,
    _ensure_cognitive_chronicle_entries_table,
    _ensure_runtime_dream_hypothesis_signal_table,
    _ensure_runtime_dream_adoption_candidate_table,
    _ensure_runtime_dream_influence_proposal_table,
    _ensure_multiuser_columns,
)
from core.runtime.db_capability_approval import (
    _ensure_capability_approval_request_columns,
)
from core.services.dream_hypothesis_generator import _ensure_table as _ensure_dream_hypotheses_table


def _bare_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _cols(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


# ---------------------------------------------------------------------------
# Scheduling tables — need scheduled_for_user_id + initiated_by
# ---------------------------------------------------------------------------

def test_scheduled_tasks_has_user_id_columns() -> None:
    conn = _bare_conn()
    _ensure_scheduled_tasks_table(conn)
    cols = _cols(conn, "scheduled_tasks")
    assert "scheduled_for_user_id" in cols, "scheduled_tasks missing scheduled_for_user_id"
    assert "initiated_by" in cols, "scheduled_tasks missing initiated_by"


def test_runtime_initiatives_has_user_id_columns() -> None:
    conn = _bare_conn()
    _ensure_runtime_initiatives_table(conn)
    cols = _cols(conn, "runtime_initiatives")
    assert "scheduled_for_user_id" in cols, "runtime_initiatives missing scheduled_for_user_id"
    assert "initiated_by" in cols, "runtime_initiatives missing initiated_by"


def test_capability_approval_requests_has_user_id_columns() -> None:
    conn = _bare_conn()
    # capability_approval_requests is initialised via init_db() block in db.py;
    # the additive migration function is exported from db_capability_approval.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS capability_approval_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL UNIQUE,
            capability_id TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            status TEXT NOT NULL,
            executed INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    _ensure_capability_approval_request_columns(conn)
    _ensure_multiuser_columns(conn)
    cols = _cols(conn, "capability_approval_requests")
    assert "scheduled_for_user_id" in cols, "capability_approval_requests missing scheduled_for_user_id"
    assert "initiated_by" in cols, "capability_approval_requests missing initiated_by"


def test_tool_intent_approval_requests_has_user_id_columns() -> None:
    conn = _bare_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_intent_approval_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            approval_id TEXT NOT NULL UNIQUE,
            intent_key TEXT NOT NULL UNIQUE,
            intent_type TEXT NOT NULL,
            intent_target TEXT NOT NULL,
            approval_scope TEXT NOT NULL,
            approval_required INTEGER NOT NULL DEFAULT 1,
            approval_state TEXT NOT NULL,
            approval_source TEXT NOT NULL DEFAULT 'none',
            approval_reason TEXT NOT NULL DEFAULT '',
            requested_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            execution_state TEXT NOT NULL DEFAULT 'not-executed'
        )
        """
    )
    _ensure_multiuser_columns(conn)
    cols = _cols(conn, "tool_intent_approval_requests")
    assert "scheduled_for_user_id" in cols, "tool_intent_approval_requests missing scheduled_for_user_id"
    assert "initiated_by" in cols, "tool_intent_approval_requests missing initiated_by"


# ---------------------------------------------------------------------------
# Relevance tables — need relevant_to_users
# ---------------------------------------------------------------------------

def test_cognitive_chronicle_entries_has_relevant_to_users() -> None:
    conn = _bare_conn()
    _ensure_cognitive_chronicle_entries_table(conn)
    cols = _cols(conn, "cognitive_chronicle_entries")
    assert "relevant_to_users" in cols, "cognitive_chronicle_entries missing relevant_to_users"


def test_cognitive_dream_hypotheses_has_relevant_to_users() -> None:
    conn = _bare_conn()
    _ensure_dream_hypotheses_table.__func__(conn) if hasattr(_ensure_dream_hypotheses_table, "__func__") else None
    # _ensure_table in dream_hypothesis_generator uses its own connect();
    # we test the column is present after calling it via the module-level helper.
    # Use an in-process memory DB approach: create table manually + run migration.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_dream_hypotheses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hypothesis TEXT NOT NULL,
            connection TEXT NOT NULL DEFAULT '',
            action_suggestion TEXT NOT NULL DEFAULT '',
            source_signals TEXT NOT NULL DEFAULT '[]',
            basis_fingerprint TEXT NOT NULL DEFAULT '',
            hypothesis_fingerprint TEXT NOT NULL DEFAULT '',
            confidence REAL NOT NULL DEFAULT 0.35,
            presented INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_multiuser_columns(conn)
    cols = _cols(conn, "cognitive_dream_hypotheses")
    assert "relevant_to_users" in cols, "cognitive_dream_hypotheses missing relevant_to_users"


def test_runtime_dream_hypothesis_signals_has_relevant_to_users() -> None:
    conn = _bare_conn()
    _ensure_runtime_dream_hypothesis_signal_table(conn)
    cols = _cols(conn, "runtime_dream_hypothesis_signals")
    assert "relevant_to_users" in cols, "runtime_dream_hypothesis_signals missing relevant_to_users"


def test_runtime_dream_adoption_candidates_has_relevant_to_users() -> None:
    conn = _bare_conn()
    _ensure_runtime_dream_adoption_candidate_table(conn)
    cols = _cols(conn, "runtime_dream_adoption_candidates")
    assert "relevant_to_users" in cols, "runtime_dream_adoption_candidates missing relevant_to_users"


def test_runtime_dream_influence_proposals_has_relevant_to_users() -> None:
    conn = _bare_conn()
    _ensure_runtime_dream_influence_proposal_table(conn)
    cols = _cols(conn, "runtime_dream_influence_proposals")
    assert "relevant_to_users" in cols, "runtime_dream_influence_proposals missing relevant_to_users"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def test_ensure_multiuser_columns_is_idempotent() -> None:
    """Running _ensure_multiuser_columns twice must not raise."""
    conn = _bare_conn()
    _ensure_scheduled_tasks_table(conn)
    _ensure_multiuser_columns(conn)
    _ensure_multiuser_columns(conn)  # must not raise
    cols = _cols(conn, "scheduled_tasks")
    assert cols.count("scheduled_for_user_id") == 1


# ---------------------------------------------------------------------------
# Null defaults
# ---------------------------------------------------------------------------

def test_existing_rows_have_null_defaults() -> None:
    """Insert a row in the bare-minimum schema — new columns default to NULL."""
    conn = _bare_conn()
    _ensure_scheduled_tasks_table(conn)
    conn.execute(
        "INSERT INTO scheduled_tasks (task_id, focus, source, status, run_at, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("test-1", "test focus", "test", "pending", "2026-01-01", "2026-01-01", "2026-01-01"),
    )
    row = conn.execute(
        "SELECT scheduled_for_user_id, initiated_by FROM scheduled_tasks WHERE task_id=?",
        ("test-1",),
    ).fetchone()
    assert row[0] is None
    assert row[1] is None
