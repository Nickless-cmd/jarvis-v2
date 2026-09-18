"""Durable observability storage for the Cheap Lane control center."""
from __future__ import annotations

import base64
import binascii
import json
from typing import Any
from uuid import uuid4

from core.runtime.db_cheap_provider import _ensure_invocation_schema
from core.runtime.db_core import _now_iso, connect

_MAX_JSON_BYTES = 64 * 1024
_MAX_CANDIDATES = 100
_MAX_PAGE_SIZE = 500


def _bounded_json(value: object, *, max_bytes: int = _MAX_JSON_BYTES) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError(f"JSON payload exceeds {max_bytes} bytes")
    return encoded


def _decode_json(value: object, fallback: object) -> object:
    try:
        return json.loads(str(value or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def _ensure_control_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cheap_lane_route_decisions (
            route_decision_id TEXT PRIMARY KEY,
            correlation_id TEXT NOT NULL,
            task_kind TEXT NOT NULL DEFAULT '',
            daemon TEXT NOT NULL DEFAULT '',
            candidates_json TEXT NOT NULL DEFAULT '[]',
            selected_slot_id TEXT NOT NULL DEFAULT '',
            selection_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cheap_route_correlation
            ON cheap_lane_route_decisions(correlation_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS cheap_lane_quota_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            auth_profile TEXT NOT NULL DEFAULT 'default',
            period TEXT NOT NULL,
            unit TEXT NOT NULL,
            quota_limit REAL,
            remaining REAL,
            reset_at TEXT,
            observed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cheap_quota_scope
            ON cheap_lane_quota_observations(
                provider, auth_profile, period, unit, observed_at DESC
            );

        CREATE TABLE IF NOT EXISTS cheap_lane_audit (
            audit_id TEXT PRIMARY KEY,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            before_json TEXT NOT NULL DEFAULT '{}',
            after_json TEXT NOT NULL DEFAULT '{}',
            result TEXT NOT NULL,
            error_code TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cheap_audit_created
            ON cheap_lane_audit(created_at DESC, audit_id DESC);

        CREATE TABLE IF NOT EXISTS cheap_lane_redacted_payloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invocation_id TEXT NOT NULL UNIQUE,
            prompt TEXT,
            response TEXT,
            status TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cheap_payload_expiry
            ON cheap_lane_redacted_payloads(expires_at);
        """
    )


def record_route_decision(
    *,
    correlation_id: str,
    task_kind: str,
    daemon: str,
    candidates: list[dict[str, object]],
    selected_slot_id: str,
    selection_reason: str,
) -> str:
    if len(candidates) > _MAX_CANDIDATES:
        raise ValueError(f"candidate trace exceeds {_MAX_CANDIDATES} items")
    route_id = str(uuid4())
    now = _now_iso()
    with connect() as conn:
        _ensure_control_schema(conn)
        conn.execute(
            """
            INSERT INTO cheap_lane_route_decisions (
                route_decision_id, correlation_id, task_kind, daemon,
                candidates_json, selected_slot_id, selection_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                route_id,
                correlation_id,
                task_kind,
                daemon,
                _bounded_json(candidates),
                selected_slot_id,
                selection_reason,
                now,
            ),
        )
        conn.commit()
    return route_id


def get_route_decision(route_decision_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_control_schema(conn)
        row = conn.execute(
            "SELECT * FROM cheap_lane_route_decisions WHERE route_decision_id = ?",
            (route_decision_id,),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["candidates"] = _decode_json(result.pop("candidates_json", "[]"), [])
    return result


def record_quota_observation(
    *,
    provider: str,
    auth_profile: str,
    period: str,
    unit: str,
    limit: float | None,
    remaining: float | None,
    reset_at: str | None,
    observed_at: str | None = None,
) -> int:
    with connect() as conn:
        _ensure_control_schema(conn)
        cursor = conn.execute(
            """
            INSERT INTO cheap_lane_quota_observations (
                provider, auth_profile, period, unit, quota_limit, remaining,
                reset_at, observed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider,
                auth_profile or "default",
                period,
                unit,
                limit,
                remaining,
                reset_at,
                observed_at or _now_iso(),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_quota_observations(
    *, provider: str = "", auth_profile: str = "", limit: int = 100
) -> list[dict[str, object]]:
    clauses: list[str] = []
    params: list[object] = []
    if provider:
        clauses.append("provider = ?")
        params.append(provider)
    if auth_profile:
        clauses.append("auth_profile = ?")
        params.append(auth_profile)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(max(1, min(int(limit), _MAX_PAGE_SIZE)))
    with connect() as conn:
        _ensure_control_schema(conn)
        rows = conn.execute(
            f"SELECT * FROM cheap_lane_quota_observations {where} "
            "ORDER BY observed_at DESC, id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
    return [
        {
            **dict(row),
            "limit": row["quota_limit"],
        }
        for row in rows
    ]


def record_cheap_lane_audit(
    *,
    actor: str,
    action: str,
    target: str,
    reason: str,
    before: dict[str, object],
    after: dict[str, object],
    result: str,
) -> str:
    audit_id = str(uuid4())
    now = _now_iso()
    with connect() as conn:
        _ensure_control_schema(conn)
        conn.execute(
            """
            INSERT INTO cheap_lane_audit (
                audit_id, actor, action, target, reason, before_json,
                after_json, result, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                actor,
                action,
                target,
                reason,
                _bounded_json(before),
                _bounded_json(after),
                result,
                now,
                now,
            ),
        )
        conn.commit()
    return audit_id


def finalize_cheap_lane_audit(
    audit_id: str,
    *,
    after: dict[str, object],
    result: str,
    error_code: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_control_schema(conn)
        cursor = conn.execute(
            """
            UPDATE cheap_lane_audit
            SET after_json = ?, result = ?, error_code = ?, updated_at = ?
            WHERE audit_id = ?
            """,
            (_bounded_json(after), result, error_code, now, audit_id),
        )
        if cursor.rowcount != 1:
            raise KeyError(f"unknown Cheap Lane audit: {audit_id}")
        conn.commit()
    return {
        "audit_id": audit_id,
        "after": after,
        "result": result,
        "error_code": error_code,
        "updated_at": now,
    }


def list_cheap_lane_audit(*, limit: int = 100) -> dict[str, object]:
    page_size = max(1, min(int(limit), _MAX_PAGE_SIZE))
    with connect() as conn:
        _ensure_control_schema(conn)
        rows = conn.execute(
            "SELECT * FROM cheap_lane_audit "
            "ORDER BY created_at DESC, audit_id DESC LIMIT ?",
            (page_size,),
        ).fetchall()
    items: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        item["before"] = _decode_json(item.pop("before_json", "{}"), {})
        item["after"] = _decode_json(item.pop("after_json", "{}"), {})
        items.append(item)
    return {"items": items, "next_cursor": None}


def record_redacted_payload(
    *,
    invocation_id: str,
    prompt: str | None,
    response: str | None,
    status: str,
    expires_at: str,
) -> int:
    now = _now_iso()
    with connect() as conn:
        _ensure_control_schema(conn)
        _ensure_invocation_schema(conn)
        conn.execute(
            """
            INSERT INTO cheap_lane_redacted_payloads (
                invocation_id, prompt, response, status, expires_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(invocation_id) DO UPDATE SET
                prompt=excluded.prompt,
                response=excluded.response,
                status=excluded.status,
                expires_at=excluded.expires_at,
                created_at=excluded.created_at
            """,
            (invocation_id, prompt, response, status, expires_at, now),
        )
        conn.execute(
            "UPDATE cheap_provider_invocations SET payload_status = ? "
            "WHERE invocation_id = ?",
            (status, invocation_id),
        )
        row = conn.execute(
            "SELECT id FROM cheap_lane_redacted_payloads WHERE invocation_id = ?",
            (invocation_id,),
        ).fetchone()
        conn.commit()
    return int(row["id"])


def _encode_cursor(created_at: str, row_id: int) -> str:
    raw = json.dumps([created_at, row_id], separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, int]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError
        return str(value[0]), int(value[1])
    except (
        ValueError,
        TypeError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        binascii.Error,
    ) as exc:
        raise ValueError("invalid Cheap Lane cursor") from exc


def _invocation_row(row) -> dict[str, object]:
    return dict(row)


def list_cheap_lane_invocations(
    *,
    since: str,
    until: str | None = None,
    provider: str = "",
    model: str = "",
    auth_profile: str = "",
    daemon: str = "",
    status: str = "",
    error_class: str = "",
    correlation_id: str = "",
    query: str = "",
    cursor: str = "",
    limit: int = 100,
) -> dict[str, object]:
    clauses = ["lane = 'cheap'", "created_at >= ?"]
    params: list[object] = [since]
    for column, value in (
        ("provider", provider),
        ("model", model),
        ("auth_profile", auth_profile),
        ("daemon", daemon),
        ("status", status),
        ("error_class", error_class),
        ("correlation_id", correlation_id),
    ):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    if until:
        clauses.append("created_at <= ?")
        params.append(until)
    if query:
        pattern = f"%{query}%"
        clauses.append(
            "(provider LIKE ? OR model LIKE ? OR daemon LIKE ? OR "
            "error_code LIKE ? OR error_message LIKE ? OR correlation_id LIKE ?)"
        )
        params.extend([pattern] * 6)
    if cursor:
        cursor_time, cursor_id = _decode_cursor(cursor)
        clauses.append("(created_at < ? OR (created_at = ? AND id < ?))")
        params.extend((cursor_time, cursor_time, cursor_id))
    page_size = max(1, min(int(limit), _MAX_PAGE_SIZE))
    params.append(page_size + 1)
    with connect() as conn:
        _ensure_invocation_schema(conn)
        rows = conn.execute(
            "SELECT * FROM cheap_provider_invocations WHERE "
            + " AND ".join(clauses)
            + " ORDER BY created_at DESC, id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
    has_more = len(rows) > page_size
    visible = rows[:page_size]
    next_cursor = None
    if has_more and visible:
        last = visible[-1]
        next_cursor = _encode_cursor(str(last["created_at"]), int(last["id"]))
    return {
        "items": [_invocation_row(row) for row in visible],
        "next_cursor": next_cursor,
    }


def get_cheap_lane_invocation_detail(
    invocation_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_invocation_schema(conn)
        _ensure_control_schema(conn)
        row = conn.execute(
            "SELECT * FROM cheap_provider_invocations "
            "WHERE invocation_id = ? AND lane = 'cheap' LIMIT 1",
            (invocation_id,),
        ).fetchone()
        if row is None:
            return None
        payload_row = conn.execute(
            "SELECT prompt, response, status, expires_at, created_at "
            "FROM cheap_lane_redacted_payloads WHERE invocation_id = ?",
            (invocation_id,),
        ).fetchone()
    detail: dict[str, Any] = _invocation_row(row)
    route_id = str(detail.get("route_decision_id") or "")
    detail["route_decision"] = get_route_decision(route_id) if route_id else None
    detail["payload"] = dict(payload_row) if payload_row is not None else None
    return detail
