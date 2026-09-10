"""Persistence for conversation topics and evidence-bounded world facts."""

from __future__ import annotations

import sqlite3
from typing import Iterable

from core.runtime.db_core import connect


_LEGACY_TOPIC_MIGRATION = "quarantine-runtime-world-model-conversation-topics-v1"


def upsert_conversation_topic(
    *,
    topic_id: str,
    canonical_key: str,
    title: str,
    summary: str,
    source_kind: str,
    session_id: str,
    run_id: str,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_conversation_topics_table(conn)
        conn.execute(
            """
            INSERT INTO conversation_topics (
                topic_id, canonical_key, title, summary, source_kind,
                session_id, run_id, support_count, session_count,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
            ON CONFLICT(canonical_key) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                source_kind = excluded.source_kind,
                session_count = conversation_topics.session_count + CASE
                    WHEN excluded.session_id != ''
                     AND excluded.session_id != conversation_topics.session_id THEN 1
                    ELSE 0
                END,
                session_id = excluded.session_id,
                run_id = excluded.run_id,
                support_count = conversation_topics.support_count + 1,
                updated_at = excluded.updated_at
            """,
            (
                topic_id,
                canonical_key,
                title,
                summary,
                source_kind,
                session_id,
                run_id,
                created_at,
                updated_at,
            ),
        )
        row = conn.execute(
            """
            SELECT topic_id, canonical_key, title, summary, source_kind,
                   session_id, run_id, support_count, session_count,
                   created_at, updated_at
            FROM conversation_topics
            WHERE canonical_key = ?
            """,
            (canonical_key,),
        ).fetchone()
    if row is None:
        raise RuntimeError("conversation topic was not persisted")
    return _conversation_topic_from_row(row)


def select_conversation_topics(*, limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_conversation_topics_table(conn)
        rows = conn.execute(
            """
            SELECT topic_id, canonical_key, title, summary, source_kind,
                   session_id, run_id, support_count, session_count,
                   created_at, updated_at
            FROM conversation_topics
            ORDER BY updated_at DESC, rowid DESC
            LIMIT ?
            """,
            (max(int(limit), 1),),
        ).fetchall()
    return [_conversation_topic_from_row(row) for row in rows]


def insert_world_fact(
    *,
    fact_id: str,
    canonical_key: str,
    statement: str,
    status: str,
    confidence: str,
    source_kind: str,
    source_ref: str,
    observed_at: str,
    valid_from: str,
    valid_until: str,
    contradicts_fact_id: str,
    supersedes_fact_id: str,
    evidence_count: int,
    distinct_source_count: int,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_world_facts_table(conn)
        conn.execute(
            """
            INSERT INTO runtime_world_facts (
                fact_id, canonical_key, statement, status, confidence,
                source_kind, source_ref, observed_at, valid_from, valid_until,
                contradicts_fact_id, supersedes_fact_id, evidence_count,
                distinct_source_count, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact_id,
                canonical_key,
                statement,
                status,
                confidence,
                source_kind,
                source_ref,
                observed_at,
                valid_from,
                valid_until,
                contradicts_fact_id,
                supersedes_fact_id,
                max(int(evidence_count), 1),
                max(int(distinct_source_count), 1),
                created_at,
                updated_at,
            ),
        )
        row = conn.execute(
            f"SELECT {_WORLD_FACT_COLUMNS} FROM runtime_world_facts WHERE fact_id = ?",
            (fact_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("world fact was not persisted")
    return _world_fact_from_row(row)


def select_world_facts(
    *,
    statuses: Iterable[str] | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    normalized_statuses = [str(status) for status in statuses or [] if str(status)]
    params: list[object] = []
    where = ""
    if normalized_statuses:
        placeholders = ", ".join("?" for _ in normalized_statuses)
        where = f"WHERE status IN ({placeholders})"
        params.extend(normalized_statuses)
    params.append(max(int(limit), 1))
    with connect() as conn:
        _ensure_runtime_world_facts_table(conn)
        rows = conn.execute(
            f"""
            SELECT {_WORLD_FACT_COLUMNS}
            FROM runtime_world_facts
            {where}
            ORDER BY CASE status
                WHEN 'verified' THEN 0
                WHEN 'observed' THEN 1
                WHEN 'reported' THEN 2
                WHEN 'contradicted' THEN 3
                WHEN 'stale' THEN 4
                WHEN 'superseded' THEN 5
                ELSE 6
            END,
            observed_at DESC,
            rowid DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [_world_fact_from_row(row) for row in rows]


def list_legacy_world_model_signals_excluding_topics(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Read the old signal store without allowing conversation topics through."""
    clauses = ["signal_type != 'conversational_context'"]
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    params.append(max(int(limit), 1))
    with connect() as conn:
        if not _table_exists(conn, "runtime_world_model_signals"):
            return []
        rows = conn.execute(
            f"""
            SELECT signal_id, signal_type, canonical_key, status, title,
                   summary, rationale, source_kind, confidence,
                   evidence_summary, support_summary, status_reason, run_id,
                   session_id, support_count, session_count, merge_count,
                   created_at, updated_at
            FROM runtime_world_model_signals
            WHERE {' AND '.join(clauses)}
            ORDER BY id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [_legacy_world_signal_from_row(row) for row in rows]


def quarantine_legacy_world_topics(batch_size: int = 200) -> dict[str, int]:
    """Quarantine at most ``batch_size`` old conversation-topic signal rows."""
    bounded_size = max(int(batch_size), 0)
    with connect() as conn:
        _ensure_world_self_truth_migrations_table(conn)
        migration = conn.execute(
            """
            SELECT cursor_id, completed_at
            FROM world_self_truth_migrations
            WHERE migration_key = ?
            """,
            (_LEGACY_TOPIC_MIGRATION,),
        ).fetchone()
        cursor_id = int(migration["cursor_id"] or 0) if migration else 0
        if migration is not None and str(migration["completed_at"] or ""):
            return {"quarantined": 0, "cursor_id": cursor_id, "completed": 1}
        if bounded_size == 0 or not _table_exists(conn, "runtime_world_model_signals"):
            return {"quarantined": 0, "cursor_id": cursor_id, "completed": 0}

        rows = conn.execute(
            """
            SELECT id
            FROM runtime_world_model_signals
            WHERE id > ?
              AND signal_type = 'conversational_context'
              AND status != 'legacy_quarantined'
            ORDER BY id ASC
            LIMIT ?
            """,
            (cursor_id, bounded_size),
        ).fetchall()
        ids = [int(row["id"]) for row in rows]
        if ids:
            placeholders = ", ".join("?" for _ in ids)
            conn.execute(
                f"""
                UPDATE runtime_world_model_signals
                SET status = 'legacy_quarantined'
                WHERE id IN ({placeholders})
                  AND signal_type = 'conversational_context'
                """,
                ids,
            )
            cursor_id = ids[-1]

        remaining = conn.execute(
            """
            SELECT 1
            FROM runtime_world_model_signals
            WHERE id > ?
              AND signal_type = 'conversational_context'
              AND status != 'legacy_quarantined'
            LIMIT 1
            """,
            (cursor_id,),
        ).fetchone()
        completed = int(remaining is None)
        now = _sqlite_now(conn)
        conn.execute(
            """
            INSERT INTO world_self_truth_migrations (
                migration_key, cursor_id, completed_at, updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(migration_key) DO UPDATE SET
                cursor_id = excluded.cursor_id,
                completed_at = excluded.completed_at,
                updated_at = excluded.updated_at
            """,
            (_LEGACY_TOPIC_MIGRATION, cursor_id, now if completed else "", now),
        )
    return {"quarantined": len(ids), "cursor_id": cursor_id, "completed": completed}


def _ensure_conversation_topics_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_topics (
            topic_id TEXT NOT NULL PRIMARY KEY,
            canonical_key TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def _ensure_runtime_world_facts_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_world_facts (
            fact_id TEXT NOT NULL PRIMARY KEY,
            canonical_key TEXT NOT NULL,
            statement TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_ref TEXT NOT NULL DEFAULT '',
            observed_at TEXT NOT NULL,
            valid_from TEXT NOT NULL DEFAULT '',
            valid_until TEXT NOT NULL DEFAULT '',
            contradicts_fact_id TEXT NOT NULL DEFAULT '',
            supersedes_fact_id TEXT NOT NULL DEFAULT '',
            evidence_count INTEGER NOT NULL DEFAULT 1,
            distinct_source_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_world_facts_status
        ON runtime_world_facts(status, observed_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_world_facts_canonical_key
        ON runtime_world_facts(canonical_key, observed_at DESC)
        """
    )


def _ensure_world_self_truth_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS world_self_truth_migrations (
            migration_key TEXT NOT NULL PRIMARY KEY,
            cursor_id INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
        """
    )


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def _sqlite_now(conn: sqlite3.Connection) -> str:
    return str(conn.execute("SELECT strftime('%Y-%m-%dT%H:%M:%fZ', 'now')").fetchone()[0])


def _conversation_topic_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "topic_id": row["topic_id"],
        "canonical_key": row["canonical_key"],
        "title": row["title"],
        "summary": row["summary"],
        "source_kind": row["source_kind"],
        "session_id": row["session_id"],
        "run_id": row["run_id"],
        "support_count": int(row["support_count"]),
        "session_count": int(row["session_count"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


_WORLD_FACT_COLUMNS = """
fact_id, canonical_key, statement, status, confidence, source_kind, source_ref,
observed_at, valid_from, valid_until, contradicts_fact_id, supersedes_fact_id,
evidence_count, distinct_source_count, created_at, updated_at
"""


def _world_fact_from_row(row: sqlite3.Row) -> dict[str, object]:
    result = {key: row[key] for key in row.keys()}
    result["evidence_count"] = int(row["evidence_count"])
    result["distinct_source_count"] = int(row["distinct_source_count"])
    return result


def _legacy_world_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    result = {key: row[key] for key in row.keys()}
    for key in ("support_count", "session_count", "merge_count"):
        result[key] = int(row[key] or 0)
    return result

