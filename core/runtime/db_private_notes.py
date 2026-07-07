"""Persistence for the private/protected inner-layer note tables.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
`private_inner_notes`, `private_growth_notes` and `protected_inner_voices`
(ensure_private_notes_tables + the additive column-migration helpers) plus
their record/update/recent CRUD.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def ensure_private_notes_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS private_inner_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            work_id TEXT NOT NULL,
            status TEXT NOT NULL,
            note_kind TEXT NOT NULL DEFAULT '',
            focus TEXT NOT NULL DEFAULT '',
            uncertainty TEXT NOT NULL DEFAULT '',
            identity_alignment TEXT NOT NULL DEFAULT '',
            work_signal TEXT NOT NULL DEFAULT '',
            private_summary TEXT NOT NULL,
            created_at TEXT NOT NULL,
            enriched INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS private_growth_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            work_id TEXT NOT NULL,
            learning_kind TEXT NOT NULL,
            lesson TEXT NOT NULL,
            mistake_signal TEXT NOT NULL DEFAULT '',
            helpful_signal TEXT NOT NULL DEFAULT '',
            identity_signal TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            enriched INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS protected_inner_voices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voice_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            work_id TEXT NOT NULL,
            mood_tone TEXT NOT NULL,
            self_position TEXT NOT NULL,
            current_concern TEXT NOT NULL,
            current_pull TEXT NOT NULL,
            voice_line TEXT NOT NULL,
            created_at TEXT NOT NULL,
            enriched INTEGER NOT NULL DEFAULT 0
        )
        """
    )


def _ensure_private_inner_note_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(private_inner_notes)").fetchall()
    existing = {str(row["name"]) for row in rows}
    required_columns = {
        "note_kind": "TEXT NOT NULL DEFAULT ''",
        "focus": "TEXT NOT NULL DEFAULT ''",
        "uncertainty": "TEXT NOT NULL DEFAULT ''",
        "identity_alignment": "TEXT NOT NULL DEFAULT ''",
        "work_signal": "TEXT NOT NULL DEFAULT ''",
    }
    for name, spec in required_columns.items():
        if name in existing:
            continue
        conn.execute(f"ALTER TABLE private_inner_notes ADD COLUMN {name} {spec}")


def _ensure_enriched_columns(conn: sqlite3.Connection) -> None:
    """Add enriched column to private layer tables if missing."""
    for table in ("private_inner_notes", "private_growth_notes", "protected_inner_voices"):
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row["name"]) for row in rows}
        if "enriched" not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN enriched INTEGER NOT NULL DEFAULT 0")


