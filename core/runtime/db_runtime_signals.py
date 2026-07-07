"""Persistence for the runtime learning/outcome signal tables.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
`runtime_action_outcomes` and `runtime_learning_signals`
(ensure_runtime_signals_tables + the additive target_domain migration) plus
their record/recent CRUD and row-mapping helpers.
"""
from __future__ import annotations

import json as _json
import sqlite3
from uuid import uuid4

from core.runtime.db_core import connect


def ensure_runtime_signals_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_action_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outcome_id TEXT NOT NULL UNIQUE,
            action_id TEXT NOT NULL,
            decision_mode TEXT NOT NULL,
            decision_reason TEXT NOT NULL DEFAULT '',
            decision_score REAL NOT NULL DEFAULT 0,
            payload_json TEXT NOT NULL DEFAULT '{}',
            result_status TEXT NOT NULL,
            result_summary TEXT NOT NULL DEFAULT '',
            result_json TEXT NOT NULL DEFAULT '{}',
            recorded_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_action_outcomes_lookup
        ON runtime_action_outcomes(action_id, recorded_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_learning_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            outcome_id TEXT NOT NULL,
            source_action_id TEXT NOT NULL,
            target_action_id TEXT NOT NULL DEFAULT '',
            target_family TEXT NOT NULL DEFAULT '',
            target_domain TEXT NOT NULL DEFAULT '',
            signal_key TEXT NOT NULL,
            signal_weight REAL NOT NULL DEFAULT 0,
            signal_count INTEGER NOT NULL DEFAULT 1,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            recorded_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_learning_signals_lookup
        ON runtime_learning_signals(signal_key, target_family, target_action_id, recorded_at DESC)
        """
    )
    try:
        conn.execute(
            """
            ALTER TABLE runtime_learning_signals
            ADD COLUMN target_domain TEXT NOT NULL DEFAULT ''
            """
        )
    except sqlite3.OperationalError:
        pass


def _runtime_action_outcome_from_row(row: sqlite3.Row) -> dict[str, object]:
    payload_raw = str(row["payload_json"] or "{}")
    result_raw = str(row["result_json"] or "{}")
    try:
        payload = _json.loads(payload_raw)
    except Exception:
        payload = {}
    try:
        result = _json.loads(result_raw)
    except Exception:
        result = {}
    return {
        "outcome_id": row["outcome_id"],
        "action_id": row["action_id"],
        "decision_mode": row["decision_mode"],
        "decision_reason": row["decision_reason"],
        "decision_score": float(row["decision_score"] or 0.0),
        "payload": payload if isinstance(payload, dict) else {},
        "result_status": row["result_status"],
        "result_summary": row["result_summary"],
        "result": result if isinstance(result, dict) else {},
        "recorded_at": row["recorded_at"],
    }


def _runtime_learning_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    metadata_raw = str(row["metadata_json"] or "{}")
    try:
        metadata = _json.loads(metadata_raw)
    except Exception:
        metadata = {}
    return {
        "signal_id": row["signal_id"],
        "outcome_id": row["outcome_id"],
        "source_action_id": row["source_action_id"],
        "target_action_id": row["target_action_id"],
        "target_family": row["target_family"],
        "target_domain": row["target_domain"],
        "signal_key": row["signal_key"],
        "signal_weight": float(row["signal_weight"] or 0.0),
        "signal_count": int(row["signal_count"] or 1),
        "metadata": metadata if isinstance(metadata, dict) else {},
        "recorded_at": row["recorded_at"],
    }


def recent_runtime_action_outcomes(limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                outcome_id,
                action_id,
                decision_mode,
                decision_reason,
                decision_score,
                payload_json,
                result_status,
                result_summary,
                result_json,
                recorded_at
            FROM runtime_action_outcomes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [_runtime_action_outcome_from_row(row) for row in rows]


def recent_runtime_learning_signals(limit: int = 25) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                signal_id,
                outcome_id,
                source_action_id,
                target_action_id,
                target_family,
                target_domain,
                signal_key,
                signal_weight,
                signal_count,
                metadata_json,
                recorded_at
            FROM runtime_learning_signals
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [_runtime_learning_signal_from_row(row) for row in rows]


def record_runtime_action_outcome(
    *,
    action_id: str,
    decision_mode: str,
    decision_reason: str,
    decision_score: float,
    payload_json: dict[str, object] | None,
    result_status: str,
    result_summary: str,
    result_json: dict[str, object] | None,
    recorded_at: str,
) -> dict[str, object]:
    outcome_id = f"rao-{uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_action_outcomes (
                outcome_id,
                action_id,
                decision_mode,
                decision_reason,
                decision_score,
                payload_json,
                result_status,
                result_summary,
                result_json,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                outcome_id,
                action_id,
                decision_mode,
                decision_reason,
                float(decision_score or 0.0),
                _json.dumps(payload_json or {}, ensure_ascii=False, sort_keys=True),
                result_status,
                result_summary,
                _json.dumps(result_json or {}, ensure_ascii=False, sort_keys=True),
                recorded_at,
            ),
        )
        conn.commit()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                outcome_id,
                action_id,
                decision_mode,
                decision_reason,
                decision_score,
                payload_json,
                result_status,
                result_summary,
                result_json,
                recorded_at
            FROM runtime_action_outcomes
            WHERE outcome_id = ?
            """,
            (outcome_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("runtime action outcome was not persisted")
    return _runtime_action_outcome_from_row(row)


def record_runtime_learning_signal(
    *,
    outcome_id: str,
    source_action_id: str,
    target_action_id: str,
    target_family: str,
    target_domain: str,
    signal_key: str,
    signal_weight: float,
    signal_count: int,
    metadata_json: dict[str, object] | None,
    recorded_at: str,
) -> dict[str, object]:
    signal_id = f"rls-{uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_learning_signals (
                signal_id,
                outcome_id,
                source_action_id,
                target_action_id,
                target_family,
                target_domain,
                signal_key,
                signal_weight,
                signal_count,
                metadata_json,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                outcome_id,
                source_action_id,
                target_action_id,
                target_family,
                target_domain,
                signal_key,
                float(signal_weight or 0.0),
                int(signal_count or 1),
                _json.dumps(metadata_json or {}, ensure_ascii=False, sort_keys=True),
                recorded_at,
            ),
        )
        conn.commit()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                signal_id,
                outcome_id,
                source_action_id,
                target_action_id,
                target_family,
                target_domain,
                signal_key,
                signal_weight,
                signal_count,
                metadata_json,
                recorded_at
            FROM runtime_learning_signals
            WHERE signal_id = ?
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("runtime learning signal was not persisted")
    return _runtime_learning_signal_from_row(row)
