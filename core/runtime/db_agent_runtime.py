"""Persistence for Jarvis' agent + council runtime cluster.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
the seven agent/council tables (agent_registry, agent_runs, agent_messages,
agent_tool_calls, agent_schedules, council_sessions, council_members) via the
lazily-invoked `_ensure_agent_runtime_tables`, plus all CRUD and the private
row-mapper helpers for the cluster. The ensure-function is called lazily by the
CRUD functions themselves (never by init_db), so the cluster is self-contained.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect, _now_iso


def _ensure_agent_runtime_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_registry (
            agent_id TEXT PRIMARY KEY,
            parent_agent_id TEXT NOT NULL DEFAULT '',
            owner_agent_id TEXT NOT NULL DEFAULT 'jarvis',
            council_id TEXT NOT NULL DEFAULT '',
            kind TEXT NOT NULL DEFAULT 'subagent',
            role TEXT NOT NULL DEFAULT '',
            goal TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'planned',
            lane TEXT NOT NULL DEFAULT 'cheap',
            provider TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            system_prompt TEXT NOT NULL DEFAULT '',
            system_prompt_version TEXT NOT NULL DEFAULT 'v1',
            tool_policy TEXT NOT NULL DEFAULT 'none',
            allowed_tools_json TEXT NOT NULL DEFAULT '[]',
            persistent INTEGER NOT NULL DEFAULT 0,
            ttl_seconds INTEGER NOT NULL DEFAULT 0,
            schedule_json TEXT NOT NULL DEFAULT '{}',
            next_wake_at TEXT NOT NULL DEFAULT '',
            budget_tokens INTEGER NOT NULL DEFAULT 0,
            tokens_burned INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT NOT NULL DEFAULT '',
            context_json TEXT NOT NULL DEFAULT '{}',
            result_contract_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT NOT NULL DEFAULT '',
            expired_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_registry_status_updated
        ON agent_registry(status, updated_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_runs (
            run_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            execution_mode TEXT NOT NULL DEFAULT 'solo-task',
            provider TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            input_summary TEXT NOT NULL DEFAULT '',
            output_summary TEXT NOT NULL DEFAULT '',
            input_payload_json TEXT NOT NULL DEFAULT '{}',
            output_payload_json TEXT NOT NULL DEFAULT '{}',
            started_at TEXT NOT NULL DEFAULT '',
            finished_at TEXT NOT NULL DEFAULT '',
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0,
            provider_status TEXT NOT NULL DEFAULT '',
            failure_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_created
        ON agent_runs(agent_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_messages (
            message_id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            council_id TEXT NOT NULL DEFAULT '',
            agent_id TEXT NOT NULL DEFAULT '',
            peer_agent_id TEXT NOT NULL DEFAULT '',
            direction TEXT NOT NULL DEFAULT 'agent->jarvis',
            role TEXT NOT NULL DEFAULT 'assistant',
            content TEXT NOT NULL DEFAULT '',
            kind TEXT NOT NULL DEFAULT 'message',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_messages_thread_created
        ON agent_messages(thread_id, created_at ASC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_tool_calls (
            tool_call_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            arguments_json TEXT NOT NULL DEFAULT '{}',
            result_preview TEXT NOT NULL DEFAULT '',
            started_at TEXT NOT NULL DEFAULT '',
            finished_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_run_created
        ON agent_tool_calls(run_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_schedules (
            schedule_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            schedule_kind TEXT NOT NULL DEFAULT 'manual',
            schedule_expr TEXT NOT NULL DEFAULT '',
            next_fire_at TEXT NOT NULL DEFAULT '',
            last_fire_at TEXT NOT NULL DEFAULT '',
            missed_run_policy TEXT NOT NULL DEFAULT 'fire-once',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS council_sessions (
            council_id TEXT PRIMARY KEY,
            owner_agent_id TEXT NOT NULL DEFAULT 'jarvis',
            topic TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'forming',
            mode TEXT NOT NULL DEFAULT 'council',
            summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            finished_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS council_members (
            council_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT '',
            position_summary TEXT NOT NULL DEFAULT '',
            vote TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            PRIMARY KEY (council_id, agent_id)
        )
        """
    )


