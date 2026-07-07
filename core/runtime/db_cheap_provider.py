"""Persistence for the cheap-provider runtime-state + invocation cluster.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema and
CRUD for the two cheap-lane tables (cheap_provider_runtime_state and
cheap_provider_invocations). Both tables are created inline via
`CREATE TABLE IF NOT EXISTS` inside each function (no separate _ensure_*
helper and no init_db coupling), so the cluster is fully self-contained.
"""
from __future__ import annotations

from core.runtime.db_core import connect, _now_iso


def upsert_cheap_provider_runtime_state(
    *,
    provider: str,
    model: str = "",
    lane: str = "cheap",
    status: str = "",
    auth_ready: bool = False,
    quota_limited: bool = False,
    cooldown_until: str | None = None,
    last_error_code: str = "",
    last_error_message: str = "",
    last_success_at: str | None = None,
    last_failure_at: str | None = None,
    metadata_json: str = "{}",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cheap_provider_runtime_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                lane TEXT NOT NULL DEFAULT 'cheap',
                status TEXT NOT NULL DEFAULT '',
                auth_ready INTEGER NOT NULL DEFAULT 0,
                quota_limited INTEGER NOT NULL DEFAULT 0,
                cooldown_until TEXT,
                last_error_code TEXT NOT NULL DEFAULT '',
                last_error_message TEXT NOT NULL DEFAULT '',
                last_success_at TEXT,
                last_failure_at TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                UNIQUE(provider, model, lane)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO cheap_provider_runtime_state (
                provider, model, lane, status, auth_ready, quota_limited,
                cooldown_until, last_error_code, last_error_message,
                last_success_at, last_failure_at, metadata_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, model, lane) DO UPDATE SET
                status=excluded.status,
                auth_ready=excluded.auth_ready,
                quota_limited=excluded.quota_limited,
                cooldown_until=excluded.cooldown_until,
                last_error_code=excluded.last_error_code,
                last_error_message=excluded.last_error_message,
                last_success_at=COALESCE(excluded.last_success_at, cheap_provider_runtime_state.last_success_at),
                last_failure_at=COALESCE(excluded.last_failure_at, cheap_provider_runtime_state.last_failure_at),
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
            """,
            (
                provider,
                model,
                lane,
                status,
                int(auth_ready),
                int(quota_limited),
                cooldown_until,
                last_error_code,
                last_error_message,
                last_success_at,
                last_failure_at,
                metadata_json,
                now,
            ),
        )
        conn.commit()
    return {
        "provider": provider,
        "model": model,
        "lane": lane,
        "status": status,
        "auth_ready": bool(auth_ready),
        "quota_limited": bool(quota_limited),
        "cooldown_until": cooldown_until,
        "last_error_code": last_error_code,
        "last_error_message": last_error_message,
        "last_success_at": last_success_at,
        "last_failure_at": last_failure_at,
        "metadata_json": metadata_json,
        "updated_at": now,
    }


def get_cheap_provider_runtime_state(
    *,
    provider: str,
    model: str = "",
    lane: str = "cheap",
) -> dict[str, object] | None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cheap_provider_runtime_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                lane TEXT NOT NULL DEFAULT 'cheap',
                status TEXT NOT NULL DEFAULT '',
                auth_ready INTEGER NOT NULL DEFAULT 0,
                quota_limited INTEGER NOT NULL DEFAULT 0,
                cooldown_until TEXT,
                last_error_code TEXT NOT NULL DEFAULT '',
                last_error_message TEXT NOT NULL DEFAULT '',
                last_success_at TEXT,
                last_failure_at TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                UNIQUE(provider, model, lane)
            )
            """
        )
        row = conn.execute(
            """
            SELECT *
            FROM cheap_provider_runtime_state
            WHERE provider = ? AND model = ? AND lane = ?
            LIMIT 1
            """,
            (provider, model, lane),
        ).fetchone()
    if row is None:
        return None
    return {
        "provider": str(row["provider"]),
        "model": str(row["model"]),
        "lane": str(row["lane"]),
        "status": str(row["status"]),
        "auth_ready": bool(row["auth_ready"]),
        "quota_limited": bool(row["quota_limited"]),
        "cooldown_until": row["cooldown_until"],
        "last_error_code": str(row["last_error_code"]),
        "last_error_message": str(row["last_error_message"]),
        "last_success_at": row["last_success_at"],
        "last_failure_at": row["last_failure_at"],
        "metadata_json": str(row["metadata_json"]),
        "updated_at": str(row["updated_at"]),
    }


