"""Persistence for the `bounded_action_continuity_state` table.

Split out of core/runtime/db.py per the boy-scout rule. Owns its schema
(ensure_bounded_action_tables) plus the get/upsert CRUD and row-mapping helper.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def ensure_bounded_action_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bounded_action_continuity_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            continuity_id TEXT NOT NULL,
            action_continuity_state TEXT NOT NULL,
            last_action_type TEXT NOT NULL,
            last_action_target TEXT NOT NULL,
            last_action_summary TEXT NOT NULL,
            last_action_outcome TEXT NOT NULL,
            last_action_at TEXT NOT NULL,
            action_mode TEXT NOT NULL,
            read_only INTEGER NOT NULL DEFAULT 1,
            mutation_permitted INTEGER NOT NULL DEFAULT 0,
            followup_state TEXT NOT NULL,
            followup_hint TEXT NOT NULL,
            post_action_understanding TEXT NOT NULL,
            post_action_concern TEXT NOT NULL,
            confidence TEXT NOT NULL,
            source_contributors TEXT NOT NULL DEFAULT '',
            boundary TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def _bounded_action_continuity_state_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    source_contributors = [
        item for item in str(row["source_contributors"] or "").split("|") if item
    ]
    return {
        "active": bool(row["last_action_at"]),
        "kind": "bounded-read-only-action-continuity-light",
        "continuity_id": str(row["continuity_id"] or ""),
        "action_continuity_state": str(row["action_continuity_state"] or "idle"),
        "last_action_type": str(row["last_action_type"] or ""),
        "last_action_target": str(row["last_action_target"] or ""),
        "last_action_summary": str(row["last_action_summary"] or ""),
        "last_action_outcome": str(row["last_action_outcome"] or "none"),
        "last_action_at": str(row["last_action_at"] or ""),
        "action_mode": str(row["action_mode"] or "read-only"),
        "read_only": bool(row["read_only"]),
        "mutation_permitted": bool(row["mutation_permitted"]),
        "followup_state": str(row["followup_state"] or "none"),
        "followup_hint": str(row["followup_hint"] or ""),
        "post_action_understanding": str(row["post_action_understanding"] or ""),
        "post_action_concern": str(row["post_action_concern"] or "stable"),
        "confidence": str(row["confidence"] or "low"),
        "source_contributors": source_contributors,
        "boundary": str(row["boundary"] or ""),
        "updated_at": str(row["updated_at"] or ""),
        "source": "/runtime/bounded-action-continuity",
    }


def get_bounded_action_continuity_state() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                continuity_id,
                action_continuity_state,
                last_action_type,
                last_action_target,
                last_action_summary,
                last_action_outcome,
                last_action_at,
                action_mode,
                read_only,
                mutation_permitted,
                followup_state,
                followup_hint,
                post_action_understanding,
                post_action_concern,
                confidence,
                source_contributors,
                boundary,
                updated_at
            FROM bounded_action_continuity_state
            WHERE id = 1
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return _bounded_action_continuity_state_from_row(row)


def upsert_bounded_action_continuity_state(
    *,
    active: bool,
    kind: str,
    continuity_id: str,
    action_continuity_state: str,
    last_action_type: str,
    last_action_target: str,
    last_action_summary: str,
    last_action_outcome: str,
    last_action_at: str,
    action_mode: str,
    read_only: bool,
    mutation_permitted: bool,
    followup_state: str,
    followup_hint: str,
    post_action_understanding: str,
    post_action_concern: str,
    confidence: str,
    source_contributors: list[str],
    boundary: str,
    updated_at: str,
    source: str,
) -> dict[str, object]:
    del active, kind, source
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO bounded_action_continuity_state (
                id,
                continuity_id,
                action_continuity_state,
                last_action_type,
                last_action_target,
                last_action_summary,
                last_action_outcome,
                last_action_at,
                action_mode,
                read_only,
                mutation_permitted,
                followup_state,
                followup_hint,
                post_action_understanding,
                post_action_concern,
                confidence,
                source_contributors,
                boundary,
                updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                continuity_id = excluded.continuity_id,
                action_continuity_state = excluded.action_continuity_state,
                last_action_type = excluded.last_action_type,
                last_action_target = excluded.last_action_target,
                last_action_summary = excluded.last_action_summary,
                last_action_outcome = excluded.last_action_outcome,
                last_action_at = excluded.last_action_at,
                action_mode = excluded.action_mode,
                read_only = excluded.read_only,
                mutation_permitted = excluded.mutation_permitted,
                followup_state = excluded.followup_state,
                followup_hint = excluded.followup_hint,
                post_action_understanding = excluded.post_action_understanding,
                post_action_concern = excluded.post_action_concern,
                confidence = excluded.confidence,
                source_contributors = excluded.source_contributors,
                boundary = excluded.boundary,
                updated_at = excluded.updated_at
            """,
            (
                continuity_id,
                action_continuity_state,
                last_action_type,
                last_action_target,
                last_action_summary,
                last_action_outcome,
                last_action_at,
                action_mode,
                1 if read_only else 0,
                1 if mutation_permitted else 0,
                followup_state,
                followup_hint,
                post_action_understanding,
                post_action_concern,
                confidence,
                "|".join(
                    str(item or "").strip()
                    for item in source_contributors
                    if str(item or "").strip()
                ),
                boundary,
                updated_at,
            ),
        )
        conn.commit()
    state = get_bounded_action_continuity_state()
    if state is None:
        raise RuntimeError("bounded action continuity state was not persisted")
    return state
