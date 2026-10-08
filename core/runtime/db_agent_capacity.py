"""Atomic admission limits for contract agent assignments.

The queue is a durable reservation, distinct from an active worker slot.  This
module is deliberately called with the connection that already owns the
``BEGIN IMMEDIATE`` transaction in ``accept_assignment``.  Opening a second
connection here would roll back the caller's transaction in this runtime.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import _now_iso


MAX_QUEUED_GLOBAL = 24
MAX_QUEUED_PER_PARENT = 8
MAX_ACTIVE_GLOBAL = 12
MAX_ACTIVE_PER_OWNER = 8
MAX_ACTIVE_PER_PARENT = 6


def ensure_capacity_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(agent_assignments)")}
    if "ready_at" not in columns:
        try:
            conn.execute("ALTER TABLE agent_assignments ADD COLUMN ready_at TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_queue_ready "
                 "ON agent_assignments(status, ready_at, created_at)")


def assert_queue_capacity(conn: sqlite3.Connection, *, parent_agent_id: str) -> None:
    """Refuse an additional queued assignment when a durable queue is full.

    The caller must hold a write transaction.  ``queued`` is counted alone:
    running and parked assignments have already vacated their queue place.
    """
    from core.runtime.db_agent_contract import ContractError

    if not conn.in_transaction:
        raise RuntimeError("queue admission requires a write transaction")
    global_count = conn.execute(
        "SELECT COUNT(*) FROM agent_assignments WHERE status='queued'"
    ).fetchone()[0]
    if global_count >= MAX_QUEUED_GLOBAL:
        raise ContractError("CAPACITY", f"global queue limit {MAX_QUEUED_GLOBAL}")
    parent_count = conn.execute(
        "SELECT COUNT(*) FROM agent_assignments WHERE status='queued' "
        "AND parent_agent_id=?", (parent_agent_id,)
    ).fetchone()[0]
    if parent_count >= MAX_QUEUED_PER_PARENT:
        raise ContractError("CAPACITY", f"parent queue limit {MAX_QUEUED_PER_PARENT}")


def queue_status(conn: sqlite3.Connection, *, parent_agent_id: str = "") -> dict[str, int]:
    """Expose the same DB counters used by admission to Desk and operators."""
    global_count = int(conn.execute(
        "SELECT COUNT(*) FROM agent_assignments WHERE status='queued'"
    ).fetchone()[0])
    parent_count = int(conn.execute(
        "SELECT COUNT(*) FROM agent_assignments WHERE status='queued' "
        "AND parent_agent_id=?", (parent_agent_id,)
    ).fetchone()[0]) if parent_agent_id else 0
    return {"queued_global": global_count, "max_queued_global": MAX_QUEUED_GLOBAL,
            "queued_parent": parent_count, "max_queued_parent": MAX_QUEUED_PER_PARENT}


def mark_ready(*, assignment_id: str) -> bool:
    """Publish a fully provisioned assignment to the worker scheduler."""
    from core.runtime.db_agent_contract import _conn

    conn = _conn()
    cur = conn.execute("UPDATE agent_assignments SET ready_at=?, updated_at=? "
                       "WHERE assignment_id=? AND status='queued' AND ready_at=''",
                       (_now_iso(), _now_iso(), assignment_id))
    conn.commit()
    return cur.rowcount == 1


def claim_worker_slot(*, assignment_id: str) -> bool:
    """Atomically claim one ready assignment under all three active caps.

    Returns false for a full lane or a concurrent winner.  No worker may start
    without a true result.  Parked or terminal assignments do not consume slots.
    """
    from core.runtime.db_agent_contract import _conn

    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            "SELECT owner_user_id, parent_agent_id FROM agent_assignments "
            "WHERE assignment_id=? AND status='queued' AND ready_at!='' "
            "AND (queue_deadline_at='' OR queue_deadline_at>?)",
            (assignment_id, _now_iso())).fetchone()
        if row is None:
            conn.rollback()
            return False
        active = conn.execute(
            "SELECT COUNT(*) FROM agent_assignments WHERE status='active'"
        ).fetchone()[0]
        owner_active = conn.execute(
            "SELECT COUNT(*) FROM agent_assignments WHERE status='active' AND owner_user_id=?",
            (row["owner_user_id"],)).fetchone()[0]
        parent_active = conn.execute(
            "SELECT COUNT(*) FROM agent_assignments WHERE status='active' AND parent_agent_id=?",
            (row["parent_agent_id"],)).fetchone()[0]
        if (active >= MAX_ACTIVE_GLOBAL or owner_active >= MAX_ACTIVE_PER_OWNER
                or parent_active >= MAX_ACTIVE_PER_PARENT):
            conn.rollback()
            return False
        cur = conn.execute(
            "UPDATE agent_assignments SET status='active', updated_at=? "
            "WHERE assignment_id=? AND status='queued' AND ready_at!=''",
            (_now_iso(), assignment_id))
        conn.commit()
        return cur.rowcount == 1
    except BaseException:
        conn.rollback()
        raise


def ready_queue(*, limit: int = MAX_QUEUED_GLOBAL) -> list[tuple[str, str]]:
    """Return ready IDs in FIFO order; callers still have to win the claim."""
    from core.runtime.db_agent_contract import _conn

    rows = _conn().execute(
        "SELECT assignment_id, agent_id FROM agent_assignments "
        "WHERE status='queued' AND ready_at!='' ORDER BY created_at, assignment_id LIMIT ?",
        (max(0, min(int(limit), MAX_QUEUED_GLOBAL)),)).fetchall()
    return [(row["assignment_id"], row["agent_id"]) for row in rows]


def discard_unbound_agent(*, agent_id: str) -> bool:
    """Undo a spawn whose atomic assignment admission lost a capacity race."""
    from core.runtime.db_agent_contract import _conn

    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("SELECT 1 FROM agent_assignments WHERE agent_id=?", (agent_id,)).fetchone():
            conn.rollback()
            return False
        conn.execute("DELETE FROM agent_messages WHERE agent_id=?", (agent_id,))
        cur = conn.execute("DELETE FROM agent_registry WHERE agent_id=?", (agent_id,))
        conn.commit()
        return cur.rowcount == 1
    except BaseException:
        conn.rollback()
        raise


def release_unstarted_claim(*, assignment_id: str) -> bool:
    """Return a failed startup to the queue only before any run or lease began.

    Once a worker reached a model or tool boundary, its outcome belongs to the
    lease/outcome-unknown recovery path; this helper must never replay it.
    """
    from core.runtime.db_agent_contract import _conn

    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT status FROM agent_assignments WHERE assignment_id=?",
                           (assignment_id,)).fetchone()
        if row is None or row["status"] != "active":
            conn.rollback()
            return False
        began = conn.execute("SELECT 1 FROM agent_runs WHERE assignment_id=? "
                             "AND started_at!='' LIMIT 1", (assignment_id,)).fetchone()
        lease = conn.execute("SELECT 1 FROM agent_leases WHERE assignment_id=? AND state='held' "
                             "AND lease_until>?", (assignment_id, _now_iso())).fetchone()
        if began or lease:
            conn.rollback()
            return False
        conn.execute("UPDATE agent_assignments SET status='queued', updated_at=? "
                     "WHERE assignment_id=?", (_now_iso(), assignment_id))
        conn.commit()
        return True
    except BaseException:
        conn.rollback()
        raise
