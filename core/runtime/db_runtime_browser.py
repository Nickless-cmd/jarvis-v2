"""Persistence for the `runtime_browser_bodies` table — Jarvis' browser bodies.

Split out of core/runtime/db.py per the boy-scout rule. Owns its schema
(ensure_runtime_browser_tables) plus the get/upsert/list CRUD.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def ensure_runtime_browser_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_browser_bodies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            body_id TEXT NOT NULL UNIQUE,
            profile_name TEXT NOT NULL,
            status TEXT NOT NULL,
            active_task_id TEXT NOT NULL DEFAULT '',
            active_flow_id TEXT NOT NULL DEFAULT '',
            focused_tab_id TEXT NOT NULL DEFAULT '',
            tabs_json TEXT NOT NULL DEFAULT '[]',
            last_url TEXT NOT NULL DEFAULT '',
            last_title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_browser_bodies_profile
        ON runtime_browser_bodies(profile_name, id DESC)
        """
    )


def get_runtime_browser_body(body_id: str) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                body_id,
                profile_name,
                status,
                active_task_id,
                active_flow_id,
                focused_tab_id,
                tabs_json,
                last_url,
                last_title,
                summary,
                created_at,
                updated_at
            FROM runtime_browser_bodies
            WHERE body_id = ?
            LIMIT 1
            """,
            (body_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "body_id": row["body_id"],
        "profile_name": row["profile_name"],
        "status": row["status"],
        "active_task_id": row["active_task_id"],
        "active_flow_id": row["active_flow_id"],
        "focused_tab_id": row["focused_tab_id"],
        "tabs_json": row["tabs_json"],
        "last_url": row["last_url"],
        "last_title": row["last_title"],
        "summary": row["summary"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def upsert_runtime_browser_body(
    *,
    body_id: str,
    profile_name: str,
    status: str,
    active_task_id: str = "",
    active_flow_id: str = "",
    focused_tab_id: str = "",
    tabs_json: str = "[]",
    last_url: str = "",
    last_title: str = "",
    summary: str = "",
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_browser_bodies (
                body_id,
                profile_name,
                status,
                active_task_id,
                active_flow_id,
                focused_tab_id,
                tabs_json,
                last_url,
                last_title,
                summary,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(body_id) DO UPDATE SET
                profile_name = excluded.profile_name,
                status = excluded.status,
                active_task_id = excluded.active_task_id,
                active_flow_id = excluded.active_flow_id,
                focused_tab_id = excluded.focused_tab_id,
                tabs_json = excluded.tabs_json,
                last_url = excluded.last_url,
                last_title = excluded.last_title,
                summary = excluded.summary,
                updated_at = excluded.updated_at
            """,
            (
                body_id,
                profile_name,
                status,
                active_task_id,
                active_flow_id,
                focused_tab_id,
                tabs_json,
                last_url,
                last_title,
                summary,
                created_at,
                updated_at,
            ),
        )
        conn.commit()
    body = get_runtime_browser_body(body_id)
    if body is None:
        raise RuntimeError("runtime browser body was not persisted")
    return body


def list_runtime_browser_bodies(limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                body_id,
                profile_name,
                status,
                active_task_id,
                active_flow_id,
                focused_tab_id,
                tabs_json,
                last_url,
                last_title,
                summary,
                created_at,
                updated_at
            FROM runtime_browser_bodies
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "body_id": row["body_id"],
            "profile_name": row["profile_name"],
            "status": row["status"],
            "active_task_id": row["active_task_id"],
            "active_flow_id": row["active_flow_id"],
            "focused_tab_id": row["focused_tab_id"],
            "tabs_json": row["tabs_json"],
            "last_url": row["last_url"],
            "last_title": row["last_title"],
            "summary": row["summary"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]
