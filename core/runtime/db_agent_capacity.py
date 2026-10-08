"""Atomic admission limits for contract agent assignments.

The queue is a durable reservation, distinct from an active worker slot.  This
module is deliberately called with the connection that already owns the
``BEGIN IMMEDIATE`` transaction in ``accept_assignment``.  Opening a second
connection here would roll back the caller's transaction in this runtime.
"""
from __future__ import annotations

import sqlite3


MAX_QUEUED_GLOBAL = 24
MAX_QUEUED_PER_PARENT = 8


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