def create_agent_registry_entry(
    *,
    agent_id: str,
    parent_agent_id: str = "",
    owner_agent_id: str = "jarvis",
    council_id: str = "",
    kind: str = "subagent",
    role: str = "",
    goal: str = "",
    status: str = "planned",
    lane: str = "cheap",
    provider: str = "",
    model: str = "",
    system_prompt: str = "",
    system_prompt_version: str = "v1",
    tool_policy: str = "none",
    allowed_tools_json: str = "[]",
    persistent: bool = False,
    ttl_seconds: int = 0,
    schedule_json: str = "{}",
    next_wake_at: str = "",
    budget_tokens: int = 0,
    tokens_burned: int = 0,
    failure_count: int = 0,
    last_error: str = "",
    context_json: str = "{}",
    result_contract_json: str = "{}",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            """
            INSERT INTO agent_registry (
                agent_id, parent_agent_id, owner_agent_id, council_id, kind, role, goal,
                status, lane, provider, model, system_prompt, system_prompt_version,
                tool_policy, allowed_tools_json, persistent, ttl_seconds, schedule_json,
                next_wake_at, budget_tokens, tokens_burned, failure_count, last_error,
                context_json, result_contract_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent_id,
                parent_agent_id,
                owner_agent_id,
                council_id,
                kind,
                role,
                goal,
                status,
                lane,
                provider,
                model,
                system_prompt,
                system_prompt_version,
                tool_policy,
                allowed_tools_json,
                1 if persistent else 0,
                int(ttl_seconds),
                schedule_json,
                next_wake_at,
                int(budget_tokens),
                int(tokens_burned),
                int(failure_count),
                last_error,
                context_json,
                result_contract_json,
                now,
                now,
            ),
        )
        conn.commit()
    return get_agent_registry_entry(agent_id) or {}


def get_agent_registry_entry(agent_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        row = conn.execute(
            "SELECT * FROM agent_registry WHERE agent_id = ? LIMIT 1",
            (agent_id,),
        ).fetchone()
    if row is None:
        return None
    return _agent_registry_row_to_dict(row)


def update_agent_registry_entry(
    agent_id: str,
    *,
    status: str | None = None,
    next_wake_at: str | None = None,
    schedule_json: str | None = None,
    tokens_burned_delta: int = 0,
    failure_increment: int = 0,
    last_error: str | None = None,
    completed_at: str | None = None,
    expired_at: str | None = None,
) -> dict[str, object] | None:
    fields: list[str] = ["updated_at = ?"]
    values: list[object] = [_now_iso()]
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if next_wake_at is not None:
        fields.append("next_wake_at = ?")
        values.append(next_wake_at)
    if schedule_json is not None:
        fields.append("schedule_json = ?")
        values.append(schedule_json)
    if tokens_burned_delta:
        fields.append("tokens_burned = tokens_burned + ?")
        values.append(int(tokens_burned_delta))
    if failure_increment:
        fields.append("failure_count = failure_count + ?")
        values.append(int(failure_increment))
    if last_error is not None:
        fields.append("last_error = ?")
        values.append(last_error)
    if completed_at is not None:
        fields.append("completed_at = ?")
        values.append(completed_at)
    if expired_at is not None:
        fields.append("expired_at = ?")
        values.append(expired_at)
    values.append(agent_id)
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            f"UPDATE agent_registry SET {', '.join(fields)} WHERE agent_id = ?",
            tuple(values),
        )
        conn.commit()
    return get_agent_registry_entry(agent_id)


def list_agent_registry_entries(
    *,
    status: str = "",
    include_completed: bool = True,
    limit: int = 100,
) -> list[dict[str, object]]:
    query = ["SELECT * FROM agent_registry WHERE 1=1"]
    params: list[object] = []
    if status:
        query.append("AND status = ?")
        params.append(status)
    if not include_completed:
        query.append("AND status NOT IN ('completed', 'cancelled', 'expired')")
    query.append("ORDER BY updated_at DESC, created_at DESC LIMIT ?")
    params.append(int(limit))
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        rows = conn.execute("\n".join(query), tuple(params)).fetchall()
    return [_agent_registry_row_to_dict(row) for row in rows]


def create_agent_run(
    *,
    run_id: str,
    agent_id: str,
    status: str = "queued",
    execution_mode: str = "solo-task",
    provider: str = "",
    model: str = "",
    input_summary: str = "",
    output_summary: str = "",
    input_payload_json: str = "{}",
    output_payload_json: str = "{}",
    started_at: str = "",
    finished_at: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    provider_status: str = "",
    failure_reason: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            """
            INSERT INTO agent_runs (
                run_id, agent_id, status, execution_mode, provider, model,
                input_summary, output_summary, input_payload_json, output_payload_json,
                started_at, finished_at, input_tokens, output_tokens, cost_usd,
                provider_status, failure_reason, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                agent_id,
                status,
                execution_mode,
                provider,
                model,
                input_summary,
                output_summary,
                input_payload_json,
                output_payload_json,
                started_at,
                finished_at,
                int(input_tokens),
                int(output_tokens),
                float(cost_usd),
                provider_status,
                failure_reason,
                now,
                now,
            ),
        )
        conn.commit()
    return get_agent_run(run_id) or {}


