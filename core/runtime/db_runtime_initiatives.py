"""Persistence for the runtime-initiatives cluster.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
the runtime_initiatives table via `_ensure_runtime_initiatives_table` (called
both by init_db — via re-export on the db facade — and lazily by the CRUD
functions), plus all CRUD, the approve/reject/find helpers and the private
`_runtime_initiative_from_row` row-mapper.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def _ensure_runtime_initiatives_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_initiatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            initiative_id TEXT NOT NULL UNIQUE,
            initiative_type TEXT NOT NULL DEFAULT 'initiative',
            focus TEXT NOT NULL,
            why_text TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            source_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'medium',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            detected_at TEXT NOT NULL,
            first_seeded_at TEXT NOT NULL DEFAULT '',
            last_attempt_at TEXT NOT NULL DEFAULT '',
            next_attempt_at TEXT NOT NULL DEFAULT '',
            blocked_reason TEXT NOT NULL DEFAULT '',
            acted_at TEXT NOT NULL DEFAULT '',
            last_action_at TEXT NOT NULL DEFAULT '',
            abandoned_at TEXT NOT NULL DEFAULT '',
            action_summary TEXT NOT NULL DEFAULT '',
            outcome TEXT NOT NULL DEFAULT '',
            outcome_note TEXT NOT NULL DEFAULT '',
            user_approved_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            scheduled_for_user_id TEXT,
            initiated_by TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_initiatives_status_due
        ON runtime_initiatives(status, next_attempt_at, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_initiatives_focus_status
        ON runtime_initiatives(focus, status, id DESC)
        """
    )
    # Add outcome columns to existing tables (idempotent)
    for col_sql in (
        "ALTER TABLE runtime_initiatives ADD COLUMN initiative_type TEXT NOT NULL DEFAULT 'initiative'",
        "ALTER TABLE runtime_initiatives ADD COLUMN why_text TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN outcome TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN outcome_note TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN user_approved_at TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN first_seeded_at TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN last_action_at TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN abandoned_at TEXT NOT NULL DEFAULT ''",
    ):
        try:
            conn.execute(col_sql)
            conn.commit()
        except Exception:
            pass  # column already exists


def _runtime_initiative_from_row(row: sqlite3.Row) -> dict[str, object]:
    d = dict(row)
    return {
        "initiative_id": d.get("initiative_id", ""),
        "initiative_type": d.get("initiative_type", "initiative"),
        "focus": d.get("focus", ""),
        "why_text": d.get("why_text", ""),
        "source": d.get("source", ""),
        "source_id": d.get("source_id", ""),
        "detected_at": d.get("detected_at", ""),
        "first_seeded_at": d.get("first_seeded_at", ""),
        "status": d.get("status", "pending"),
        "priority": d.get("priority", "medium"),
        "attempt_count": int(d.get("attempt_count") or 0),
        "last_attempt_at": d.get("last_attempt_at", ""),
        "next_attempt_at": d.get("next_attempt_at", ""),
        "blocked_reason": d.get("blocked_reason", ""),
        "acted_at": d.get("acted_at", ""),
        "last_action_at": d.get("last_action_at", ""),
        "abandoned_at": d.get("abandoned_at", ""),
        "action_summary": d.get("action_summary", ""),
        "outcome": d.get("outcome", ""),
        "outcome_note": d.get("outcome_note", ""),
        "user_approved_at": d.get("user_approved_at", ""),
        "updated_at": d.get("updated_at", ""),
    }


