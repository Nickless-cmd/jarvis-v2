"""Persistence for the visible-lane projection tables.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
`visible_runs` and `visible_work_notes` (ensure_visible_tables) plus the
recent-read helpers, the work-note upsert, and the cross-session continuity
projection built on top of them.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def ensure_visible_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visible_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL UNIQUE,
            lane TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT NOT NULL,
            text_preview TEXT,
            error TEXT,
            capability_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visible_work_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT NOT NULL UNIQUE,
            work_id TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            lane TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            user_message_preview TEXT,
            capability_id TEXT,
            work_preview TEXT,
            projection_source TEXT,
            created_at TEXT NOT NULL,
            finished_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visible_work_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id TEXT NOT NULL UNIQUE,
            run_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            lane TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT NOT NULL,
            user_message_preview TEXT,
            capability_id TEXT,
            work_preview TEXT
        )
        """
    )


def recent_visible_runs(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                run_id,
                lane,
                provider,
                model,
                status,
                started_at,
                finished_at,
                text_preview,
                error,
                capability_id
            FROM visible_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "run_id": row["run_id"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "status": row["status"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "text_preview": row["text_preview"],
            "error": row["error"],
            "capability_id": row["capability_id"],
        }
        for row in rows
    ]


def recent_visible_work_notes(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                note_id,
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                user_message_preview,
                capability_id,
                work_preview,
                projection_source,
                created_at,
                finished_at
            FROM visible_work_notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "note_id": row["note_id"],
            "work_id": row["work_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "user_message_preview": row["user_message_preview"],
            "capability_id": row["capability_id"],
            "work_preview": row["work_preview"],
            "projection_source": row["projection_source"],
            "created_at": row["created_at"],
            "finished_at": row["finished_at"],
        }
        for row in rows
    ]


def recent_visible_work_units(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                started_at,
                finished_at,
                user_message_preview,
                capability_id,
                work_preview
            FROM visible_work_units
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "work_id": row["work_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "user_message_preview": row["user_message_preview"],
            "capability_id": row["capability_id"],
            "work_preview": row["work_preview"],
        }
        for row in rows
    ]


def record_visible_work_note(
    *,
    note_id: str,
    work_id: str,
    run_id: str,
    status: str,
    lane: str,
    provider: str,
    model: str,
    user_message_preview: str = "",
    capability_id: str = "",
    work_preview: str = "",
    projection_source: str = "",
    created_at: str,
    finished_at: str,
) -> dict[str, object]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO visible_work_notes (
                note_id,
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                user_message_preview,
                capability_id,
                work_preview,
                projection_source,
                created_at,
                finished_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                note_id=excluded.note_id,
                work_id=excluded.work_id,
                status=excluded.status,
                lane=excluded.lane,
                provider=excluded.provider,
                model=excluded.model,
                user_message_preview=excluded.user_message_preview,
                capability_id=excluded.capability_id,
                work_preview=excluded.work_preview,
                projection_source=excluded.projection_source,
                created_at=excluded.created_at,
                finished_at=excluded.finished_at
            """,
            (
                note_id,
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                user_message_preview,
                capability_id,
                work_preview,
                projection_source,
                created_at,
                finished_at,
            ),
        )
        conn.commit()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                note_id,
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                user_message_preview,
                capability_id,
                work_preview,
                projection_source,
                created_at,
                finished_at
            FROM visible_work_notes
            WHERE run_id = ?
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("visible work note was not persisted")
    return {
        "note_id": row["note_id"],
        "work_id": row["work_id"],
        "run_id": row["run_id"],
        "status": row["status"],
        "lane": row["lane"],
        "provider": row["provider"],
        "model": row["model"],
        "user_message_preview": row["user_message_preview"],
        "capability_id": row["capability_id"],
        "work_preview": row["work_preview"],
        "projection_source": row["projection_source"],
        "created_at": row["created_at"],
        "finished_at": row["finished_at"],
    }


def visible_session_continuity() -> dict[str, object]:
    # recent_capability_invocations stays in core.runtime.db (mega-orchestrator
    # table). Import lazily to avoid an import cycle: db.py imports this module
    # at its bottom.
    from core.runtime.db import recent_capability_invocations

    # Use visible_work_notes (which carry both user_message_preview AND
    # work_preview) instead of plain visible_runs (which only have the
    # assistant text). This makes the recent_run_summaries actually
    # carry the dialog context between sessions instead of being a
    # one-sided assistant log.
    recent_notes = recent_visible_work_notes(limit=3)
    recent_runs = recent_visible_runs(limit=3) if not recent_notes else []
    recent_invocations = recent_capability_invocations(limit=2)
    latest_note = recent_notes[0] if recent_notes else {}
    latest_run = recent_runs[0] if recent_runs else {}
    recent_capability_ids = [
        capability_id
        for item in recent_invocations
        if (capability_id := str(item.get("capability_id") or "").strip())
    ]
    recent_run_summaries = [
        {
            "run_id": item.get("run_id"),
            "status": item.get("status"),
            "finished_at": item.get("finished_at"),
            "capability_id": item.get("capability_id"),
            "user_message_preview": item.get("user_message_preview"),
            "text_preview": item.get("work_preview"),
        }
        for item in recent_notes
    ] or [
        {
            "run_id": item.get("run_id"),
            "status": item.get("status"),
            "finished_at": item.get("finished_at"),
            "capability_id": item.get("capability_id"),
            "user_message_preview": None,
            "text_preview": item.get("text_preview"),
        }
        for item in recent_runs
    ]
    latest_payload = latest_note or latest_run or {}
    return {
        "active": bool(latest_payload or recent_invocations),
        "source": "persisted-visible-work-notes+capability-invocations"
        if recent_notes
        else "persisted-visible-runs+capability-invocations",
        "latest_run_id": latest_payload.get("run_id"),
        "latest_status": latest_payload.get("status"),
        "latest_finished_at": latest_payload.get("finished_at"),
        "latest_text_preview": latest_payload.get("work_preview")
        or latest_payload.get("text_preview"),
        "latest_user_message_preview": latest_payload.get("user_message_preview"),
        "latest_capability_id": latest_payload.get("capability_id"),
        "recent_capability_ids": recent_capability_ids,
        "recent_run_summaries": recent_run_summaries,
        "included_run_rows": len(recent_notes) or len(recent_runs),
        "included_capability_rows": len(recent_invocations),
    }