def get_agent_run(run_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        row = conn.execute(
            "SELECT * FROM agent_runs WHERE run_id = ? LIMIT 1",
            (run_id,),
        ).fetchone()
    if row is None:
        return None
    return _agent_run_row_to_dict(row)


def update_agent_run(
    run_id: str,
    *,
    status: str | None = None,
    output_summary: str | None = None,
    output_payload_json: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost_usd: float | None = None,
    provider_status: str | None = None,
    failure_reason: str | None = None,
) -> dict[str, object] | None:
    fields = ["updated_at = ?"]
    values: list[object] = [_now_iso()]
    for name, value in (
        ("status", status),
        ("output_summary", output_summary),
        ("output_payload_json", output_payload_json),
        ("started_at", started_at),
        ("finished_at", finished_at),
        ("input_tokens", input_tokens),
        ("output_tokens", output_tokens),
        ("cost_usd", cost_usd),
        ("provider_status", provider_status),
        ("failure_reason", failure_reason),
    ):
        if value is None:
            continue
        fields.append(f"{name} = ?")
        values.append(value)
    values.append(run_id)
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            f"UPDATE agent_runs SET {', '.join(fields)} WHERE run_id = ?",
            tuple(values),
        )
        conn.commit()
    return get_agent_run(run_id)


def list_agent_runs(*, agent_id: str = "", limit: int = 50) -> list[dict[str, object]]:
    query = ["SELECT * FROM agent_runs WHERE 1=1"]
    params: list[object] = []
    if agent_id:
        query.append("AND agent_id = ?")
        params.append(agent_id)
    query.append("ORDER BY created_at DESC LIMIT ?")
    params.append(int(limit))
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        rows = conn.execute("\n".join(query), tuple(params)).fetchall()
    return [_agent_run_row_to_dict(row) for row in rows]


def create_agent_message(
    *,
    message_id: str,
    thread_id: str,
    run_id: str = "",
    council_id: str = "",
    agent_id: str = "",
    peer_agent_id: str = "",
    direction: str = "agent->jarvis",
    role: str = "assistant",
    content: str = "",
    kind: str = "message",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            """
            INSERT INTO agent_messages (
                message_id, thread_id, run_id, council_id, agent_id, peer_agent_id,
                direction, role, content, kind, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                thread_id,
                run_id,
                council_id,
                agent_id,
                peer_agent_id,
                direction,
                role,
                content,
                kind,
                now,
            ),
        )
        conn.commit()
    return get_agent_message(message_id) or {}


def get_agent_message(message_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        row = conn.execute(
            "SELECT * FROM agent_messages WHERE message_id = ? LIMIT 1",
            (message_id,),
        ).fetchone()
    if row is None:
        return None
    return _agent_message_row_to_dict(row)


def list_agent_messages(
    *,
    thread_id: str = "",
    run_id: str = "",
    council_id: str = "",
    agent_id: str = "",
    limit: int = 200,
) -> list[dict[str, object]]:
    query = ["SELECT * FROM agent_messages WHERE 1=1"]
    params: list[object] = []
    if thread_id:
        query.append("AND thread_id = ?")
        params.append(thread_id)
    if run_id:
        query.append("AND run_id = ?")
        params.append(run_id)
    if council_id:
        query.append("AND council_id = ?")
        params.append(council_id)
    if agent_id:
        query.append("AND agent_id = ?")
        params.append(agent_id)
    query.append("ORDER BY created_at ASC LIMIT ?")
    params.append(int(limit))
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        rows = conn.execute("\n".join(query), tuple(params)).fetchall()
    return [_agent_message_row_to_dict(row) for row in rows]


def create_agent_tool_call(
    *,
    tool_call_id: str,
    run_id: str,
    agent_id: str,
    tool_name: str,
    status: str = "queued",
    arguments_json: str = "{}",
    result_preview: str = "",
    started_at: str = "",
    finished_at: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            """
            INSERT INTO agent_tool_calls (
                tool_call_id, run_id, agent_id, tool_name, status, arguments_json,
                result_preview, started_at, finished_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tool_call_id,
                run_id,
                agent_id,
                tool_name,
                status,
                arguments_json,
                result_preview,
                started_at,
                finished_at,
                now,
            ),
        )
        conn.commit()
    return get_agent_tool_call(tool_call_id) or {}


