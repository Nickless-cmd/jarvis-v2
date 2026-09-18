"""Cross-process pause, drain, and active-call leases for Cheap Lane."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.runtime.db_cheap_lane_control import _ensure_control_schema
from core.runtime.db_core import connect

_SCOPES = {"lane", "provider", "slot"}
_MODES = {"active", "paused", "draining"}


class AdmissionRejected(RuntimeError):
    def __init__(self, *, scope: str, target: str, mode: str) -> None:
        super().__init__(f"Cheap Lane admission rejected: {scope}/{target} is {mode}")
        self.scope = scope
        self.target = target
        self.mode = mode


class AdmissionRevisionConflict(RuntimeError):
    pass


@dataclass(frozen=True)
class AdmissionLease:
    lease_id: str
    correlation_id: str
    provider: str
    slot_id: str
    expires_at: str


def _prune_expired(conn, now: datetime) -> int:
    cursor = conn.execute(
        "DELETE FROM cheap_lane_admission_leases WHERE expires_at <= ?",
        (now.isoformat(),),
    )
    return int(cursor.rowcount or 0)


def _active_count(conn, *, scope: str, target: str) -> int:
    if scope == "lane":
        row = conn.execute("SELECT COUNT(*) AS n FROM cheap_lane_admission_leases").fetchone()
    elif scope == "provider":
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM cheap_lane_admission_leases WHERE provider=?",
            (target,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM cheap_lane_admission_leases WHERE slot_id=?",
            (target,),
        ).fetchone()
    return int(row["n"] or 0)


def set_admission_mode(
    *, scope: str, target: str, mode: str, expected_revision: str = ""
) -> dict[str, object]:
    if scope not in _SCOPES:
        raise ValueError(f"invalid admission scope: {scope}")
    if mode not in _MODES:
        raise ValueError(f"invalid admission mode: {mode}")
    normalized_target = target.strip()
    if not normalized_target:
        raise ValueError("admission target is required")
    now = datetime.now(UTC)
    with connect() as conn:
        _ensure_control_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        _prune_expired(conn, now)
        current = conn.execute(
            "SELECT mode, revision FROM cheap_lane_admission_state "
            "WHERE scope=? AND target=?",
            (scope, normalized_target),
        ).fetchone()
        revision = int(current["revision"] if current else 0)
        if expected_revision and expected_revision != str(revision):
            raise AdmissionRevisionConflict(
                f"expected revision {expected_revision}, current is {revision}"
            )
        next_revision = revision + 1
        conn.execute(
            "INSERT INTO cheap_lane_admission_state "
            "(scope, target, mode, revision, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(scope, target) DO UPDATE SET mode=excluded.mode, "
            "revision=excluded.revision, updated_at=excluded.updated_at",
            (scope, normalized_target, mode, next_revision, now.isoformat()),
        )
        active = _active_count(conn, scope=scope, target=normalized_target)
        conn.commit()
    return {
        "scope": scope, "target": normalized_target, "mode": mode,
        "revision": str(next_revision), "active_calls": active,
        "updated_at": now.isoformat(),
    }


def admission_snapshot(*, scope: str, target: str) -> dict[str, object]:
    now = datetime.now(UTC)
    with connect() as conn:
        _ensure_control_schema(conn)
        _prune_expired(conn, now)
        row = conn.execute(
            "SELECT mode, revision, updated_at FROM cheap_lane_admission_state "
            "WHERE scope=? AND target=?",
            (scope, target),
        ).fetchone()
        active = _active_count(conn, scope=scope, target=target)
        conn.commit()
    return {
        "scope": scope, "target": target,
        "mode": str(row["mode"] if row else "active"),
        "revision": str(row["revision"] if row else 0),
        "active_calls": active,
        "updated_at": row["updated_at"] if row else None,
    }


def acquire_admission(
    *, correlation_id: str, provider: str, slot_id: str, lease_seconds: int = 120
) -> AdmissionLease:
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=max(10, min(int(lease_seconds), 900)))
    checks = (("lane", "cheap"), ("provider", provider), ("slot", slot_id))
    lease_id = str(uuid4())
    with connect() as conn:
        _ensure_control_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        _prune_expired(conn, now)
        for scope, target in checks:
            row = conn.execute(
                "SELECT mode FROM cheap_lane_admission_state WHERE scope=? AND target=?",
                (scope, target),
            ).fetchone()
            mode = str(row["mode"] if row else "active")
            if mode != "active":
                raise AdmissionRejected(scope=scope, target=target, mode=mode)
        conn.execute(
            "INSERT INTO cheap_lane_admission_leases "
            "(lease_id, correlation_id, provider, slot_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (lease_id, correlation_id, provider, slot_id, now.isoformat(), expires.isoformat()),
        )
        conn.commit()
    return AdmissionLease(
        lease_id=lease_id, correlation_id=correlation_id,
        provider=provider, slot_id=slot_id, expires_at=expires.isoformat(),
    )


def release_admission(lease_id: str) -> None:
    if not lease_id:
        return
    with connect() as conn:
        _ensure_control_schema(conn)
        conn.execute("DELETE FROM cheap_lane_admission_leases WHERE lease_id=?", (lease_id,))
        conn.commit()
