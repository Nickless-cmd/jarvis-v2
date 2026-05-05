"""DB helpers for self_repair_patterns + self_repair_attempts tables.

Split out from db.py per CLAUDE.md boy scout rule (db.py is 33k lines).
Re-exported from core.runtime.db for backwards compatibility.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from core.runtime.db import connect, _now_iso


def _ensure_self_repair_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS self_repair_patterns (
            pattern_id          TEXT PRIMARY KEY,
            name                TEXT NOT NULL,
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL,
            trigger_event_kind  TEXT NOT NULL,
            trigger_match_json  TEXT NOT NULL DEFAULT '{}',
            action_type         TEXT NOT NULL,
            action_params_json  TEXT NOT NULL DEFAULT '{}',
            enabled             INTEGER NOT NULL DEFAULT 1,
            cooldown_seconds    INTEGER NOT NULL DEFAULT 300,
            max_attempts_per_window INTEGER NOT NULL DEFAULT 3,
            window_seconds      INTEGER NOT NULL DEFAULT 3600,
            auto_disable_after_escalations INTEGER NOT NULL DEFAULT 3,
            auto_disable_window_hours      INTEGER NOT NULL DEFAULT 24,
            source              TEXT,
            source_evidence_json TEXT,
            last_attempt_at     TEXT,
            last_outcome        TEXT,
            total_executed      INTEGER NOT NULL DEFAULT 0,
            total_failed        INTEGER NOT NULL DEFAULT 0,
            total_escalated     INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_self_repair_patterns_trigger
            ON self_repair_patterns (enabled, trigger_event_kind)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS self_repair_attempts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id      TEXT NOT NULL,
            attempted_at    TEXT NOT NULL,
            triggered_by_event_id INTEGER,
            outcome         TEXT NOT NULL,
            error_summary   TEXT,
            elapsed_ms      INTEGER,
            FOREIGN KEY (pattern_id) REFERENCES self_repair_patterns (pattern_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_self_repair_attempts_pattern_time
            ON self_repair_attempts (pattern_id, attempted_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_self_repair_attempts_time
            ON self_repair_attempts (attempted_at DESC)
        """
    )


_INCREMENT_FIELDS = {
    "total_executed": "total_executed_increment",
    "total_failed": "total_failed_increment",
    "total_escalated": "total_escalated_increment",
}

_UPDATABLE_FIELDS = {
    "name",
    "trigger_event_kind",
    "trigger_match_json",
    "action_type",
    "action_params_json",
    "enabled",
    "cooldown_seconds",
    "max_attempts_per_window",
    "window_seconds",
    "auto_disable_after_escalations",
    "auto_disable_window_hours",
    "source",
    "source_evidence_json",
    "last_attempt_at",
    "last_outcome",
    "total_executed",
    "total_failed",
    "total_escalated",
}


def insert_self_repair_pattern(
    *,
    pattern_id: str,
    name: str,
    trigger_event_kind: str,
    trigger_match_json: str = "{}",
    action_type: str,
    action_params_json: str = "{}",
    enabled: bool = True,
    cooldown_seconds: int = 300,
    max_attempts_per_window: int = 3,
    window_seconds: int = 3600,
    auto_disable_after_escalations: int = 3,
    auto_disable_window_hours: int = 24,
    source: str | None = None,
    source_evidence_json: str | None = None,
) -> dict[str, object]:
    """UPSERT a self-repair pattern. Idempotent on pattern_id."""
    now = _now_iso()
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        conn.execute(
            """
            INSERT INTO self_repair_patterns
                (pattern_id, name, created_at, updated_at,
                 trigger_event_kind, trigger_match_json,
                 action_type, action_params_json,
                 enabled, cooldown_seconds, max_attempts_per_window,
                 window_seconds, auto_disable_after_escalations,
                 auto_disable_window_hours, source, source_evidence_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pattern_id) DO UPDATE SET
                name=excluded.name,
                updated_at=excluded.updated_at,
                trigger_event_kind=excluded.trigger_event_kind,
                trigger_match_json=excluded.trigger_match_json,
                action_type=excluded.action_type,
                action_params_json=excluded.action_params_json,
                enabled=excluded.enabled,
                cooldown_seconds=excluded.cooldown_seconds,
                max_attempts_per_window=excluded.max_attempts_per_window,
                window_seconds=excluded.window_seconds,
                auto_disable_after_escalations=excluded.auto_disable_after_escalations,
                auto_disable_window_hours=excluded.auto_disable_window_hours,
                source=excluded.source,
                source_evidence_json=excluded.source_evidence_json
            """,
            (
                str(pattern_id)[:120],
                str(name)[:240],
                now,
                now,
                str(trigger_event_kind)[:120],
                str(trigger_match_json or "{}"),
                str(action_type)[:60],
                str(action_params_json or "{}"),
                1 if enabled else 0,
                int(cooldown_seconds),
                int(max_attempts_per_window),
                int(window_seconds),
                int(auto_disable_after_escalations),
                int(auto_disable_window_hours),
                source,
                source_evidence_json,
            ),
        )
    return {"pattern_id": pattern_id, "created_at": now}


