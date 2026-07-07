"""Persistence for small self-contained runtime CRUD domains.

Split out of core/runtime/db.py per the boy-scout rule. Each domain below owns
its table via a lazy `_ensure_*_table` helper that init_db does NOT call (init_db
keeps the service-owned schema layer, but these tables are created on-demand by
their own CRUD) — so the ensure helpers move here with the domain:

- cached affective state
- experiment settings
- experiment recurrence iterations
- experiment broadcast events
- experiment meta-cognition records
- experiment attention-blink results
- session summaries
- signal archive (uses `_SIGNAL_TABLES_WITH_STATUS` from db_core)
- aesthetic motif log
- channel attachments

Plus two cognitive-adjacent readers left behind in batch 5 because they
cross-reference helpers now living in db_cognitive.py — they lazy-import those
helpers in-body:

- `get_relevant_experiential_memories` → `_ensure_cognitive_experiential_memories_table`
- `list_session_distillation_records` → `_ensure_session_distillation_records_table`
  and `_session_distillation_record_from_row` (the latter still lives in db.py).
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from core.runtime.db_core import (
    _SIGNAL_TABLES_WITH_STATUS,
    _now_iso,
    connect,
)


# ---------------------------------------------------------------------------
# Cognitive leftovers (batch-5 carry-over; cross-reference db_cognitive helpers)
# ---------------------------------------------------------------------------


def get_relevant_experiential_memories(
    *, context: str, limit: int = 3
) -> list[dict[str, object]]:
    """Find experiential memories relevant to the given context."""
    from core.runtime.db_cognitive import _ensure_cognitive_experiential_memories_table
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        rows = conn.execute(
            """SELECT * FROM cognitive_experiential_memories
               WHERE decay_score < 0.9
               ORDER BY importance DESC, reinforcement_count DESC, created_at DESC
               LIMIT ?""",
            (limit * 3,),
        ).fetchall()
    if not rows:
        return []
    context_lower = context.lower()
    context_words = set(w for w in context_lower.split() if len(w) > 3)
    scored = []
    for r in rows:
        text = f"{r['narrative']} {r['topic']} {r['key_lesson']}".lower()
        overlap = sum(1 for w in context_words if w in text)
        score = overlap * 0.3 + float(r["importance"]) * 0.4 + float(r["reinforcement_count"]) * 0.1
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "memory_id": r["memory_id"],
            "narrative": r["narrative"],
            "user_mood": r["user_mood"],
            "key_lesson": r["key_lesson"],
            "topic": r["topic"],
            "importance": float(r["importance"]),
            "decay_score": float(r["decay_score"]),
            "reinforcement_count": int(r["reinforcement_count"]),
            "created_at": r["created_at"],
        }
        for _, r in scored[:limit]
    ]


def list_session_distillation_records(
    *, limit: int = 10, session_id: str | None = None,
) -> list[dict[str, object]]:
    from core.runtime.db import _session_distillation_record_from_row
    from core.runtime.db_cognitive import _ensure_session_distillation_records_table
    with connect() as conn:
        _ensure_session_distillation_records_table(conn)
        if session_id:
            rows = conn.execute(
                "SELECT * FROM session_distillation_records WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM session_distillation_records ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [_session_distillation_record_from_row(row) for row in rows]


# ---------------------------------------------------------------------------
# Cached affective state
# ---------------------------------------------------------------------------


def _ensure_cached_affective_state_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cached_affective_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rendered_text TEXT NOT NULL,
            signals_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def save_cached_affective_state(rendered_text: str, signals_json: str) -> None:
    now = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_cached_affective_state_table(conn)
        conn.execute(
            "INSERT INTO cached_affective_state (rendered_text, signals_json, created_at) VALUES (?, ?, ?)",
            (rendered_text, signals_json, now),
        )
        conn.commit()


def get_cached_affective_state(max_age_seconds: int = 300) -> str | None:
    from datetime import timedelta
    cutoff = (datetime.now(UTC) - timedelta(seconds=max_age_seconds)).isoformat()
    with connect() as conn:
        _ensure_cached_affective_state_table(conn)
        row = conn.execute(
            """
            SELECT rendered_text FROM cached_affective_state
            WHERE created_at >= ?
            ORDER BY id DESC LIMIT 1
            """,
            (cutoff,),
        ).fetchone()
    return str(row["rendered_text"]) if row else None


# ---------------------------------------------------------------------------
# Experiment Settings
# ---------------------------------------------------------------------------

def _ensure_experiment_settings_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_settings (
               experiment_id TEXT PRIMARY KEY,
               enabled INTEGER NOT NULL DEFAULT 1,
               updated_at TEXT NOT NULL
           )"""
    )


