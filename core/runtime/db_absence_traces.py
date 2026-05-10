"""DB helpers for absence_traces (Lag 11 forgetting).

Auto-counter UPSERT, self-marker INSERT, query helpers for the heartbeat
renderer, and recursive-release UPDATE. Lives separately from db.py to
keep that file from growing further.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _month_key(at: datetime | None = None) -> str:
    at = at or datetime.now(UTC)
    return at.strftime("%Y-%m")


def increment_auto_counter(
    *,
    workspace_id: str,
    delta: int = 1,
    at: datetime | None = None,
) -> dict[str, Any]:
    """UPSERT the monthly auto-counter row.

    First call in a month creates the row with auto_count=delta.
    Subsequent calls increment.
    """
    at = at or datetime.now(UTC)
    month = _month_key(at)
    now = _now()
    trace_id = f"auto_{workspace_id}_{month}_{uuid.uuid4().hex[:8]}"
    with connect() as conn:
        # Try to update existing row first
        cur = conn.execute(
            "UPDATE absence_traces SET auto_count = auto_count + ?, updated_at = ? "
            "WHERE track_kind = 'auto_counter' "
            "AND workspace_id = ? AND month_key = ?",
            (delta, now, workspace_id, month),
        )
        if cur.rowcount == 0:
            conn.execute(
                "INSERT INTO absence_traces (trace_id, track_kind, workspace_id, "
                "month_key, auto_count, created_at, updated_at) "
                "VALUES (?, 'auto_counter', ?, ?, ?, ?, ?)",
                (trace_id, workspace_id, month, delta, now, now),
            )
        # Read back current value
        row = conn.execute(
            "SELECT trace_id, auto_count FROM absence_traces "
            "WHERE track_kind = 'auto_counter' AND workspace_id = ? AND month_key = ?",
            (workspace_id, month),
        ).fetchone()
    return {
        "trace_id": row[0],
        "auto_count": row[1],
        "month_key": month,
        "workspace_id": workspace_id,
    }


def decrement_auto_counter(
    *, workspace_id: str, month_key: str, delta: int = 1
) -> bool:
    """Used by revive_soft_deleted to undo a counted fade.

    Returns True if a row was updated, False otherwise.
    """
    now = _now()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE absence_traces SET auto_count = MAX(auto_count - ?, 0), "
            "updated_at = ? "
            "WHERE track_kind = 'auto_counter' "
            "AND workspace_id = ? AND month_key = ?",
            (delta, now, workspace_id, month_key),
        )
        return cur.rowcount > 0


def insert_self_marker(
    *, workspace_id: str, period_label: str
) -> dict[str, Any]:
    """Record an irrevocable self-release. NO memory reference is stored."""
    now = _now()
    trace_id = f"self_{workspace_id}_{uuid.uuid4().hex}"
    with connect() as conn:
        conn.execute(
            "INSERT INTO absence_traces (trace_id, track_kind, workspace_id, "
            "released_at, period_label, is_self_released, created_at, updated_at) "
            "VALUES (?, 'self_marker', ?, ?, ?, 0, ?, ?)",
            (trace_id, workspace_id, now, period_label, now, now),
        )
    return {
        "trace_id": trace_id,
        "released_at": now,
        "period_label": period_label,
    }


def list_self_markers(
    *, workspace_id: str, include_released: bool = False
) -> list[dict[str, Any]]:
    """List self-markers for a workspace, ordered oldest first."""
    where = "track_kind = 'self_marker' AND workspace_id = ?"
    params: list[Any] = [workspace_id]
    if not include_released:
        where += " AND is_self_released = 0"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT trace_id, released_at, period_label, is_self_released, "
            f"created_at FROM absence_traces WHERE {where} "
            f"ORDER BY released_at ASC",
            params,
        ).fetchall()
    return [
        {
            "trace_id": r[0],
            "released_at": r[1],
            "period_label": r[2],
            "is_self_released": bool(r[3]),
            "created_at": r[4],
        }
        for r in rows
    ]


def get_auto_counter(
    *, workspace_id: str, month_key: str | None = None
) -> dict[str, Any] | None:
    """Get the counter row for a given month (default: current month)."""
    month = month_key or _month_key()
    with connect() as conn:
        row = conn.execute(
            "SELECT trace_id, auto_count, month_key FROM absence_traces "
            "WHERE track_kind = 'auto_counter' "
            "AND workspace_id = ? AND month_key = ?",
            (workspace_id, month),
        ).fetchone()
    if row is None:
        return None
    return {
        "trace_id": row[0],
        "auto_count": row[1],
        "month_key": row[2],
        "workspace_id": workspace_id,
    }


def mark_self_released(*, trace_id: str) -> bool:
    """Recursive release: mark an existing self-marker as released.

    The row stays in the DB (regnskab over rekursiv slip-handling) but
    is_self_released=1 makes the heartbeat renderer skip it.
    """
    now = _now()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE absence_traces SET is_self_released = 1, updated_at = ? "
            "WHERE track_kind = 'self_marker' AND trace_id = ?",
            (now, trace_id),
        )
        return cur.rowcount > 0