def get_self_repair_pattern(pattern_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        row = conn.execute(
            "SELECT * FROM self_repair_patterns WHERE pattern_id=?",
            (str(pattern_id),),
        ).fetchone()
    return _pattern_row_to_dict(row) if row is not None else None


def list_self_repair_patterns(
    *,
    enabled: bool | None = None,
    trigger_event_kind: str | None = None,
) -> list[dict[str, object]]:
    where: list[str] = []
    params: list[Any] = []
    if enabled is not None:
        where.append("enabled = ?")
        params.append(1 if enabled else 0)
    if trigger_event_kind:
        where.append("trigger_event_kind = ?")
        params.append(str(trigger_event_kind))
    sql = "SELECT * FROM self_repair_patterns"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at ASC"
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [_pattern_row_to_dict(r) for r in rows]


def update_self_repair_pattern(pattern_id: str, **fields: Any) -> bool:
    """Update specific fields. Supports `<field>_increment` for atomic counters.

    Returns True if a row was updated, False otherwise.
    """
    if not fields:
        return False

    set_clauses: list[str] = []
    params: list[Any] = []
    for key, value in fields.items():
        if key in _INCREMENT_FIELDS.values():
            target = next(
                target for target, inc_name in _INCREMENT_FIELDS.items()
                if inc_name == key
            )
            set_clauses.append(f"{target} = COALESCE({target}, 0) + ?")
            params.append(int(value))
        elif key in _UPDATABLE_FIELDS:
            if key == "enabled":
                set_clauses.append(f"{key} = ?")
                params.append(1 if value else 0)
            else:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        else:
            raise ValueError(f"unsupported field for update: {key!r}")

    set_clauses.append("updated_at = ?")
    params.append(_now_iso())
    params.append(str(pattern_id))

    with connect() as conn:
        _ensure_self_repair_tables(conn)
        cur = conn.execute(
            f"UPDATE self_repair_patterns SET {', '.join(set_clauses)} WHERE pattern_id=?",
            tuple(params),
        )
        return cur.rowcount > 0


def delete_self_repair_pattern(pattern_id: str) -> bool:
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        cur = conn.execute(
            "DELETE FROM self_repair_patterns WHERE pattern_id=?",
            (str(pattern_id),),
        )
        return cur.rowcount > 0


def insert_self_repair_attempt(
    *,
    pattern_id: str,
    attempted_at: str,
    triggered_by_event_id: int | None,
    outcome: str,
    error_summary: str | None,
    elapsed_ms: int,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        cur = conn.execute(
            """
            INSERT INTO self_repair_attempts
                (pattern_id, attempted_at, triggered_by_event_id,
                 outcome, error_summary, elapsed_ms)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(pattern_id),
                str(attempted_at),
                int(triggered_by_event_id) if triggered_by_event_id else None,
                str(outcome)[:40],
                error_summary[:240] if error_summary else None,
                int(elapsed_ms),
            ),
        )
        return {"id": int(cur.lastrowid), "attempted_at": attempted_at}


def count_recent_attempts(
    *,
    pattern_id: str,
    since_iso: str,
    outcome: str | None = None,
) -> int:
    where = ["pattern_id = ?", "attempted_at >= ?"]
    params: list[Any] = [str(pattern_id), str(since_iso)]
    if outcome is not None:
        where.append("outcome = ?")
        params.append(str(outcome))
    sql = "SELECT COUNT(*) AS n FROM self_repair_attempts WHERE " + " AND ".join(where)
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        row = conn.execute(sql, tuple(params)).fetchone()
    return int(row["n"]) if row else 0


def list_recent_self_repair_attempts(
    *, pattern_id: str | None = None, limit: int = 50,
) -> list[dict[str, object]]:
    where = ""
    params: list[Any] = []
    if pattern_id:
        where = "WHERE pattern_id = ?"
        params.append(str(pattern_id))
    sql = (
        "SELECT id, pattern_id, attempted_at, triggered_by_event_id, "
        "outcome, error_summary, elapsed_ms FROM self_repair_attempts "
        f"{where} ORDER BY attempted_at DESC LIMIT ?"
    )
    params.append(max(int(limit), 1))
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        {
            "id": int(r["id"]),
            "pattern_id": r["pattern_id"],
            "attempted_at": r["attempted_at"],
            "triggered_by_event_id": r["triggered_by_event_id"],
            "outcome": r["outcome"],
            "error_summary": r["error_summary"],
            "elapsed_ms": r["elapsed_ms"],
        }
        for r in rows
    ]


def _pattern_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "pattern_id": row["pattern_id"],
        "name": row["name"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "trigger_event_kind": row["trigger_event_kind"],
        "trigger_match_json": row["trigger_match_json"],
        "action_type": row["action_type"],
        "action_params_json": row["action_params_json"],
        "enabled": int(row["enabled"]),
        "cooldown_seconds": int(row["cooldown_seconds"]),
        "max_attempts_per_window": int(row["max_attempts_per_window"]),
        "window_seconds": int(row["window_seconds"]),
        "auto_disable_after_escalations": int(row["auto_disable_after_escalations"]),
        "auto_disable_window_hours": int(row["auto_disable_window_hours"]),
        "source": row["source"],
        "source_evidence_json": row["source_evidence_json"],
        "last_attempt_at": row["last_attempt_at"],
        "last_outcome": row["last_outcome"],
        "total_executed": int(row["total_executed"]),
        "total_failed": int(row["total_failed"]),
        "total_escalated": int(row["total_escalated"]),
    }