def get_experiment_enabled(experiment_id: str) -> bool:
    """Return True if experiment is enabled. Defaults to True if no row exists."""
    with connect() as conn:
        _ensure_experiment_settings_table(conn)
        row = conn.execute(
            "SELECT enabled FROM experiment_settings WHERE experiment_id = ?",
            (experiment_id,),
        ).fetchone()
    if row is None:
        return True
    return bool(row["enabled"])


def set_experiment_enabled(experiment_id: str, enabled: bool) -> None:
    """Enable or disable an experiment. Creates row if absent."""
    now = _now_iso()
    with connect() as conn:
        _ensure_experiment_settings_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_settings
               (experiment_id, enabled, updated_at) VALUES (?, ?, ?)""",
            (experiment_id, 1 if enabled else 0, now),
        )


# ---------------------------------------------------------------------------
# Experiment 1: Recurrence Loop
# ---------------------------------------------------------------------------

def _ensure_recurrence_iterations_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_recurrence_iterations (
               iteration_id TEXT PRIMARY KEY,
               content TEXT NOT NULL,
               keywords TEXT NOT NULL,
               stability_score REAL NOT NULL DEFAULT 0.0,
               iteration_number INTEGER NOT NULL DEFAULT 1,
               created_at TEXT NOT NULL
           )"""
    )


