"""Agent-audit-trail — PERSISTENT per-user/per-tool execution log for
jarvis-code's forwarded tool calls (Fase 5 Task 9).

Distinct from the cost-nerve (core.costing.ledger — spend, not who-ran-what)
and from the gate-verdict-ledger (core.runtime.db_gate_verdicts — aggregated
counts, not individual rows): this table answers "who ran what, when, and
what happened" for owner-only readback. One row per forwarded tool
execution (both allowed and denied) — behind the jc_audit_trail flag
(default OFF), fully inert when unflagged (see agent_audit.py route).

Self-safe: all write/read failures are swallowed (an audit-log failure must
never break the tool call it's logging).
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jc_agent_audit (
            id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT '',
            tool TEXT NOT NULL DEFAULT '',
            target_summary TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_jc_agent_audit_user_ts "
        "ON jc_agent_audit (user_id, ts DESC)"
    )


def write_row(*, user_id: str, role: str, tool: str,
             target_summary: str = "", decision: str = "") -> bool:
    """Insert one audit row. Returns True on success, False on any failure
    (never raises — a logging failure must not break the tool call)."""
    try:
        with connect() as conn:
            _ensure_table(conn)
            conn.execute(
                """
                INSERT INTO jc_agent_audit (id, ts, user_id, role, tool, target_summary, decision)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    datetime.now(UTC).isoformat(),
                    str(user_id or ""),
                    str(role or ""),
                    str(tool or ""),
                    str(target_summary or "")[:500],
                    str(decision or ""),
                ),
            )
            conn.commit()
            return True
    except Exception:
        return False


def read_rows(user_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Read audit rows, most recent first. Filters by user_id when given.
    Self-safe → [] on any failure."""
    limit = max(1, min(int(limit or 100), 1000))
    try:
        with connect() as conn:
            _ensure_table(conn)
            if user_id:
                rows = conn.execute(
                    "SELECT id, ts, user_id, role, tool, target_summary, decision "
                    "FROM jc_agent_audit WHERE user_id = ? ORDER BY ts DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, ts, user_id, role, tool, target_summary, decision "
                    "FROM jc_agent_audit ORDER BY ts DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []
