"""Long-horizon goals store — persistent objectives Jarvis carries across sessions.

Two tables:
- long_horizon_goals: one row per goal (title, status, progress, metadata)
- long_horizon_goal_updates: append-only log of progress notes

Goals are meant to outlive a single conversation. They surface in the
heartbeat so Jarvis stays oriented toward them between interactions.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


VALID_STATUSES = {"active", "paused", "completed", "abandoned"}


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS long_horizon_goals (
            goal_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            priority INTEGER NOT NULL DEFAULT 50,
            progress_pct INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            target_date TEXT,
            completed_at TEXT,
            latest_note TEXT,
            tags TEXT,
            created_by TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_goals_status "
        "ON long_horizon_goals (status, priority DESC, updated_at DESC)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS long_horizon_goal_updates (
            update_id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            note TEXT NOT NULL,
            progress_delta INTEGER,
            source TEXT,
            FOREIGN KEY (goal_id) REFERENCES long_horizon_goals(goal_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_goal_updates_goal "
        "ON long_horizon_goal_updates (goal_id, created_at DESC)"
    )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def create_goal(
    *,
    title: str,
    description: str | None = None,
    priority: int = 50,
    target_date: str | None = None,
    tags: list[str] | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    goal_id = _new_id("goal")
    now = _now_iso()
    tags_json = json.dumps(list(tags)) if tags else None
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO long_horizon_goals (
                goal_id, title, description, status, priority, progress_pct,
                created_at, updated_at, target_date, tags, created_by
            ) VALUES (?, ?, ?, 'active', ?, 0, ?, ?, ?, ?, ?)
            """,
            (
                goal_id,
                title.strip(),
                (description or "").strip() or None,
                max(0, min(100, int(priority))),
                now,
                now,
                target_date,
                tags_json,
                created_by,
            ),
        )
        conn.commit()
    return get_goal(goal_id) or {}


def append_goal_update(
    *,
    goal_id: str,
    note: str,
    progress_delta: int | None = None,
    source: str | None = None,
    new_status: str | None = None,
) -> dict[str, Any] | None:
    """Append a progress note and optionally bump progress/status."""
    goal = get_goal(goal_id)
    if not goal:
        return None
    update_id = _new_id("gup")
    now = _now_iso()
    new_progress = int(goal.get("progress_pct") or 0)
    if progress_delta is not None:
        new_progress = max(0, min(100, new_progress + int(progress_delta)))
    status = goal.get("status") or "active"
    completed_at = goal.get("completed_at")
    if new_status and new_status in VALID_STATUSES:
        status = new_status
        if status == "completed" and not completed_at:
            completed_at = now
        if status == "active":
            completed_at = None
    if new_progress >= 100 and status == "active":
        status = "completed"
        completed_at = completed_at or now
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO long_horizon_goal_updates (
                update_id, goal_id, created_at, note, progress_delta, source
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                update_id,
                goal_id,
                now,
                note.strip(),
                progress_delta,
                source,
            ),
        )
        conn.execute(
            """
            UPDATE long_horizon_goals
               SET progress_pct = ?,
                   status = ?,
                   completed_at = ?,
                   latest_note = ?,
                   updated_at = ?
             WHERE goal_id = ?
            """,
            (
                new_progress,
                status,
                completed_at,
                note.strip()[:500],
                now,
                goal_id,
            ),
        )
        conn.commit()
    return get_goal(goal_id)


def get_goal(goal_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM long_horizon_goals WHERE goal_id = ?",
            (goal_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_goal(dict(row))


def list_goals(
    *,
    status: str | None = "active",
    limit: int = 50,
) -> list[dict[str, Any]]:
    where = ""
    params: list[Any] = []
    if status and status != "all":
        where = "WHERE status = ?"
        params.append(status)
    query = (
        f"SELECT * FROM long_horizon_goals {where} "
        "ORDER BY priority DESC, updated_at DESC LIMIT ?"
    )
    params.append(int(limit))
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(query, params).fetchall()
    return [_row_to_goal(dict(r)) for r in rows]


def list_goal_updates(goal_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(
            "SELECT * FROM long_horizon_goal_updates "
            "WHERE goal_id = ? ORDER BY created_at DESC LIMIT ?",
            (goal_id, int(limit)),
        ).fetchall()
    return [dict(r) for r in rows]


def update_goal_fields(
    goal_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    priority: int | None = None,
    target_date: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any] | None:
    goal = get_goal(goal_id)
    if not goal:
        return None
    sets: list[str] = []
    params: list[Any] = []
    if title is not None:
        sets.append("title = ?")
        params.append(title.strip())
    if description is not None:
        sets.append("description = ?")
        params.append(description.strip() or None)
    if priority is not None:
        sets.append("priority = ?")
        params.append(max(0, min(100, int(priority))))
    if target_date is not None:
        sets.append("target_date = ?")
        params.append(target_date or None)
    if tags is not None:
        sets.append("tags = ?")
        params.append(json.dumps(list(tags)) if tags else None)
    if not sets:
        return goal
    sets.append("updated_at = ?")
    params.append(_now_iso())
    params.append(goal_id)
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            f"UPDATE long_horizon_goals SET {', '.join(sets)} WHERE goal_id = ?",
            params,
        )
        conn.commit()
    return get_goal(goal_id)


def delete_goal(goal_id: str) -> bool:
    with connect() as conn:
        _ensure_tables(conn)
        cur = conn.execute(
            "DELETE FROM long_horizon_goals WHERE goal_id = ?", (goal_id,)
        )
        conn.execute(
            "DELETE FROM long_horizon_goal_updates WHERE goal_id = ?", (goal_id,)
        )
        conn.commit()
    return (cur.rowcount or 0) > 0


def count_goals(*, status: str | None = None) -> int:
    where = ""
    params: list[Any] = []
    if status:
        where = "WHERE status = ?"
        params.append(status)
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            f"SELECT COUNT(*) AS c FROM long_horizon_goals {where}",
            params,
        ).fetchone()
    return int(row["c"] if row else 0)


def _row_to_goal(row: dict[str, Any]) -> dict[str, Any]:
    tags_raw = row.get("tags")
    try:
        tags = json.loads(tags_raw) if tags_raw else []
    except Exception:
        tags = []
    row["tags"] = tags
    return row
