"""DB helpers for user_contradictions + user_statements tables.

Split out from db.py per CLAUDE.md boy scout rule.
Re-exported from core.runtime.db for backwards compatibility.

Design:
- user_statements: gemmer statements/claims brugeren har sagt,
  med topic-kategorisering for semantisk sammenligning.
- user_contradictions: gemmer fundne modsigelser mellem to statements.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from core.runtime.db import connect, _now_iso


def _ensure_user_contradiction_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            statement_id TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL DEFAULT 'bjørn',
            text TEXT NOT NULL,
            topic TEXT NOT NULL DEFAULT 'general',
            session_id TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'chat',
            support_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_statements_lookup
        ON user_statements(user_id, topic, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_contradictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contradiction_id TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL DEFAULT 'bjørn',
            statement_a_id TEXT NOT NULL DEFAULT '',
            statement_a_text TEXT NOT NULL,
            statement_a_source TEXT NOT NULL DEFAULT '',
            statement_a_created_at TEXT NOT NULL DEFAULT '',
            statement_b_text TEXT NOT NULL,
            statement_b_source TEXT NOT NULL DEFAULT '',
            statement_b_created_at TEXT NOT NULL,
            topic TEXT NOT NULL DEFAULT 'general',
            overlap_tokens TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_contradictions_lookup
        ON user_contradictions(user_id, topic, status, created_at DESC)
        """
    )


def upsert_user_statement(
    *,
    statement_id: str,
    user_id: str,
    text: str,
    topic: str,
    session_id: str,
    source: str,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    """Gem eller opdater et user statement.

    Hvis et statement med samme tekst+user_id+topic findes,
    opdateres det eksisterende (support_count += 1).
    """
    with connect() as conn:
        _ensure_user_contradiction_tables(conn)
        existing = conn.execute(
            """
            SELECT statement_id, support_count, created_at
            FROM user_statements
            WHERE user_id = ?
              AND topic = ?
              AND LOWER(text) = LOWER(?)
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, topic, text),
        ).fetchone()

        if existing is not None:
            resolved_id = str(existing["statement_id"])
            merged_count = int(existing["support_count"] or 0) + 1
            conn.execute(
                """
                UPDATE user_statements
                SET support_count = ?,
                    session_id = ?,
                    source = ?,
                    updated_at = ?
                WHERE statement_id = ?
                """,
                (merged_count, session_id, source, updated_at, resolved_id),
            )
            conn.commit()
            return {
                "statement_id": resolved_id,
                "was_created": False,
                "was_updated": True,
                "support_count": merged_count,
            }

        conn.execute(
            """
            INSERT INTO user_statements
                (statement_id, user_id, text, topic, session_id, source,
                 support_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                statement_id,
                user_id,
                text,
                topic,
                session_id,
                source,
                1,
                created_at,
                updated_at,
            ),
        )
        conn.commit()
        return {"statement_id": statement_id, "was_created": True, "was_updated": True}


def get_user_statement_by_text(
    *,
    text: str,
    user_id: str = "bjørn",
    topic: str = "general",
) -> dict[str, object] | None:
    """Find et eksisterende statement med samme tekst (case-insensitive)."""
    with connect() as conn:
        _ensure_user_contradiction_tables(conn)
        row = conn.execute(
            """
            SELECT statement_id, user_id, text, topic, support_count,
                   created_at, updated_at
            FROM user_statements
            WHERE user_id = ?
              AND topic = ?
              AND LOWER(text) = LOWER(?)
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, topic, text),
        ).fetchone()
        if row is None:
            return None
        return dict(row)


def list_user_statements(
    *,
    user_id: str = "bjørn",
    topic: str = "",
    limit: int = 50,
) -> list[dict[str, object]]:
    """Hent statements for en bruger, filtreret på topic hvis angivet."""
    with connect() as conn:
        _ensure_user_contradiction_tables(conn)
        if topic:
            rows = conn.execute(
                """
                SELECT statement_id, user_id, text, topic, support_count,
                       created_at, updated_at
                FROM user_statements
                WHERE user_id = ? AND topic = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, topic, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT statement_id, user_id, text, topic, support_count,
                       created_at, updated_at
                FROM user_statements
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]


def insert_user_contradiction(
    *,
    contradiction_id: str,
    user_id: str,
    statement_a_id: str,
    statement_a_text: str,
    statement_a_source: str,
    statement_a_created_at: str,
    statement_b_text: str,
    statement_b_source: str,
    statement_b_created_at: str,
    topic: str,
    overlap_tokens: str,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    """Gem en fundet bruger-modsigelse."""
    with connect() as conn:
        _ensure_user_contradiction_tables(conn)
        conn.execute(
            """
            INSERT INTO user_contradictions
                (contradiction_id, user_id, statement_a_id,
                 statement_a_text, statement_a_source, statement_a_created_at,
                 statement_b_text, statement_b_source, statement_b_created_at,
                 topic, overlap_tokens, status, notes,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contradiction_id,
                user_id,
                statement_a_id,
                statement_a_text[:1000],
                statement_a_source,
                statement_a_created_at,
                statement_b_text[:1000],
                statement_b_source,
                statement_b_created_at,
                topic,
                overlap_tokens,
                "active",
                "",
                created_at,
                updated_at,
            ),
        )
        conn.commit()
        return {"contradiction_id": contradiction_id, "was_created": True}


def list_user_contradictions(
    *,
    user_id: str = "bjørn",
    topic: str = "",
    limit: int = 10,
    status: str = "active",
) -> list[dict[str, object]]:
    """Hent lagrede modsigelser for en bruger."""
    with connect() as conn:
        _ensure_user_contradiction_tables(conn)
        if topic:
            rows = conn.execute(
                """
                SELECT contradiction_id, user_id,
                       statement_a_id, statement_a_text, statement_a_source,
                       statement_a_created_at,
                       statement_b_text, statement_b_source,
                       statement_b_created_at,
                       topic, overlap_tokens, status, notes,
                       created_at, updated_at
                FROM user_contradictions
                WHERE user_id = ? AND topic = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, topic, status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT contradiction_id, user_id,
                       statement_a_id, statement_a_text, statement_a_source,
                       statement_a_created_at,
                       statement_b_text, statement_b_source,
                       statement_b_created_at,
                       topic, overlap_tokens, status, notes,
                       created_at, updated_at
                FROM user_contradictions
                WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, status, limit),
            ).fetchall()
        return [dict(r) for r in rows]


def update_user_contradiction_status(
    *,
    contradiction_id: str,
    status: str,
    notes: str = "",
    updated_at: str | None = None,
) -> dict[str, object] | None:
    """Opdater status på en modsigelse (fx 'resolved' eller 'dismissed')."""
    now = updated_at or _now_iso()
    with connect() as conn:
        _ensure_user_contradiction_tables(conn)
        conn.execute(
            """
            UPDATE user_contradictions
            SET status = ?, notes = ?, updated_at = ?
            WHERE contradiction_id = ?
            """,
            (status, notes, now, contradiction_id),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT contradiction_id, user_id, status, notes, updated_at
            FROM user_contradictions
            WHERE contradiction_id = ?
            """,
            (contradiction_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)