def record_private_inner_note(
    *,
    note_id: str,
    source: str,
    run_id: str,
    work_id: str,
    status: str,
    note_kind: str,
    focus: str,
    uncertainty: str,
    identity_alignment: str,
    work_signal: str,
    private_summary: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_inner_notes (
                note_id, source, run_id, work_id, status, note_kind, focus,
                uncertainty, identity_alignment, work_signal, private_summary, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                note_id=excluded.note_id,
                source=excluded.source,
                work_id=excluded.work_id,
                status=excluded.status,
                note_kind=excluded.note_kind,
                focus=excluded.focus,
                uncertainty=excluded.uncertainty,
                identity_alignment=excluded.identity_alignment,
                work_signal=excluded.work_signal,
                private_summary=excluded.private_summary,
                created_at=excluded.created_at
            """,
            (
                note_id,
                source,
                run_id,
                work_id,
                status,
                note_kind,
                focus,
                uncertainty,
                identity_alignment,
                work_signal,
                private_summary,
                created_at,
            ),
        )
        conn.commit()


def update_private_inner_note_enriched(*, run_id: str, enriched_summary: str) -> None:
    """Replace template summary with LLM-enriched text."""
    with connect() as conn:
        conn.execute(
            "UPDATE private_inner_notes SET private_summary = ?, enriched = 1 WHERE run_id = ?",
            (enriched_summary, run_id),
        )
        conn.commit()


def recent_private_inner_notes(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                note_id,
                source,
                run_id,
                work_id,
                status,
                note_kind,
                focus,
                uncertainty,
                identity_alignment,
                work_signal,
                private_summary,
                created_at
            FROM private_inner_notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "note_id": row["note_id"],
            "source": row["source"],
            "run_id": row["run_id"],
            "work_id": row["work_id"],
            "status": row["status"],
            "note_kind": row["note_kind"],
            "focus": row["focus"],
            "uncertainty": row["uncertainty"],
            "identity_alignment": row["identity_alignment"],
            "work_signal": row["work_signal"],
            "private_summary": row["private_summary"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def record_private_growth_note(
    *,
    record_id: str,
    source: str,
    run_id: str,
    work_id: str,
    learning_kind: str,
    lesson: str,
    mistake_signal: str,
    helpful_signal: str,
    identity_signal: str,
    confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_growth_notes (
                record_id, source, run_id, work_id, learning_kind, lesson,
                mistake_signal, helpful_signal, identity_signal, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                record_id=excluded.record_id,
                source=excluded.source,
                work_id=excluded.work_id,
                learning_kind=excluded.learning_kind,
                lesson=excluded.lesson,
                mistake_signal=excluded.mistake_signal,
                helpful_signal=excluded.helpful_signal,
                identity_signal=excluded.identity_signal,
                confidence=excluded.confidence,
                created_at=excluded.created_at
            """,
            (
                record_id,
                source,
                run_id,
                work_id,
                learning_kind,
                lesson,
                mistake_signal,
                helpful_signal,
                identity_signal,
                confidence,
                created_at,
            ),
        )
        conn.commit()


def update_private_growth_note_enriched(
    *, run_id: str, enriched_lesson: str, enriched_helpful_signal: str
) -> None:
    """Replace template lesson and helpful_signal with LLM-enriched text."""
    with connect() as conn:
        conn.execute(
            "UPDATE private_growth_notes SET lesson = ?, helpful_signal = ?, enriched = 1 WHERE run_id = ?",
            (enriched_lesson, enriched_helpful_signal, run_id),
        )
        conn.commit()


def recent_private_growth_notes(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                record_id,
                source,
                run_id,
                work_id,
                learning_kind,
                lesson,
                mistake_signal,
                helpful_signal,
                identity_signal,
                confidence,
                created_at
            FROM private_growth_notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "record_id": row["record_id"],
            "source": row["source"],
            "run_id": row["run_id"],
            "work_id": row["work_id"],
            "learning_kind": row["learning_kind"],
            "lesson": row["lesson"],
            "mistake_signal": row["mistake_signal"],
            "helpful_signal": row["helpful_signal"],
            "identity_signal": row["identity_signal"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def record_protected_inner_voice(
    *,
    voice_id: str,
    source: str,
    run_id: str,
    work_id: str,
    mood_tone: str,
    self_position: str,
    current_concern: str,
    current_pull: str,
    voice_line: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO protected_inner_voices (
                voice_id, source, run_id, work_id, mood_tone, self_position,
                current_concern, current_pull, voice_line, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                voice_id=excluded.voice_id,
                source=excluded.source,
                work_id=excluded.work_id,
                mood_tone=excluded.mood_tone,
                self_position=excluded.self_position,
                current_concern=excluded.current_concern,
                current_pull=excluded.current_pull,
                voice_line=excluded.voice_line,
                created_at=excluded.created_at
            """,
            (
                voice_id,
                source,
                run_id,
                work_id,
                mood_tone,
                self_position,
                current_concern,
                current_pull,
                voice_line,
                created_at,
            ),
        )
        conn.commit()


def update_protected_inner_voice_enriched(*, run_id: str, enriched_voice_line: str) -> None:
    """Replace template voice_line with LLM-enriched text."""
    with connect() as conn:
        conn.execute(
            "UPDATE protected_inner_voices SET voice_line = ?, enriched = 1 WHERE run_id = ?",
            (enriched_voice_line, run_id),
        )
        conn.commit()


def get_protected_inner_voice() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                voice_id,
                source,
                run_id,
                work_id,
                mood_tone,
                self_position,
                current_concern,
                current_pull,
                voice_line,
                created_at
            FROM protected_inner_voices
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "voice_id": row["voice_id"],
        "source": row["source"],
        "run_id": row["run_id"],
        "work_id": row["work_id"],
        "mood_tone": row["mood_tone"],
        "self_position": row["self_position"],
        "current_concern": row["current_concern"],
        "current_pull": row["current_pull"],
        "voice_line": row["voice_line"],
        "created_at": row["created_at"],
    }


def list_recent_protected_inner_voices(*, limit: int = 8) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                voice_id,
                source,
                run_id,
                work_id,
                mood_tone,
                self_position,
                current_concern,
                current_pull,
                voice_line,
                created_at,
                enriched
            FROM protected_inner_voices
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(int(limit), 1),),
        ).fetchall()
    items: list[dict[str, object]] = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "voice_id": row["voice_id"],
                "source": row["source"],
                "run_id": row["run_id"],
                "work_id": row["work_id"],
                "mood_tone": row["mood_tone"],
                "self_position": row["self_position"],
                "current_concern": row["current_concern"],
                "current_pull": row["current_pull"],
                "voice_line": row["voice_line"],
                "created_at": row["created_at"],
                "enriched": bool(row["enriched"]),
            }
        )
    return items
