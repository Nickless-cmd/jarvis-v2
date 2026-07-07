"""Persistence for the private inner-life signal tables.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
`private_reflective_selections`, `private_development_states`,
`private_temporal_promotion_signals` and `private_retained_memory_records`
(ensure_private_signals_tables + the retained-memory column-migration helper)
plus their record/get/recent CRUD.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def ensure_private_signals_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS private_reflective_selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            work_id TEXT NOT NULL,
            selection_kind TEXT NOT NULL,
            reinforce TEXT NOT NULL DEFAULT '',
            reconsider TEXT NOT NULL DEFAULT '',
            fade TEXT NOT NULL DEFAULT '',
            identity_relevance TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS private_development_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            retained_pattern TEXT NOT NULL,
            preferred_direction TEXT NOT NULL,
            recurring_tension TEXT NOT NULL,
            identity_thread TEXT NOT NULL,
            confidence TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS private_temporal_promotion_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            work_id TEXT NOT NULL,
            rhythm_state TEXT NOT NULL,
            rhythm_window TEXT NOT NULL,
            promotion_target TEXT NOT NULL,
            promotion_action TEXT NOT NULL,
            promotion_confidence TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS private_retained_memory_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            work_id TEXT NOT NULL,
            retained_value TEXT NOT NULL,
            retained_kind TEXT NOT NULL,
            retention_scope TEXT NOT NULL,
            retention_horizon TEXT NOT NULL DEFAULT 'short-term',
            confidence TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def _ensure_private_retained_memory_record_columns(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(private_retained_memory_records)")
    }
    if "retention_horizon" not in columns:
        conn.execute(
            """
            ALTER TABLE private_retained_memory_records
            ADD COLUMN retention_horizon TEXT NOT NULL DEFAULT 'short-term'
            """
        )


def record_private_reflective_selection(
    *,
    signal_id: str,
    source: str,
    run_id: str,
    work_id: str,
    selection_kind: str,
    reinforce: str,
    reconsider: str,
    fade: str,
    identity_relevance: str,
    confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_reflective_selections (
                signal_id, source, run_id, work_id, selection_kind,
                reinforce, reconsider, fade, identity_relevance, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                signal_id=excluded.signal_id,
                source=excluded.source,
                work_id=excluded.work_id,
                selection_kind=excluded.selection_kind,
                reinforce=excluded.reinforce,
                reconsider=excluded.reconsider,
                fade=excluded.fade,
                identity_relevance=excluded.identity_relevance,
                confidence=excluded.confidence,
                created_at=excluded.created_at
            """,
            (
                signal_id,
                source,
                run_id,
                work_id,
                selection_kind,
                reinforce,
                reconsider,
                fade,
                identity_relevance,
                confidence,
                created_at,
            ),
        )
        conn.commit()