def get_agent_tool_call(tool_call_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        row = conn.execute(
            "SELECT * FROM agent_tool_calls WHERE tool_call_id = ? LIMIT 1",
            (tool_call_id,),
        ).fetchone()
    if row is None:
        return None
    return _agent_tool_call_row_to_dict(row)


def list_agent_tool_calls(*, run_id: str = "", agent_id: str = "", limit: int = 100) -> list[dict[str, object]]:
    query = ["SELECT * FROM agent_tool_calls WHERE 1=1"]
    params: list[object] = []
    if run_id:
        query.append("AND run_id = ?")
        params.append(run_id)
    if agent_id:
        query.append("AND agent_id = ?")
        params.append(agent_id)
    query.append("ORDER BY created_at DESC LIMIT ?")
    params.append(int(limit))
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        rows = conn.execute("\n".join(query), tuple(params)).fetchall()
    return [_agent_tool_call_row_to_dict(row) for row in rows]


def create_agent_schedule(
    *,
    schedule_id: str,
    agent_id: str,
    schedule_kind: str = "manual",
    schedule_expr: str = "",
    next_fire_at: str = "",
    last_fire_at: str = "",
    missed_run_policy: str = "fire-once",
    active: bool = True,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            """
            INSERT INTO agent_schedules (
                schedule_id, agent_id, schedule_kind, schedule_expr, next_fire_at,
                last_fire_at, missed_run_policy, active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(schedule_id) DO UPDATE SET
                agent_id = excluded.agent_id,
                schedule_kind = excluded.schedule_kind,
                schedule_expr = excluded.schedule_expr,
                next_fire_at = excluded.next_fire_at,
                last_fire_at = excluded.last_fire_at,
                missed_run_policy = excluded.missed_run_policy,
                active = excluded.active,
                updated_at = excluded.updated_at
            """,
            (
                schedule_id,
                agent_id,
                schedule_kind,
                schedule_expr,
                next_fire_at,
                last_fire_at,
                missed_run_policy,
                1 if active else 0,
                now,
                now,
            ),
        )
        conn.commit()
    return get_agent_schedule(schedule_id) or {}


def get_agent_schedule(schedule_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        row = conn.execute(
            "SELECT * FROM agent_schedules WHERE schedule_id = ? LIMIT 1",
            (schedule_id,),
        ).fetchone()
    if row is None:
        return None
    return _agent_schedule_row_to_dict(row)


def update_agent_schedule(
    schedule_id: str,
    *,
    schedule_expr: str | None = None,
    next_fire_at: str | None = None,
    last_fire_at: str | None = None,
    active: bool | None = None,
) -> dict[str, object] | None:
    fields = ["updated_at = ?"]
    values: list[object] = [_now_iso()]
    for name, value in (
        ("schedule_expr", schedule_expr),
        ("next_fire_at", next_fire_at),
        ("last_fire_at", last_fire_at),
    ):
        if value is None:
            continue
        fields.append(f"{name} = ?")
        values.append(value)
    if active is not None:
        fields.append("active = ?")
        values.append(1 if active else 0)
    values.append(schedule_id)
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            f"UPDATE agent_schedules SET {', '.join(fields)} WHERE schedule_id = ?",
            tuple(values),
        )
        conn.commit()
    return get_agent_schedule(schedule_id)


def list_agent_schedules(*, agent_id: str = "", active_only: bool = False, due_before: str = "", limit: int = 100) -> list[dict[str, object]]:
    query = ["SELECT * FROM agent_schedules WHERE 1=1"]
    params: list[object] = []
    if agent_id:
        query.append("AND agent_id = ?")
        params.append(agent_id)
    if active_only:
        query.append("AND active = 1")
    if due_before:
        query.append("AND next_fire_at != '' AND next_fire_at <= ?")
        params.append(due_before)
    query.append("ORDER BY next_fire_at ASC, created_at ASC LIMIT ?")
    params.append(int(limit))
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        rows = conn.execute("\n".join(query), tuple(params)).fetchall()
    return [_agent_schedule_row_to_dict(row) for row in rows]


def create_council_session(
    *,
    council_id: str,
    owner_agent_id: str = "jarvis",
    topic: str = "",
    status: str = "forming",
    mode: str = "council",
    summary: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            """
            INSERT INTO council_sessions (
                council_id, owner_agent_id, topic, status, mode, summary,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (council_id, owner_agent_id, topic, status, mode, summary, now, now),
        )
        conn.commit()
    return get_council_session(council_id) or {}


def get_council_session(council_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        row = conn.execute(
            "SELECT * FROM council_sessions WHERE council_id = ? LIMIT 1",
            (council_id,),
        ).fetchone()
    if row is None:
        return None
    session = _council_session_row_to_dict(row)
    session["members"] = list_council_members(council_id=council_id)
    return session


def update_council_session(
    council_id: str,
    *,
    status: str | None = None,
    summary: str | None = None,
    finished_at: str | None = None,
) -> dict[str, object] | None:
    fields = ["updated_at = ?"]
    values: list[object] = [_now_iso()]
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if summary is not None:
        fields.append("summary = ?")
        values.append(summary)
    if finished_at is not None:
        fields.append("finished_at = ?")
        values.append(finished_at)
    values.append(council_id)
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            f"UPDATE council_sessions SET {', '.join(fields)} WHERE council_id = ?",
            tuple(values),
        )
        conn.commit()
    return get_council_session(council_id)


def list_council_sessions(limit: int = 50) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        rows = conn.execute(
            "SELECT * FROM council_sessions ORDER BY updated_at DESC, created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    sessions = [_council_session_row_to_dict(row) for row in rows]
    for item in sessions:
        item["members"] = list_council_members(council_id=str(item["council_id"]))
    return sessions


def add_council_member(
    *,
    council_id: str,
    agent_id: str,
    role: str,
    position_summary: str = "",
    vote: str = "",
    confidence: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            """
            INSERT INTO council_members (
                council_id, agent_id, role, position_summary, vote, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(council_id, agent_id) DO UPDATE SET
                role = excluded.role,
                position_summary = excluded.position_summary,
                vote = excluded.vote,
                confidence = excluded.confidence
            """,
            (council_id, agent_id, role, position_summary, vote, confidence, now),
        )
        conn.commit()
    return get_council_member(council_id=council_id, agent_id=agent_id) or {}


def update_council_member(
    *,
    council_id: str,
    agent_id: str,
    position_summary: str | None = None,
    vote: str | None = None,
    confidence: str | None = None,
) -> dict[str, object] | None:
    fields = []
    values: list[object] = []
    for name, value in (
        ("position_summary", position_summary),
        ("vote", vote),
        ("confidence", confidence),
    ):
        if value is None:
            continue
        fields.append(f"{name} = ?")
        values.append(value)
    if not fields:
        return get_council_member(council_id=council_id, agent_id=agent_id)
    values.extend([council_id, agent_id])
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        conn.execute(
            f"UPDATE council_members SET {', '.join(fields)} WHERE council_id = ? AND agent_id = ?",
            tuple(values),
        )
        conn.commit()
    return get_council_member(council_id=council_id, agent_id=agent_id)


def get_council_member(*, council_id: str, agent_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        row = conn.execute(
            "SELECT * FROM council_members WHERE council_id = ? AND agent_id = ? LIMIT 1",
            (council_id, agent_id),
        ).fetchone()
    if row is None:
        return None
    return _council_member_row_to_dict(row)


def list_council_members(*, council_id: str) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_agent_runtime_tables(conn)
        rows = conn.execute(
            "SELECT * FROM council_members WHERE council_id = ? ORDER BY created_at ASC",
            (council_id,),
        ).fetchall()
    return [_council_member_row_to_dict(row) for row in rows]


def _agent_registry_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "agent_id": str(row["agent_id"]),
        "parent_agent_id": str(row["parent_agent_id"]),
        "owner_agent_id": str(row["owner_agent_id"]),
        "council_id": str(row["council_id"]),
        "kind": str(row["kind"]),
        "role": str(row["role"]),
        "goal": str(row["goal"]),
        "status": str(row["status"]),
        "lane": str(row["lane"]),
        "provider": str(row["provider"]),
        "model": str(row["model"]),
        "system_prompt": str(row["system_prompt"]),
        "system_prompt_version": str(row["system_prompt_version"]),
        "tool_policy": str(row["tool_policy"]),
        "allowed_tools_json": str(row["allowed_tools_json"]),
        "persistent": bool(row["persistent"]),
        "ttl_seconds": int(row["ttl_seconds"]),
        "schedule_json": str(row["schedule_json"]),
        "next_wake_at": str(row["next_wake_at"]),
        "budget_tokens": int(row["budget_tokens"]),
        "tokens_burned": int(row["tokens_burned"]),
        "failure_count": int(row["failure_count"]),
        "last_error": str(row["last_error"]),
        "context_json": str(row["context_json"]),
        "result_contract_json": str(row["result_contract_json"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "completed_at": str(row["completed_at"]),
        "expired_at": str(row["expired_at"]),
    }


def _agent_run_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "run_id": str(row["run_id"]),
        "agent_id": str(row["agent_id"]),
        "status": str(row["status"]),
        "execution_mode": str(row["execution_mode"]),
        "provider": str(row["provider"]),
        "model": str(row["model"]),
        "input_summary": str(row["input_summary"]),
        "output_summary": str(row["output_summary"]),
        "input_payload_json": str(row["input_payload_json"]),
        "output_payload_json": str(row["output_payload_json"]),
        "started_at": str(row["started_at"]),
        "finished_at": str(row["finished_at"]),
        "input_tokens": int(row["input_tokens"]),
        "output_tokens": int(row["output_tokens"]),
        "cost_usd": float(row["cost_usd"]),
        "provider_status": str(row["provider_status"]),
        "failure_reason": str(row["failure_reason"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _agent_message_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "message_id": str(row["message_id"]),
        "thread_id": str(row["thread_id"]),
        "run_id": str(row["run_id"]),
        "council_id": str(row["council_id"]),
        "agent_id": str(row["agent_id"]),
        "peer_agent_id": str(row["peer_agent_id"]),
        "direction": str(row["direction"]),
        "role": str(row["role"]),
        "content": str(row["content"]),
        "kind": str(row["kind"]),
        "created_at": str(row["created_at"]),
    }


def _agent_tool_call_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "tool_call_id": str(row["tool_call_id"]),
        "run_id": str(row["run_id"]),
        "agent_id": str(row["agent_id"]),
        "tool_name": str(row["tool_name"]),
        "status": str(row["status"]),
        "arguments_json": str(row["arguments_json"]),
        "result_preview": str(row["result_preview"]),
        "started_at": str(row["started_at"]),
        "finished_at": str(row["finished_at"]),
        "created_at": str(row["created_at"]),
    }


def _agent_schedule_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "schedule_id": str(row["schedule_id"]),
        "agent_id": str(row["agent_id"]),
        "schedule_kind": str(row["schedule_kind"]),
        "schedule_expr": str(row["schedule_expr"]),
        "next_fire_at": str(row["next_fire_at"]),
        "last_fire_at": str(row["last_fire_at"]),
        "missed_run_policy": str(row["missed_run_policy"]),
        "active": bool(row["active"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _council_session_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "council_id": str(row["council_id"]),
        "owner_agent_id": str(row["owner_agent_id"]),
        "topic": str(row["topic"]),
        "status": str(row["status"]),
        "mode": str(row["mode"]),
        "summary": str(row["summary"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "finished_at": str(row["finished_at"]),
    }


def _council_member_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "council_id": str(row["council_id"]),
        "agent_id": str(row["agent_id"]),
        "role": str(row["role"]),
        "position_summary": str(row["position_summary"]),
        "vote": str(row["vote"]),
        "confidence": str(row["confidence"]),
        "created_at": str(row["created_at"]),
    }
