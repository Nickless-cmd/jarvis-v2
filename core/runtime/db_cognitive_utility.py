"""Persistence for the cognitive-domain utility caches.

Sub-split out of core/runtime/db_cognitive.py per the boy-scout rule (the parent
exceeded the 2000-line core-file limit). Owns the schema and CRUD for three
fully-independent utility tables — web_cache, session_topics and
daemon_output_log — each via a lazily-invoked `_ensure_*_table` helper called
only by its own CRUD (never by init_db), so the cluster is self-contained.

Re-exported from db_cognitive.py (and in turn from db.py) so existing imports
like `from core.runtime.db import web_cache_lookup` keep resolving unchanged.
"""
from __future__ import annotations

import logging as _logging
from datetime import UTC, datetime, timedelta

import sqlite3

from core.runtime.db_core import connect

# Same logger handle as db.py (`uvicorn.error`) — used by session_topic_accumulate
# for its best-effort DB-persist warning. Defined locally so the module stays
# self-contained (a plain logging.getLogger, not db.py runtime state).
_logger = _logging.getLogger("uvicorn.error")


def _ensure_web_cache_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS web_cache (
            cache_key TEXT PRIMARY KEY,
            query_raw TEXT NOT NULL,
            query_normalized TEXT NOT NULL,
            source_url TEXT,
            title TEXT,
            body TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            ttl_policy TEXT NOT NULL DEFAULT 'medium',
            hit_count INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_web_cache_expires ON web_cache(expires_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_web_cache_normalized ON web_cache(query_normalized)"
    )


def web_cache_store(
    *,
    conn: sqlite3.Connection,
    cache_key: str,
    query_raw: str,
    query_normalized: str,
    source_url: str,
    title: str,
    body: str,
    ttl_policy: str,
    expires_at: str,
) -> None:
    _ensure_web_cache_table(conn)
    conn.execute(
        """
        INSERT OR REPLACE INTO web_cache
            (cache_key, query_raw, query_normalized, source_url, title, body,
             fetched_at, expires_at, ttl_policy, hit_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            cache_key,
            query_raw,
            query_normalized,
            source_url or "",
            title or "",
            body,
            datetime.now(UTC).isoformat(),
            expires_at,
            ttl_policy,
        ),
    )
    conn.commit()


def web_cache_lookup(*, conn: sqlite3.Connection, cache_key: str) -> dict[str, object] | None:
    _ensure_web_cache_table(conn)
    now = datetime.now(UTC).isoformat()
    row = conn.execute(
        """
        SELECT cache_key, query_raw, query_normalized, source_url, title, body,
               fetched_at, expires_at, ttl_policy, hit_count
        FROM web_cache
        WHERE cache_key = ? AND expires_at > ?
        LIMIT 1
        """,
        (cache_key, now),
    ).fetchone()
    if row is None:
        return None
    new_count = int(row["hit_count"] or 0) + 1
    conn.execute(
        "UPDATE web_cache SET hit_count = ? WHERE cache_key = ?",
        (new_count, cache_key),
    )
    conn.commit()
    return {
        "cache_key": row["cache_key"],
        "query_raw": row["query_raw"],
        "query_normalized": row["query_normalized"],
        "source_url": row["source_url"],
        "title": row["title"],
        "body": row["body"],
        "fetched_at": row["fetched_at"],
        "expires_at": row["expires_at"],
        "ttl_policy": row["ttl_policy"],
        "hit_count": new_count,
    }


def web_cache_cleanup(*, conn: sqlite3.Connection) -> int:
    _ensure_web_cache_table(conn)
    now = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        "DELETE FROM web_cache WHERE expires_at < ?", (now,)
    )
    conn.commit()
    return cursor.rowcount


def _ensure_session_topics_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            topic_label TEXT NOT NULL,
            mention_count INTEGER NOT NULL DEFAULT 1,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            UNIQUE(session_id, topic_label)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_topics_session ON session_topics(session_id, last_seen DESC)"
    )
    # 2026-06-14 (Jarvis): migrate NULL mention_count → 0 for existing rows
    # that were created before the NOT NULL constraint was enforced.
    try:
        conn.execute("UPDATE session_topics SET mention_count = 0 WHERE mention_count IS NULL")
    except sqlite3.OperationalError:
        pass


def session_topic_accumulate(
    session_id: str,
    topic_label: str,
    mention_count: int = 1,
    first_seen: str = "",
    last_seen: str = "",
) -> None:
    """Upsert a topic for a session — merge if exists, insert if not.

    2026-06-14 (Jarvis): added int() coercion + try/except for robust DB
    persist. The UPDATE crashed with "int too large to convert to SQLITE
    INTEGER" when mention_count was NULL (migration edge case) or
    contained an overflow value from a previous bug.
    """
    try:
        with connect() as conn:
            _ensure_session_topics_table(conn)
            existing = conn.execute(
                "SELECT id, mention_count FROM session_topics WHERE session_id = ? AND topic_label = ?",
                (session_id, topic_label),
            ).fetchone()
            if existing:
                current = int(existing["mention_count"] or 0)
                new_count = current + int(mention_count)
                conn.execute(
                    "UPDATE session_topics SET mention_count = ?, last_seen = ? WHERE id = ?",
                    (new_count, last_seen, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO session_topics (session_id, topic_label, mention_count, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)",
                    (session_id, topic_label, int(mention_count), first_seen or last_seen, last_seen),
                )
            conn.commit()
    except Exception as exc:
        _logger.warning(
            "session_topic_accumulate: DB persist failed for session=%s topic=%s — %s",
            session_id, topic_label, exc,
        )


def session_topics_for_session(session_id: str) -> list[dict[str, object]]:
    """Return all accumulated topics for a session, ordered by mention_count DESC."""
    with connect() as conn:
        _ensure_session_topics_table(conn)
        rows = conn.execute(
            "SELECT * FROM session_topics WHERE session_id = ? ORDER BY mention_count DESC, last_seen DESC",
            (session_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "topic_label": r["topic_label"],
                "mention_count": r["mention_count"],
                "first_seen": r["first_seen"],
                "last_seen": r["last_seen"],
            }
            for r in rows
        ]


def session_topic_cleanup(max_age_days: int = 90) -> int:
    """Delete session topics not seen for max_age_days."""
    with connect() as conn:
        _ensure_session_topics_table(conn)
        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        cursor = conn.execute("DELETE FROM session_topics WHERE last_seen < ?", (cutoff,))
        conn.commit()
        return cursor.rowcount


def _ensure_daemon_output_log_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daemon_output_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daemon_name TEXT NOT NULL,
            raw_llm_output TEXT NOT NULL DEFAULT '',
            parsed_result TEXT NOT NULL DEFAULT '',
            success INTEGER NOT NULL DEFAULT 0,
            provider TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_daemon_output_log_name_created ON daemon_output_log(daemon_name, created_at DESC)"
    )


def daemon_output_log_insert(
    *,
    daemon_name: str,
    raw_llm_output: str,
    parsed_result: str,
    success: bool,
    provider: str = "",
) -> None:
    with connect() as conn:
        _ensure_daemon_output_log_table(conn)
        conn.execute(
            """
            INSERT INTO daemon_output_log (daemon_name, raw_llm_output, parsed_result, success, provider, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                daemon_name,
                raw_llm_output[:2000],
                parsed_result[:500],
                1 if success else 0,
                provider,
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()


def daemon_output_log_recent(daemon_name: str = "", limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_daemon_output_log_table(conn)
        if daemon_name:
            rows = conn.execute(
                "SELECT * FROM daemon_output_log WHERE daemon_name = ? ORDER BY created_at DESC LIMIT ?",
                (daemon_name, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM daemon_output_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [
        {
            "id": r["id"],
            "daemon_name": r["daemon_name"],
            "raw_llm_output": r["raw_llm_output"],
            "parsed_result": r["parsed_result"],
            "success": bool(r["success"]),
            "provider": r["provider"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def daemon_output_log_cleanup(max_age_days: int = 7) -> int:
    with connect() as conn:
        _ensure_daemon_output_log_table(conn)
        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        cursor = conn.execute(
            "DELETE FROM daemon_output_log WHERE created_at < ?", (cutoff,)
        )
        conn.commit()
        return cursor.rowcount