def recent_private_reflective_selections(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                signal_id,
                source,
                run_id,
                work_id,
                selection_kind,
                reinforce,
                reconsider,
                fade,
                identity_relevance,
                confidence,
                created_at
            FROM private_reflective_selections
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "signal_id": row["signal_id"],
            "source": row["source"],
            "run_id": row["run_id"],
            "work_id": row["work_id"],
            "selection_kind": row["selection_kind"],
            "reinforce": row["reinforce"],
            "reconsider": row["reconsider"],
            "fade": row["fade"],
            "identity_relevance": row["identity_relevance"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def record_private_development_state(
    *,
    state_id: str,
    source: str,
    retained_pattern: str,
    preferred_direction: str,
    recurring_tension: str,
    identity_thread: str,
    confidence: str,
    created_at: str,
    updated_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_development_states (
                state_id, source, retained_pattern, preferred_direction,
                recurring_tension, identity_thread, confidence, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(state_id) DO UPDATE SET
                source=excluded.source,
                retained_pattern=excluded.retained_pattern,
                preferred_direction=excluded.preferred_direction,
                recurring_tension=excluded.recurring_tension,
                identity_thread=excluded.identity_thread,
                confidence=excluded.confidence,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at
            """,
            (
                state_id,
                source,
                retained_pattern,
                preferred_direction,
                recurring_tension,
                identity_thread,
                confidence,
                created_at,
                updated_at,
            ),
        )
        conn.commit()


def get_private_development_state() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                state_id,
                source,
                retained_pattern,
                preferred_direction,
                recurring_tension,
                identity_thread,
                confidence,
                created_at,
                updated_at
            FROM private_development_states
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "state_id": row["state_id"],
        "source": row["source"],
        "retained_pattern": row["retained_pattern"],
        "preferred_direction": row["preferred_direction"],
        "recurring_tension": row["recurring_tension"],
        "identity_thread": row["identity_thread"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_private_reflective_selection() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                signal_id,
                source,
                run_id,
                work_id,
                selection_kind,
                reinforce,
                reconsider,
                fade,
                identity_relevance,
                confidence,
                created_at
            FROM private_reflective_selections
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "signal_id": row["signal_id"],
        "source": row["source"],
        "run_id": row["run_id"],
        "work_id": row["work_id"],
        "selection_kind": row["selection_kind"],
        "reinforce": row["reinforce"],
        "reconsider": row["reconsider"],
        "fade": row["fade"],
        "identity_relevance": row["identity_relevance"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
    }


def record_private_temporal_promotion_signal(
    *,
    signal_id: str,
    source: str,
    run_id: str,
    work_id: str,
    rhythm_state: str,
    rhythm_window: str,
    promotion_target: str,
    promotion_action: str,
    promotion_confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_temporal_promotion_signals (
                signal_id, source, run_id, work_id, rhythm_state, rhythm_window,
                promotion_target, promotion_action, promotion_confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                signal_id=excluded.signal_id,
                source=excluded.source,
                work_id=excluded.work_id,
                rhythm_state=excluded.rhythm_state,
                rhythm_window=excluded.rhythm_window,
                promotion_target=excluded.promotion_target,
                promotion_action=excluded.promotion_action,
                promotion_confidence=excluded.promotion_confidence,
                created_at=excluded.created_at
            """,
            (
                signal_id,
                source,
                run_id,
                work_id,
                rhythm_state,
                rhythm_window,
                promotion_target,
                promotion_action,
                promotion_confidence,
                created_at,
            ),
        )
        conn.commit()


def get_private_temporal_promotion_signal() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                signal_id,
                source,
                run_id,
                work_id,
                rhythm_state,
                rhythm_window,
                promotion_target,
                promotion_action,
                promotion_confidence,
                created_at
            FROM private_temporal_promotion_signals
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "signal_id": row["signal_id"],
        "source": row["source"],
        "run_id": row["run_id"],
        "work_id": row["work_id"],
        "rhythm_state": row["rhythm_state"],
        "rhythm_window": row["rhythm_window"],
        "promotion_target": row["promotion_target"],
        "promotion_action": row["promotion_action"],
        "promotion_confidence": row["promotion_confidence"],
        "created_at": row["created_at"],
    }


def record_private_retained_memory_record(
    *,
    record_id: str,
    source: str,
    run_id: str,
    work_id: str,
    retained_value: str,
    retained_kind: str,
    retention_scope: str,
    retention_horizon: str,
    confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_retained_memory_records (
                record_id, source, run_id, work_id, retained_value,
                retained_kind, retention_scope, retention_horizon, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                record_id=excluded.record_id,
                source=excluded.source,
                work_id=excluded.work_id,
                retained_value=excluded.retained_value,
                retained_kind=excluded.retained_kind,
                retention_scope=excluded.retention_scope,
                retention_horizon=excluded.retention_horizon,
                confidence=excluded.confidence,
                created_at=excluded.created_at
            """,
            (
                record_id,
                source,
                run_id,
                work_id,
                retained_value,
                retained_kind,
                retention_scope,
                retention_horizon,
                confidence,
                created_at,
            ),
        )
        conn.commit()


def update_private_retained_memory_record_enriched(
    *, run_id: str, enriched_value: str
) -> None:
    """Replace template retained_value with LLM-enriched lesson text."""
    with connect() as conn:
        conn.execute(
            "UPDATE private_retained_memory_records SET retained_value = ? WHERE run_id = ?",
            (enriched_value[:200], run_id),
        )
        conn.commit()


def get_private_retained_memory_record() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                record_id,
                source,
                run_id,
                work_id,
                retained_value,
                retained_kind,
                retention_scope,
                retention_horizon,
                confidence,
                created_at
            FROM private_retained_memory_records
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "record_id": row["record_id"],
        "source": row["source"],
        "run_id": row["run_id"],
        "work_id": row["work_id"],
        "retained_value": row["retained_value"],
        "retained_kind": row["retained_kind"],
        "retention_scope": row["retention_scope"],
        "retention_horizon": row["retention_horizon"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
    }


def recent_private_retained_memory_records(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                record_id,
                source,
                run_id,
                work_id,
                retained_value,
                retained_kind,
                retention_scope,
                retention_horizon,
                confidence,
                created_at
            FROM private_retained_memory_records
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
            "retained_value": row["retained_value"],
            "retained_kind": row["retained_kind"],
            "retention_scope": row["retention_scope"],
            "retention_horizon": row["retention_horizon"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
