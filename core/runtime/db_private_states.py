"""Persistence for the private self-model / mood / promotion-decision tables.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
`private_self_models`, `private_states` and `private_promotion_decisions`
(ensure_private_states_tables) plus their record/get CRUD.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def ensure_private_states_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS private_self_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            identity_focus TEXT NOT NULL,
            preferred_work_mode TEXT NOT NULL,
            recurring_tension TEXT NOT NULL,
            growth_direction TEXT NOT NULL,
            confidence TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS private_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            frustration TEXT NOT NULL,
            fatigue TEXT NOT NULL,
            confidence TEXT NOT NULL,
            curiosity TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS private_promotion_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            work_id TEXT NOT NULL,
            promotion_target TEXT NOT NULL,
            promotion_action TEXT NOT NULL,
            promotion_scope TEXT NOT NULL,
            confidence TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def record_private_self_model(
    *,
    model_id: str,
    source: str,
    identity_focus: str,
    preferred_work_mode: str,
    recurring_tension: str,
    growth_direction: str,
    confidence: str,
    created_at: str,
    updated_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_self_models (
                model_id, source, identity_focus, preferred_work_mode,
                recurring_tension, growth_direction, confidence, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(model_id) DO UPDATE SET
                source=excluded.source,
                identity_focus=excluded.identity_focus,
                preferred_work_mode=excluded.preferred_work_mode,
                recurring_tension=excluded.recurring_tension,
                growth_direction=excluded.growth_direction,
                confidence=excluded.confidence,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at
            """,
            (
                model_id,
                source,
                identity_focus,
                preferred_work_mode,
                recurring_tension,
                growth_direction,
                confidence,
                created_at,
                updated_at,
            ),
        )
        conn.commit()


def get_private_self_model() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                model_id,
                source,
                identity_focus,
                preferred_work_mode,
                recurring_tension,
                growth_direction,
                confidence,
                created_at,
                updated_at
            FROM private_self_models
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "model_id": row["model_id"],
        "source": row["source"],
        "identity_focus": row["identity_focus"],
        "preferred_work_mode": row["preferred_work_mode"],
        "recurring_tension": row["recurring_tension"],
        "growth_direction": row["growth_direction"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def record_private_state(
    *,
    state_id: str,
    source: str,
    frustration: str,
    fatigue: str,
    confidence: str,
    curiosity: str,
    created_at: str,
    updated_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_states (
                state_id, source, frustration, fatigue, confidence, curiosity,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(state_id) DO UPDATE SET
                source=excluded.source,
                frustration=excluded.frustration,
                fatigue=excluded.fatigue,
                confidence=excluded.confidence,
                curiosity=excluded.curiosity,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at
            """,
            (
                state_id,
                source,
                frustration,
                fatigue,
                confidence,
                curiosity,
                created_at,
                updated_at,
            ),
        )
        conn.commit()


def get_private_state() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                state_id,
                source,
                frustration,
                fatigue,
                confidence,
                curiosity,
                created_at,
                updated_at
            FROM private_states
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "state_id": row["state_id"],
        "source": row["source"],
        "frustration": row["frustration"],
        "fatigue": row["fatigue"],
        "confidence": row["confidence"],
        "curiosity": row["curiosity"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def record_private_promotion_decision(
    *,
    decision_id: str,
    source: str,
    run_id: str,
    work_id: str,
    promotion_target: str,
    promotion_action: str,
    promotion_scope: str,
    confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_promotion_decisions (
                decision_id, source, run_id, work_id, promotion_target,
                promotion_action, promotion_scope, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                decision_id=excluded.decision_id,
                source=excluded.source,
                work_id=excluded.work_id,
                promotion_target=excluded.promotion_target,
                promotion_action=excluded.promotion_action,
                promotion_scope=excluded.promotion_scope,
                confidence=excluded.confidence,
                created_at=excluded.created_at
            """,
            (
                decision_id,
                source,
                run_id,
                work_id,
                promotion_target,
                promotion_action,
                promotion_scope,
                confidence,
                created_at,
            ),
        )
        conn.commit()


def get_private_promotion_decision() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                decision_id,
                source,
                run_id,
                work_id,
                promotion_target,
                promotion_action,
                promotion_scope,
                confidence,
                created_at
            FROM private_promotion_decisions
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "decision_id": row["decision_id"],
        "source": row["source"],
        "run_id": row["run_id"],
        "work_id": row["work_id"],
        "promotion_target": row["promotion_target"],
        "promotion_action": row["promotion_action"],
        "promotion_scope": row["promotion_scope"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
    }
