"""DB helpers for dream_bias_active (Lag 2 dream-bias).

Single-row-per-workspace UPSERT semantics. Lives separately from db.py to
keep that file from growing further. Read API bypasses kill-switch — the
engine's get_active_dream_bias() wraps this with the enabled-check.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db import connect


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _future_iso(*, hours: int) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def insert_new_bias(
    *,
    workspace_id: str,
    attention_bias: dict[str, float],
    threshold_bias: dict[str, float],
    intensity: float,
    ttl_hours: int,
    dream_text: str,
    source_event_ids: list[str],
    source_kinds: list[str],
) -> dict[str, Any]:
    """INSERT a fresh bias row for a workspace.

    Caller must ensure no existing row exists OR existing row was just
    deleted — UNIQUE(workspace_id) constraint will raise otherwise.
    """
    now = _now()
    ttl_at = _future_iso(hours=ttl_hours)
    bias_id = f"db_{workspace_id}_{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        # Best-effort delete in case there's an expired row blocking UNIQUE
        conn.execute(
            "DELETE FROM dream_bias_active WHERE workspace_id = ?",
            (workspace_id,),
        )
        conn.execute(
            "INSERT INTO dream_bias_active "
            "(bias_id, workspace_id, attention_bias_json, threshold_bias_json, "
            "intensity, ttl_expires_at, dream_text, accumulated_count, "
            "last_dream_at, source_event_ids_json, source_kinds_json, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)",
            (
                bias_id, workspace_id,
                json.dumps(attention_bias), json.dumps(threshold_bias),
                float(intensity), ttl_at,
                dream_text[:400], now,
                json.dumps(source_event_ids[-50:]),
                json.dumps(source_kinds),
                now, now,
            ),
        )
    return {
        "bias_id": bias_id,
        "workspace_id": workspace_id,
        "accumulated_count": 1,
        "intensity": float(intensity),
        "ttl_expires_at": ttl_at,
    }


def update_existing_bias(
    *,
    workspace_id: str,
    attention_bias: dict[str, float],
    threshold_bias: dict[str, float],
    intensity: float,
    ttl_hours: int,
    dream_text: str,
    accumulated_count: int,
    source_event_ids: list[str],
    source_kinds: list[str],
) -> bool:
    """Update existing row in place. Returns True if a row was updated."""
    now = _now()
    ttl_at = _future_iso(hours=ttl_hours)
    with connect() as conn:
        cur = conn.execute(
            "UPDATE dream_bias_active SET "
            "attention_bias_json = ?, threshold_bias_json = ?, "
            "intensity = ?, ttl_expires_at = ?, "
            "dream_text = ?, accumulated_count = ?, last_dream_at = ?, "
            "source_event_ids_json = ?, source_kinds_json = ?, "
            "updated_at = ? "
            "WHERE workspace_id = ?",
            (
                json.dumps(attention_bias), json.dumps(threshold_bias),
                float(intensity), ttl_at,
                dream_text[:400], int(accumulated_count), now,
                json.dumps(source_event_ids[-50:]),
                json.dumps(source_kinds),
                now, workspace_id,
            ),
        )
        return cur.rowcount > 0


def get_active_bias_raw(*, workspace_id: str) -> dict[str, Any] | None:
    """Read the single active bias row for a workspace.

    Returns None if no row exists OR if TTL has expired. Does NOT honor
    the dream_bias_enabled kill-switch — that's the engine's concern.
    Includes parsed JSON fields for caller convenience.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT bias_id, workspace_id, attention_bias_json, threshold_bias_json, "
            "intensity, ttl_expires_at, dream_text, accumulated_count, last_dream_at, "
            "source_event_ids_json, source_kinds_json, created_at, updated_at "
            "FROM dream_bias_active WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
    if row is None:
        return None
    ttl_iso = str(row[5] or "")
    if ttl_iso and ttl_iso < _now():
        return None
    return {
        "bias_id": row[0],
        "workspace_id": row[1],
        "attention_bias": json.loads(row[2] or "{}"),
        "threshold_bias": json.loads(row[3] or "{}"),
        "intensity": float(row[4] or 0.0),
        "ttl_expires_at": ttl_iso,
        "dream_text": str(row[6] or ""),
        "accumulated_count": int(row[7] or 0),
        "last_dream_at": str(row[8] or ""),
        "source_event_ids": json.loads(row[9] or "[]"),
        "source_kinds": json.loads(row[10] or "[]"),
        "created_at": str(row[11] or ""),
        "updated_at": str(row[12] or ""),
    }


def delete_expired_bias_rows() -> int:
    """Hard-delete rows whose TTL has passed. Returns count."""
    now = _now()
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM dream_bias_active WHERE ttl_expires_at < ?",
            (now,),
        )
        return cur.rowcount