def create_runtime_initiative(
    *,
    initiative_id: str,
    initiative_type: str = "initiative",
    focus: str,
    why_text: str = "",
    source: str = "",
    source_id: str = "",
    status: str = "pending",
    priority: str = "medium",
    detected_at: str,
    first_seeded_at: str = "",
    next_attempt_at: str = "",
    updated_at: str,
    scheduled_for_user_id: str | None = None,
    initiated_by: str | None = None,
) -> dict[str, object]:
    # Auto-stamp from workspace_context if caller did not provide values.
    if scheduled_for_user_id is None and initiated_by is None:
        try:
            from core.identity.workspace_context import current_user_id
            uid = current_user_id() or None
            scheduled_for_user_id = uid
            initiated_by = f"user:{uid}" if uid else "jarvis-self"
        except Exception:
            pass
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        conn.execute(
            """
            INSERT INTO runtime_initiatives (
                initiative_id,
                initiative_type,
                focus,
                why_text,
                source,
                source_id,
                status,
                priority,
                detected_at,
                first_seeded_at,
                next_attempt_at,
                updated_at,
                scheduled_for_user_id,
                initiated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                initiative_id,
                initiative_type,
                focus,
                why_text,
                source,
                source_id,
                status,
                priority,
                detected_at,
                first_seeded_at,
                next_attempt_at,
                updated_at,
                scheduled_for_user_id,
                initiated_by,
            ),
        )
        conn.commit()
    initiative = get_runtime_initiative(initiative_id)
    if initiative is None:
        raise RuntimeError("runtime initiative was not persisted")
    return initiative


def get_runtime_initiative(initiative_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        row = conn.execute(
            """
            SELECT
                initiative_id,
                initiative_type,
                focus,
                why_text,
                source,
                source_id,
                detected_at,
                first_seeded_at,
                status,
                priority,
                attempt_count,
                last_attempt_at,
                next_attempt_at,
                blocked_reason,
                acted_at,
                last_action_at,
                abandoned_at,
                action_summary,
                outcome,
                outcome_note,
                user_approved_at,
                updated_at
            FROM runtime_initiatives
            WHERE initiative_id = ?
            LIMIT 1
            """,
            (initiative_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_initiative_from_row(row)


def find_pending_runtime_initiative_by_focus(
    focus: str,
    *,
    initiative_type: str | None = None,
) -> dict[str, object] | None:
    normalized = str(focus or "").strip().lower()
    if not normalized:
        return None
    clauses = ["status = 'pending'", "lower(focus) = ?"]
    params: list[object] = [normalized]
    if initiative_type:
        clauses.append("initiative_type = ?")
        params.append(initiative_type)
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        row = conn.execute(
            f"""
            SELECT
                initiative_id,
                initiative_type,
                focus,
                why_text,
                source,
                source_id,
                detected_at,
                first_seeded_at,
                status,
                priority,
                attempt_count,
                last_attempt_at,
                next_attempt_at,
                blocked_reason,
                acted_at,
                last_action_at,
                abandoned_at,
                action_summary,
                outcome,
                outcome_note,
                user_approved_at,
                updated_at
            FROM runtime_initiatives
            WHERE {' AND '.join(clauses)}
            ORDER BY id DESC
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
    if row is None:
        return None
    return _runtime_initiative_from_row(row)


def list_runtime_initiatives(
    *,
    status: str | None = None,
    initiative_type: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    from core.identity.workspace_context import current_user_id as _uid
    _current_uid = _uid()
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if initiative_type:
        clauses.append("initiative_type = ?")
        params.append(initiative_type)
    if _current_uid:
        clauses.append(
            "(relevant_to_users IS NULL OR relevant_to_users LIKE '%' || ? || '%')"
        )
        params.append(_current_uid)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        rows = conn.execute(
            f"""
            SELECT
                initiative_id,
                initiative_type,
                focus,
                why_text,
                source,
                source_id,
                detected_at,
                first_seeded_at,
                status,
                priority,
                attempt_count,
                last_attempt_at,
                next_attempt_at,
                blocked_reason,
                acted_at,
                last_action_at,
                abandoned_at,
                action_summary,
                outcome,
                outcome_note,
                user_approved_at,
                updated_at
            FROM runtime_initiatives
            {where_sql}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_initiative_from_row(row) for row in rows]


def update_runtime_initiative(
    initiative_id: str,
    *,
    status: str | None = None,
    initiative_type: str | None = None,
    priority: str | None = None,
    detected_at: str | None = None,
    why_text: str | None = None,
    first_seeded_at: str | None = None,
    attempt_count: int | None = None,
    last_attempt_at: str | None = None,
    next_attempt_at: str | None = None,
    blocked_reason: str | None = None,
    acted_at: str | None = None,
    last_action_at: str | None = None,
    abandoned_at: str | None = None,
    action_summary: str | None = None,
    updated_at: str,
) -> dict[str, object] | None:
    updates: list[str] = ["updated_at = ?"]
    params: list[object] = [updated_at]
    field_map: dict[str, object | None] = {
        "status": status,
        "initiative_type": initiative_type,
        "priority": priority,
        "detected_at": detected_at,
        "why_text": why_text,
        "first_seeded_at": first_seeded_at,
        "attempt_count": attempt_count,
        "last_attempt_at": last_attempt_at,
        "next_attempt_at": next_attempt_at,
        "blocked_reason": blocked_reason,
        "acted_at": acted_at,
        "last_action_at": last_action_at,
        "abandoned_at": abandoned_at,
        "action_summary": action_summary,
    }
    for column, value in field_map.items():
        if value is None:
            continue
        updates.append(f"{column} = ?")
        params.append(value)
    params.append(initiative_id)
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        row = conn.execute(
            "SELECT initiative_id FROM runtime_initiatives WHERE initiative_id = ? LIMIT 1",
            (initiative_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            f"""
            UPDATE runtime_initiatives
            SET {', '.join(updates)}
            WHERE initiative_id = ?
            """,
            tuple(params),
        )
        conn.commit()
    return get_runtime_initiative(initiative_id)


def approve_runtime_initiative(
    initiative_id: str,
    *,
    outcome_note: str = "",
    updated_at: str,
) -> dict[str, object] | None:
    """Mark an initiative as user-approved. Sets user_approved_at and outcome='approved'."""
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        row = conn.execute(
            "SELECT initiative_id FROM runtime_initiatives WHERE initiative_id = ? LIMIT 1",
            (initiative_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_initiatives
            SET outcome = 'approved', outcome_note = ?, user_approved_at = ?, updated_at = ?
            WHERE initiative_id = ?
            """,
            (outcome_note[:300], updated_at, updated_at, initiative_id),
        )
        conn.commit()
    return get_runtime_initiative(initiative_id)


def reject_runtime_initiative(
    initiative_id: str,
    *,
    outcome_note: str = "",
    updated_at: str,
) -> dict[str, object] | None:
    """Mark an initiative as user-rejected. Sets outcome='rejected' and expires it."""
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        row = conn.execute(
            "SELECT initiative_id FROM runtime_initiatives WHERE initiative_id = ? LIMIT 1",
            (initiative_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_initiatives
            SET outcome = 'rejected', outcome_note = ?, status = 'expired',
                user_approved_at = ?, updated_at = ?
            WHERE initiative_id = ?
            """,
            (outcome_note[:300], updated_at, updated_at, initiative_id),
        )
        conn.commit()
    return get_runtime_initiative(initiative_id)