def list_cheap_provider_runtime_states(*, lane: str = "cheap") -> list[dict[str, object]]:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cheap_provider_runtime_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                lane TEXT NOT NULL DEFAULT 'cheap',
                status TEXT NOT NULL DEFAULT '',
                auth_ready INTEGER NOT NULL DEFAULT 0,
                quota_limited INTEGER NOT NULL DEFAULT 0,
                cooldown_until TEXT,
                last_error_code TEXT NOT NULL DEFAULT '',
                last_error_message TEXT NOT NULL DEFAULT '',
                last_success_at TEXT,
                last_failure_at TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                UNIQUE(provider, model, lane)
            )
            """
        )
        rows = conn.execute(
            """
            SELECT *
            FROM cheap_provider_runtime_state
            WHERE lane = ?
            ORDER BY provider ASC, model ASC, id DESC
            """,
            (lane,),
        ).fetchall()
    return [
        {
            "provider": str(row["provider"]),
            "model": str(row["model"]),
            "lane": str(row["lane"]),
            "status": str(row["status"]),
            "auth_ready": bool(row["auth_ready"]),
            "quota_limited": bool(row["quota_limited"]),
            "cooldown_until": row["cooldown_until"],
            "last_error_code": str(row["last_error_code"]),
            "last_error_message": str(row["last_error_message"]),
            "last_success_at": row["last_success_at"],
            "last_failure_at": row["last_failure_at"],
            "metadata_json": str(row["metadata_json"]),
            "updated_at": str(row["updated_at"]),
        }
        for row in rows
    ]


def record_cheap_provider_invocation(
    *,
    provider: str,
    model: str = "",
    lane: str = "cheap",
    status: str,
    error_code: str = "",
    error_message: str = "",
    retry_after_seconds: int = 0,
    latency_ms: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cheap_provider_invocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lane TEXT NOT NULL DEFAULT 'cheap',
                provider TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                error_code TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                retry_after_seconds INTEGER NOT NULL DEFAULT 0,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor = conn.execute(
            """
            INSERT INTO cheap_provider_invocations (
                lane, provider, model, status, error_code, error_message,
                retry_after_seconds, latency_ms, input_tokens, output_tokens,
                cost_usd, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lane,
                provider,
                model,
                status,
                error_code,
                error_message,
                int(retry_after_seconds),
                int(latency_ms),
                int(input_tokens),
                int(output_tokens),
                float(cost_usd),
                now,
            ),
        )
        conn.commit()
        row_id = int(cursor.lastrowid)
    return {
        "id": row_id,
        "lane": lane,
        "provider": provider,
        "model": model,
        "status": status,
        "error_code": error_code,
        "error_message": error_message,
        "retry_after_seconds": int(retry_after_seconds),
        "latency_ms": int(latency_ms),
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "cost_usd": float(cost_usd),
        "created_at": now,
    }


def count_cheap_provider_invocations(
    *,
    provider: str,
    lane: str = "cheap",
    since: str,
    status: str | None = None,
) -> int:
    query = [
        "SELECT COUNT(*) AS count FROM cheap_provider_invocations",
        "WHERE provider = ? AND lane = ? AND created_at >= ?",
    ]
    params: list[object] = [provider, lane, since]
    if status is not None:
        query.append("AND status = ?")
        params.append(status)
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cheap_provider_invocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lane TEXT NOT NULL DEFAULT 'cheap',
                provider TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                error_code TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                retry_after_seconds INTEGER NOT NULL DEFAULT 0,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        row = conn.execute("\n".join(query), tuple(params)).fetchone()
    return int(row["count"]) if row else 0

