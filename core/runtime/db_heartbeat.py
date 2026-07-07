"""Persistence for the heartbeat runtime tables — Jarvis' tick rhythm.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
`heartbeat_runtime_state` and `heartbeat_runtime_ticks` (ensure_heartbeat_tables
+ the two additive column-migration helpers) plus the state/tick CRUD.
"""
from __future__ import annotations

import logging as _logging
import sqlite3

from core.runtime.db_core import connect

_logger = _logging.getLogger("uvicorn.error")


def ensure_heartbeat_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS heartbeat_runtime_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            state_id TEXT NOT NULL UNIQUE,
            last_tick_id TEXT NOT NULL DEFAULT '',
            last_tick_at TEXT NOT NULL DEFAULT '',
            next_tick_at TEXT NOT NULL DEFAULT '',
            schedule_state TEXT NOT NULL DEFAULT '',
            due INTEGER NOT NULL DEFAULT 0,
            last_decision_type TEXT NOT NULL DEFAULT '',
            last_result TEXT NOT NULL DEFAULT '',
            blocked_reason TEXT NOT NULL DEFAULT '',
            currently_ticking INTEGER NOT NULL DEFAULT 0,
            last_trigger_source TEXT NOT NULL DEFAULT '',
            scheduler_active INTEGER NOT NULL DEFAULT 0,
            scheduler_started_at TEXT NOT NULL DEFAULT '',
            scheduler_stopped_at TEXT NOT NULL DEFAULT '',
            scheduler_health TEXT NOT NULL DEFAULT '',
            recovery_status TEXT NOT NULL DEFAULT '',
            last_recovery_at TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            lane TEXT NOT NULL DEFAULT '',
            model_source TEXT NOT NULL DEFAULT '',
            resolution_status TEXT NOT NULL DEFAULT '',
            fallback_used INTEGER NOT NULL DEFAULT 0,
            execution_status TEXT NOT NULL DEFAULT '',
            parse_status TEXT NOT NULL DEFAULT '',
            budget_status TEXT NOT NULL DEFAULT '',
            last_ping_eligible INTEGER NOT NULL DEFAULT 0,
            last_ping_result TEXT NOT NULL DEFAULT '',
            last_successful_ping_at TEXT NOT NULL DEFAULT '',
            last_action_type TEXT NOT NULL DEFAULT '',
            last_action_status TEXT NOT NULL DEFAULT '',
            last_action_summary TEXT NOT NULL DEFAULT '',
            last_action_artifact TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS heartbeat_runtime_ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tick_id TEXT NOT NULL UNIQUE,
            trigger TEXT NOT NULL,
            tick_status TEXT NOT NULL,
            decision_type TEXT NOT NULL DEFAULT '',
            decision_summary TEXT NOT NULL DEFAULT '',
            decision_reason TEXT NOT NULL DEFAULT '',
            blocked_reason TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            lane TEXT NOT NULL DEFAULT '',
            model_source TEXT NOT NULL DEFAULT '',
            resolution_status TEXT NOT NULL DEFAULT '',
            fallback_used INTEGER NOT NULL DEFAULT 0,
            execution_status TEXT NOT NULL DEFAULT '',
            parse_status TEXT NOT NULL DEFAULT '',
            budget_status TEXT NOT NULL DEFAULT '',
            ping_eligible INTEGER NOT NULL DEFAULT 0,
            ping_result TEXT NOT NULL DEFAULT '',
            action_status TEXT NOT NULL DEFAULT '',
            action_summary TEXT NOT NULL DEFAULT '',
            action_type TEXT NOT NULL DEFAULT '',
            action_artifact TEXT NOT NULL DEFAULT '',
            raw_response TEXT NOT NULL DEFAULT '',
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_heartbeat_runtime_ticks_finished
        ON heartbeat_runtime_ticks(id DESC)
        """
    )


def _ensure_heartbeat_runtime_state_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(heartbeat_runtime_state)").fetchall()
    existing = {str(row["name"]) for row in rows}
    if "currently_ticking" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN currently_ticking INTEGER NOT NULL DEFAULT 0
            """
        )
    if "last_trigger_source" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_trigger_source TEXT NOT NULL DEFAULT ''
            """
        )
    if "schedule_state" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN schedule_state TEXT NOT NULL DEFAULT ''
            """
        )
    if "due" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN due INTEGER NOT NULL DEFAULT 0
            """
        )
    if "scheduler_active" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN scheduler_active INTEGER NOT NULL DEFAULT 0
            """
        )
    if "scheduler_started_at" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN scheduler_started_at TEXT NOT NULL DEFAULT ''
            """
        )
    if "scheduler_stopped_at" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN scheduler_stopped_at TEXT NOT NULL DEFAULT ''
            """
        )
    if "scheduler_health" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN scheduler_health TEXT NOT NULL DEFAULT ''
            """
        )
    if "recovery_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN recovery_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_recovery_at" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_recovery_at TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_action_type" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_action_type TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_action_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_action_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_action_summary" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_action_summary TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_action_artifact" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_action_artifact TEXT NOT NULL DEFAULT ''
            """
        )
    if "model_source" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN model_source TEXT NOT NULL DEFAULT ''
            """
        )
    if "resolution_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN resolution_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "fallback_used" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN fallback_used INTEGER NOT NULL DEFAULT 0
            """
        )
    if "execution_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN execution_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "parse_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN parse_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_successful_ping_at" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_successful_ping_at TEXT NOT NULL DEFAULT ''
            """
        )


def _ensure_heartbeat_runtime_tick_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(heartbeat_runtime_ticks)").fetchall()
    existing = {str(row["name"]) for row in rows}
    if "action_type" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN action_type TEXT NOT NULL DEFAULT ''
            """
        )
    if "action_artifact" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN action_artifact TEXT NOT NULL DEFAULT ''
            """
        )
    if "model_source" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN model_source TEXT NOT NULL DEFAULT ''
            """
        )
    if "resolution_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN resolution_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "fallback_used" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN fallback_used INTEGER NOT NULL DEFAULT 0
            """
        )
    if "execution_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN execution_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "parse_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN parse_status TEXT NOT NULL DEFAULT ''
            """
        )