def insert_recurrence_iteration(
    *,
    iteration_id: str,
    content: str,
    keywords: str,
    stability_score: float,
    iteration_number: int,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_recurrence_iterations_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_recurrence_iterations
               (iteration_id, content, keywords, stability_score, iteration_number, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (iteration_id, content[:500], keywords, stability_score, iteration_number, now),
        )


def get_latest_recurrence_iteration() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_recurrence_iterations_table(conn)
        row = conn.execute(
            """SELECT * FROM experiment_recurrence_iterations
               ORDER BY created_at DESC LIMIT 1"""
        ).fetchone()
    if not row:
        return None
    return {
        "iteration_id": str(row["iteration_id"]),
        "content": str(row["content"]),
        "keywords": str(row["keywords"]),
        "stability_score": float(row["stability_score"]),
        "iteration_number": int(row["iteration_number"]),
        "created_at": str(row["created_at"]),
    }


def list_recurrence_iterations(limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_recurrence_iterations_table(conn)
        rows = conn.execute(
            """SELECT * FROM experiment_recurrence_iterations
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "iteration_id": str(r["iteration_id"]),
            "content": str(r["content"]),
            "keywords": str(r["keywords"]),
            "stability_score": float(r["stability_score"]),
            "iteration_number": int(r["iteration_number"]),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Experiment 3: Global Workspace Broadcast Events
# ---------------------------------------------------------------------------

def _ensure_broadcast_events_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_broadcast_events (
               event_id TEXT PRIMARY KEY,
               topic_cluster TEXT NOT NULL,
               sources TEXT NOT NULL,
               source_count INTEGER NOT NULL,
               payload_summary TEXT NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )


def insert_broadcast_event(
    *,
    event_id: str,
    topic_cluster: str,
    sources: str,
    source_count: int,
    payload_summary: str,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_broadcast_events_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_broadcast_events
               (event_id, topic_cluster, sources, source_count, payload_summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (event_id, topic_cluster, sources, source_count, payload_summary[:300], now),
        )


def list_broadcast_events(limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_broadcast_events_table(conn)
        rows = conn.execute(
            """SELECT * FROM experiment_broadcast_events
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "event_id": str(r["event_id"]),
            "topic_cluster": str(r["topic_cluster"]),
            "sources": str(r["sources"]),
            "source_count": int(r["source_count"]),
            "payload_summary": str(r["payload_summary"]),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Experiment 4: Meta-Cognition Records
# ---------------------------------------------------------------------------

def _ensure_meta_cognition_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_meta_cognition_records (
               record_id TEXT PRIMARY KEY,
               meta_observation TEXT NOT NULL,
               meta_meta_observation TEXT NOT NULL,
               meta_depth INTEGER NOT NULL DEFAULT 1,
               input_state_summary TEXT NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )


def insert_meta_cognition_record(
    *,
    record_id: str,
    meta_observation: str,
    meta_meta_observation: str,
    meta_depth: int,
    input_state_summary: str,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_meta_cognition_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_meta_cognition_records
               (record_id, meta_observation, meta_meta_observation, meta_depth, input_state_summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (record_id, meta_observation[:1000], meta_meta_observation[:500], meta_depth, input_state_summary[:200], now),
        )


def list_meta_cognition_records(limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_meta_cognition_table(conn)
        rows = conn.execute(
            """SELECT * FROM experiment_meta_cognition_records
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "record_id": str(r["record_id"]),
            "meta_observation": str(r["meta_observation"]),
            "meta_meta_observation": str(r["meta_meta_observation"]),
            "meta_depth": int(r["meta_depth"]),
            "input_state_summary": str(r["input_state_summary"]),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Experiment 5: Attention Blink Results
# ---------------------------------------------------------------------------

def _ensure_attention_blink_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_attention_blink_results (
               test_id TEXT PRIMARY KEY,
               t1_baseline TEXT NOT NULL,
               t1_response TEXT NOT NULL,
               t2_response TEXT NOT NULL,
               blink_ratio REAL NOT NULL,
               interpretation TEXT NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )


def insert_attention_blink_result(
    *,
    test_id: str,
    t1_baseline: str,
    t1_response: str,
    t2_response: str,
    blink_ratio: float,
    interpretation: str,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_attention_blink_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_attention_blink_results
               (test_id, t1_baseline, t1_response, t2_response, blink_ratio, interpretation, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (test_id, t1_baseline, t1_response, t2_response, blink_ratio, interpretation, now),
        )


def list_attention_blink_results(limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_attention_blink_table(conn)
        rows = conn.execute(
            """SELECT * FROM experiment_attention_blink_results
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "test_id": str(r["test_id"]),
            "t1_baseline": str(r["t1_baseline"]),
            "t1_response": str(r["t1_response"]),
            "t2_response": str(r["t2_response"]),
            "blink_ratio": float(r["blink_ratio"]),
            "interpretation": str(r["interpretation"]),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Session summaries — LLM-generated conversation summaries for continuity
# ---------------------------------------------------------------------------


def _ensure_session_summaries_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            run_id TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL,
            key_topics TEXT NOT NULL DEFAULT '',
            decisions_made TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_summaries_session ON session_summaries(session_id, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_summaries_created ON session_summaries(created_at DESC)"
    )


def session_summary_insert(
    *,
    session_id: str,
    run_id: str = "",
    summary: str,
    key_topics: str = "",
    decisions_made: str = "",
) -> None:
    with connect() as conn:
        _ensure_session_summaries_table(conn)
        conn.execute(
            """
            INSERT INTO session_summaries (session_id, run_id, summary, key_topics, decisions_made, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, run_id, summary[:2000], key_topics[:500], decisions_made[:500], datetime.now(UTC).isoformat()),
        )
        conn.commit()


def session_summary_recent(limit: int = 3) -> list[dict[str, object]]:
    """Return the most recent session summaries (across all sessions)."""
    with connect() as conn:
        _ensure_session_summaries_table(conn)
        rows = conn.execute(
            "SELECT * FROM session_summaries ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "session_id": r["session_id"],
            "run_id": r["run_id"],
            "summary": r["summary"],
            "key_topics": r["key_topics"],
            "decisions_made": r["decisions_made"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def session_summary_for_session(session_id: str) -> dict[str, object] | None:
    """Return the latest summary for a specific session."""
    with connect() as conn:
        _ensure_session_summaries_table(conn)
        row = conn.execute(
            "SELECT * FROM session_summaries WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "run_id": row["run_id"],
        "summary": row["summary"],
        "key_topics": row["key_topics"],
        "decisions_made": row["decisions_made"],
        "created_at": row["created_at"],
    }


def session_summary_cleanup(max_age_days: int = 90) -> int:
    """Delete session summaries older than max_age_days."""
    with connect() as conn:
        _ensure_session_summaries_table(conn)
        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        cursor = conn.execute("DELETE FROM session_summaries WHERE created_at < ?", (cutoff,))
        conn.commit()
        return cursor.rowcount


# ---------------------------------------------------------------------------
# Signal archive — stores signals before decay-deletion for debugging
# ---------------------------------------------------------------------------


def _ensure_signal_archive_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS signal_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_table TEXT NOT NULL,
            signal_id TEXT NOT NULL,
            signal_type TEXT NOT NULL DEFAULT '',
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            archived_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_signal_archive_source ON signal_archive(source_table, archived_at DESC)"
    )


def signal_decay_archive_and_delete(*, stale_hours: int = 24) -> dict[str, int]:
    """Archive and delete signals marked stale for longer than stale_hours.

    Returns {"archived": N, "tables_scanned": M, "per_table": {table: count}}.
    """
    now = datetime.now(UTC)
    cutoff = (now - timedelta(hours=stale_hours)).isoformat()
    now_iso = now.isoformat()
    total_archived = 0
    per_table: dict[str, int] = {}

    with connect() as conn:
        _ensure_signal_archive_table(conn)
        for table in _SIGNAL_TABLES_WITH_STATUS:
            try:
                # Find stale signals updated before the cutoff
                rows = conn.execute(
                    f"SELECT * FROM {table} WHERE status = 'stale' AND updated_at < ?",  # noqa: S608
                    (cutoff,),
                ).fetchall()
                if not rows:
                    continue
                count = 0
                for row in rows:
                    conn.execute(
                        """
                        INSERT INTO signal_archive
                            (source_table, signal_id, signal_type, canonical_key, status,
                             title, summary, status_reason, created_at, updated_at, archived_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            table,
                            str(row["signal_id"]),
                            str(row["signal_type"] if "signal_type" in row.keys() else ""),
                            str(row["canonical_key"] if "canonical_key" in row.keys() else ""),
                            str(row["status"]),
                            str(row["title"] if "title" in row.keys() else ""),
                            str(row["summary"] if "summary" in row.keys() else ""),
                            str(row["status_reason"] if "status_reason" in row.keys() else ""),
                            str(row["created_at"] if "created_at" in row.keys() else ""),
                            str(row["updated_at"] if "updated_at" in row.keys() else ""),
                            now_iso,
                        ),
                    )
                    conn.execute(
                        f"DELETE FROM {table} WHERE signal_id = ?",  # noqa: S608
                        (str(row["signal_id"]),),
                    )
                    count += 1
                per_table[table] = count
                total_archived += count
            except Exception:
                # Table may not exist yet — skip silently
                continue
        conn.commit()

    return {
        "archived": total_archived,
        "tables_scanned": len(_SIGNAL_TABLES_WITH_STATUS),
        "per_table": per_table,
    }


def signal_archive_cleanup(max_age_days: int = 30) -> int:
    """Delete archived signals older than max_age_days."""
    with connect() as conn:
        _ensure_signal_archive_table(conn)
        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        cursor = conn.execute("DELETE FROM signal_archive WHERE archived_at < ?", (cutoff,))
        conn.commit()
        return cursor.rowcount


def signal_archive_recent(limit: int = 50) -> list[dict[str, object]]:
    """Return recent archived signals for debugging."""
    with connect() as conn:
        _ensure_signal_archive_table(conn)
        rows = conn.execute(
            "SELECT * FROM signal_archive ORDER BY archived_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {col: row[col] for col in row.keys()}
        for row in rows
    ]


# ---------------------------------------------------------------------------
# aesthetic_motif_log — accumulated aesthetic motifs from daemon text output
# ---------------------------------------------------------------------------


def _ensure_aesthetic_motif_log_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS aesthetic_motif_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            motif TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_aesthetic_motif_log_motif ON aesthetic_motif_log(motif)"
    )


def aesthetic_motif_log_insert(
    *,
    source: str,
    motif: str,
    confidence: float,
) -> None:
    with connect() as conn:
        _ensure_aesthetic_motif_log_table(conn)
        conn.execute(
            """
            INSERT INTO aesthetic_motif_log (source, motif, confidence, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (source, motif, confidence, datetime.now(UTC).isoformat()),
        )
        conn.commit()


def aesthetic_motif_log_unique_motifs() -> list[str]:
    with connect() as conn:
        _ensure_aesthetic_motif_log_table(conn)
        rows = conn.execute(
            "SELECT DISTINCT motif FROM aesthetic_motif_log ORDER BY motif"
        ).fetchall()
        return [row[0] for row in rows]


def aesthetic_motif_log_summary() -> list[dict]:
    with connect() as conn:
        _ensure_aesthetic_motif_log_table(conn)
        rows = conn.execute(
            """
            SELECT motif, COUNT(*) as count, AVG(confidence) as avg_confidence
            FROM aesthetic_motif_log
            GROUP BY motif
            ORDER BY count DESC
            """
        ).fetchall()
        return [
            {"motif": row[0], "count": row[1], "avg_confidence": row[2]}
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Channel Attachments
# ---------------------------------------------------------------------------

def _ensure_channel_attachments_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS channel_attachments (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            attachment_id TEXT    NOT NULL UNIQUE,
            session_id    TEXT    NOT NULL,
            channel_type  TEXT    NOT NULL,
            filename      TEXT    NOT NULL,
            mime_type     TEXT    NOT NULL DEFAULT '',
            size_bytes    INTEGER NOT NULL DEFAULT 0,
            local_path    TEXT    NOT NULL,
            source_url    TEXT    NOT NULL DEFAULT '',
            created_at    TEXT    NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_attachments_session "
        "ON channel_attachments(session_id)"
    )


def store_channel_attachment(
    *,
    conn: sqlite3.Connection,
    attachment_id: str,
    session_id: str,
    channel_type: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    local_path: str,
    source_url: str,
) -> None:
    _ensure_channel_attachments_table(conn)
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT OR IGNORE INTO channel_attachments
            (attachment_id, session_id, channel_type, filename, mime_type,
             size_bytes, local_path, source_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (attachment_id, session_id, channel_type, filename, mime_type,
         size_bytes, local_path, source_url, now),
    )


def get_channel_attachment(
    *, conn: sqlite3.Connection, attachment_id: str
) -> dict | None:
    _ensure_channel_attachments_table(conn)
    row = conn.execute(
        """
        SELECT attachment_id, session_id, channel_type, filename, mime_type,
               size_bytes, local_path, source_url, created_at
        FROM channel_attachments WHERE attachment_id = ?
        """,
        (attachment_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_channel_attachments(
    *, conn: sqlite3.Connection, session_id: str, limit: int = 20
) -> list[dict]:
    _ensure_channel_attachments_table(conn)
    rows = conn.execute(
        """
        SELECT attachment_id, session_id, channel_type, filename, mime_type,
               size_bytes, local_path, source_url, created_at
        FROM channel_attachments
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]