def _heartbeat_runtime_state_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "state_id": row["state_id"],
        "last_tick_id": row["last_tick_id"],
        "last_tick_at": row["last_tick_at"],
        "next_tick_at": row["next_tick_at"],
        "schedule_state": row["schedule_state"],
        "due": bool(row["due"]),
        "last_decision_type": row["last_decision_type"],
        "last_result": row["last_result"],
        "blocked_reason": row["blocked_reason"],
        "currently_ticking": bool(row["currently_ticking"]),
        "last_trigger_source": row["last_trigger_source"],
        "scheduler_active": bool(row["scheduler_active"]),
        "scheduler_started_at": row["scheduler_started_at"],
        "scheduler_stopped_at": row["scheduler_stopped_at"],
        "scheduler_health": row["scheduler_health"],
        "recovery_status": row["recovery_status"],
        "last_recovery_at": row["last_recovery_at"],
        "provider": row["provider"],
        "model": row["model"],
        "lane": row["lane"],
        "model_source": row["model_source"],
        "resolution_status": row["resolution_status"],
        "fallback_used": bool(row["fallback_used"]),
        "execution_status": row["execution_status"],
        "parse_status": row["parse_status"],
        "budget_status": row["budget_status"],
        "last_ping_eligible": bool(row["last_ping_eligible"]),
        "last_ping_result": row["last_ping_result"],
        "last_successful_ping_at": row["last_successful_ping_at"] if "last_successful_ping_at" in row.keys() else "",
        "last_action_type": row["last_action_type"],
        "last_action_status": row["last_action_status"],
        "last_action_summary": row["last_action_summary"],
        "last_action_artifact": row["last_action_artifact"],
        "updated_at": row["updated_at"],
    }


def _heartbeat_runtime_tick_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "tick_id": row["tick_id"],
        "trigger": row["trigger"],
        "tick_status": row["tick_status"],
        "decision_type": row["decision_type"],
        "decision_summary": row["decision_summary"],
        "decision_reason": row["decision_reason"],
        "blocked_reason": row["blocked_reason"],
        "provider": row["provider"],
        "model": row["model"],
        "lane": row["lane"],
        "model_source": row["model_source"],
        "resolution_status": row["resolution_status"],
        "fallback_used": bool(row["fallback_used"]),
        "execution_status": row["execution_status"],
        "parse_status": row["parse_status"],
        "budget_status": row["budget_status"],
        "ping_eligible": bool(row["ping_eligible"]),
        "ping_result": row["ping_result"],
        "action_status": row["action_status"],
        "action_summary": row["action_summary"],
        "action_type": row["action_type"],
        "action_artifact": row["action_artifact"],
        "raw_response": row["raw_response"],
        "input_tokens": int(row["input_tokens"] or 0),
        "output_tokens": int(row["output_tokens"] or 0),
        "cost_usd": float(row["cost_usd"] or 0.0),
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }


def get_heartbeat_runtime_state() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                state_id,
                last_tick_id,
                last_tick_at,
                next_tick_at,
                schedule_state,
                due,
                last_decision_type,
                last_result,
                blocked_reason,
                currently_ticking,
                last_trigger_source,
                scheduler_active,
                scheduler_started_at,
                scheduler_stopped_at,
                scheduler_health,
                recovery_status,
                last_recovery_at,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                fallback_used,
                execution_status,
                parse_status,
                budget_status,
                last_ping_eligible,
                last_ping_result,
                last_action_type,
                last_action_status,
                last_action_summary,
                last_action_artifact,
                updated_at
            FROM heartbeat_runtime_state
            WHERE id = 1
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return _heartbeat_runtime_state_from_row(row)


def upsert_heartbeat_runtime_state(
    *,
    state_id: str,
    last_tick_id: str,
    last_tick_at: str,
    next_tick_at: str,
    schedule_state: str,
    due: bool,
    last_decision_type: str,
    last_result: str,
    blocked_reason: str,
    currently_ticking: bool,
    last_trigger_source: str,
    scheduler_active: bool,
    scheduler_started_at: str,
    scheduler_stopped_at: str,
    scheduler_health: str,
    recovery_status: str,
    last_recovery_at: str,
    provider: str,
    model: str,
    lane: str,
    model_source: str,
    resolution_status: str,
    fallback_used: bool,
    execution_status: str,
    parse_status: str,
    budget_status: str,
    last_ping_eligible: bool,
    last_ping_result: str,
    last_action_type: str,
    last_action_status: str,
    last_action_summary: str,
    last_action_artifact: str,
    updated_at: str,
    last_successful_ping_at: str = "",
) -> dict[str, object]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO heartbeat_runtime_state (
                id,
                state_id,
                last_tick_id,
                last_tick_at,
                next_tick_at,
                schedule_state,
                due,
                last_decision_type,
                last_result,
                blocked_reason,
                currently_ticking,
                last_trigger_source,
                scheduler_active,
                scheduler_started_at,
                scheduler_stopped_at,
                scheduler_health,
                recovery_status,
                last_recovery_at,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                fallback_used,
                execution_status,
                parse_status,
                budget_status,
                last_ping_eligible,
                last_ping_result,
                last_successful_ping_at,
                last_action_type,
                last_action_status,
                last_action_summary,
                last_action_artifact,
                updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                state_id = excluded.state_id,
                last_tick_id = excluded.last_tick_id,
                last_tick_at = excluded.last_tick_at,
                next_tick_at = excluded.next_tick_at,
                schedule_state = excluded.schedule_state,
                due = excluded.due,
                last_decision_type = excluded.last_decision_type,
                last_result = excluded.last_result,
                blocked_reason = excluded.blocked_reason,
                currently_ticking = excluded.currently_ticking,
                last_trigger_source = excluded.last_trigger_source,
                scheduler_active = excluded.scheduler_active,
                scheduler_started_at = excluded.scheduler_started_at,
                scheduler_stopped_at = excluded.scheduler_stopped_at,
                scheduler_health = excluded.scheduler_health,
                recovery_status = excluded.recovery_status,
                last_recovery_at = excluded.last_recovery_at,
                provider = excluded.provider,
                model = excluded.model,
                lane = excluded.lane,
                model_source = excluded.model_source,
                resolution_status = excluded.resolution_status,
                fallback_used = excluded.fallback_used,
                execution_status = excluded.execution_status,
                parse_status = excluded.parse_status,
                budget_status = excluded.budget_status,
                last_ping_eligible = excluded.last_ping_eligible,
                last_ping_result = excluded.last_ping_result,
                last_successful_ping_at = excluded.last_successful_ping_at,
                last_action_type = excluded.last_action_type,
                last_action_status = excluded.last_action_status,
                last_action_summary = excluded.last_action_summary,
                last_action_artifact = excluded.last_action_artifact,
                updated_at = excluded.updated_at
            """,
            (
                state_id,
                last_tick_id,
                last_tick_at,
                next_tick_at,
                schedule_state,
                1 if due else 0,
                last_decision_type,
                last_result,
                blocked_reason,
                1 if currently_ticking else 0,
                last_trigger_source,
                1 if scheduler_active else 0,
                scheduler_started_at,
                scheduler_stopped_at,
                scheduler_health,
                recovery_status,
                last_recovery_at,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                1 if fallback_used else 0,
                execution_status,
                parse_status,
                budget_status,
                1 if last_ping_eligible else 0,
                last_ping_result,
                last_successful_ping_at,
                last_action_type,
                last_action_status,
                last_action_summary,
                last_action_artifact,
                updated_at,
            ),
        )
        _logger.info(
            "HEARTBEAT-UPSERT-BEFORE-COMMIT: schedule_state=%s due=%s updated_at=%s state_id=%s in_transaction=%s",
            schedule_state, due, updated_at, state_id, conn.in_transaction,
        )
        try:
            conn.commit()
        except Exception:
            _logger.error(
                "HEARTBEAT-UPSERT-COMMIT-FAILED: schedule_state=%s due=%s updated_at=%s state_id=%s",
                schedule_state, due, updated_at, state_id,
            )
            raise
    state = get_heartbeat_runtime_state()
    if state is None:
        _logger.error(
            "HEARTBEAT-UPSERT-NOT-PERSISTED: schedule_state=%s due=%s updated_at=%s state_id=%s",
            schedule_state, due, updated_at, state_id,
        )
        raise RuntimeError("heartbeat runtime state was not persisted")
    _logger.info(
        "HEARTBEAT-UPSERT-PERSISTED-OK: schedule_state=%s state_id=%s",
        state.get("schedule_state"), state.get("state_id"),
    )
    return state


def record_heartbeat_runtime_tick(
    *,
    tick_id: str,
    trigger: str,
    tick_status: str,
    decision_type: str,
    decision_summary: str,
    decision_reason: str,
    blocked_reason: str,
    provider: str,
    model: str,
    lane: str,
    model_source: str,
    resolution_status: str,
    fallback_used: bool,
    execution_status: str,
    parse_status: str,
    budget_status: str,
    ping_eligible: bool,
    ping_result: str,
    action_status: str,
    action_summary: str,
    action_type: str,
    action_artifact: str,
    raw_response: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    started_at: str,
    finished_at: str,
) -> dict[str, object]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO heartbeat_runtime_ticks (
                tick_id,
                trigger,
                tick_status,
                decision_type,
                decision_summary,
                decision_reason,
                blocked_reason,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                fallback_used,
                execution_status,
                parse_status,
                budget_status,
                ping_eligible,
                ping_result,
                action_status,
                action_summary,
                action_type,
                action_artifact,
                raw_response,
                input_tokens,
                output_tokens,
                cost_usd,
                started_at,
                finished_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tick_id,
                trigger,
                tick_status,
                decision_type,
                decision_summary,
                decision_reason,
                blocked_reason,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                1 if fallback_used else 0,
                execution_status,
                parse_status,
                budget_status,
                1 if ping_eligible else 0,
                ping_result,
                action_status,
                action_summary,
                action_type,
                action_artifact,
                raw_response,
                int(input_tokens or 0),
                int(output_tokens or 0),
                float(cost_usd or 0.0),
                started_at,
                finished_at,
            ),
        )
        conn.commit()
    tick = get_heartbeat_runtime_tick(tick_id)
    if tick is None:
        raise RuntimeError("heartbeat runtime tick was not persisted")
    return tick


def get_heartbeat_runtime_tick(tick_id: str) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                tick_id,
                trigger,
                tick_status,
                decision_type,
                decision_summary,
                decision_reason,
                blocked_reason,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                fallback_used,
                execution_status,
                parse_status,
                budget_status,
                ping_eligible,
                ping_result,
                action_status,
                action_summary,
                action_type,
                action_artifact,
                raw_response,
                input_tokens,
                output_tokens,
                cost_usd,
                started_at,
                finished_at
            FROM heartbeat_runtime_ticks
            WHERE tick_id = ?
            LIMIT 1
            """,
            (tick_id,),
        ).fetchone()
    if row is None:
        return None
    return _heartbeat_runtime_tick_from_row(row)


def recent_heartbeat_runtime_ticks(limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                tick_id,
                trigger,
                tick_status,
                decision_type,
                decision_summary,
                decision_reason,
                blocked_reason,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                fallback_used,
                execution_status,
                parse_status,
                budget_status,
                ping_eligible,
                ping_result,
                action_status,
                action_summary,
                action_type,
                action_artifact,
                raw_response,
                input_tokens,
                output_tokens,
                cost_usd,
                started_at,
                finished_at
            FROM heartbeat_runtime_ticks
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [_heartbeat_runtime_tick_from_row(row) for row in rows]
