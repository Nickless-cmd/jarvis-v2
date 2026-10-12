"""SQLite repository for first-class, owner-scoped Routines.

All private definition, execution, event, delivery and migration payloads are
sealed before they cross the database boundary.  This module deliberately has
no dependency on chat sessions or their inboxes.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any, Mapping

from core.runtime.db_core import connect
from core.services.routine_crypto import open_sealed, seal
from core.services.routine_types import AccessScope, RoutineStatus, RunStatus


_ROUTINE_STATUSES = tuple(item.value for item in RoutineStatus)
_RUN_STATUSES = tuple(item.value for item in RunStatus)
_DELIVERY_STATUSES = ("pending", "claimed", "retry", "delivered", "failed", "cancelled")


def _sql_values(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _open_json(owner_user_id: str, blob: bytes) -> Any:
    return json.loads(open_sealed(owner_user_id, bytes(blob)).decode("utf-8"))


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS routines (
            routine_id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            access_scope TEXT NOT NULL CHECK(access_scope IN ({_sql_values(('user_private', 'system_owner'))})),
            created_by TEXT NOT NULL CHECK(created_by IN ('user','jarvis','system','migration')),
            name_enc BLOB NOT NULL,
            instruction_enc BLOB NOT NULL,
            capability_scope TEXT NOT NULL CHECK(capability_scope IN ('chat','code','system')),
            workspace_enc BLOB NOT NULL,
            trigger_kind TEXT NOT NULL CHECK(trigger_kind IN ('manual','schedule','interval','event','system')),
            trigger_config_enc BLOB NOT NULL,
            permission_policy_enc BLOB NOT NULL,
            delivery_policy_enc BLOB NOT NULL,
            inbox_policy_enc BLOB NOT NULL,
            retention_policy_enc BLOB NOT NULL,
            failure_policy_enc BLOB NOT NULL,
            jarvis_restart_allowed INTEGER NOT NULL DEFAULT 0 CHECK(jarvis_restart_allowed IN (0,1)),
            status TEXT NOT NULL CHECK(status IN ({_sql_values(_ROUTINE_STATUSES)})),
            version INTEGER NOT NULL CHECK(version >= 1),
            consecutive_failures INTEGER NOT NULL DEFAULT 0 CHECK(consecutive_failures >= 0),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            stopped_at TEXT,
            archived_at TEXT,
            deleted_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_routines_owner_status
            ON routines(owner_user_id, status, updated_at);

        CREATE TABLE IF NOT EXISTS routine_versions (
            routine_id TEXT NOT NULL REFERENCES routines(routine_id),
            version INTEGER NOT NULL CHECK(version >= 1),
            definition_snapshot_enc BLOB NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(routine_id, version)
        );

        CREATE TABLE IF NOT EXISTS routine_runs (
            run_id TEXT PRIMARY KEY,
            routine_id TEXT NOT NULL REFERENCES routines(routine_id),
            owner_user_id TEXT NOT NULL,
            access_scope TEXT NOT NULL CHECK(access_scope IN ('user_private','system_owner')),
            idempotency_key TEXT NOT NULL,
            routine_version INTEGER NOT NULL CHECK(routine_version >= 1),
            definition_snapshot_enc BLOB NOT NULL,
            execution_context_enc BLOB NOT NULL,
            status TEXT NOT NULL CHECK(status IN ({_sql_values(_RUN_STATUSES)})),
            trigger_source TEXT NOT NULL,
            lease_holder TEXT,
            lease_generation INTEGER NOT NULL DEFAULT 0 CHECK(lease_generation >= 0),
            provider TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            usage_enc BLOB,
            result_enc BLOB,
            diagnostic_code TEXT NOT NULL DEFAULT '',
            diagnostic_projection_enc BLOB,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(routine_id, idempotency_key),
            FOREIGN KEY(routine_id, routine_version)
                REFERENCES routine_versions(routine_id, version)
        );
        CREATE INDEX IF NOT EXISTS idx_routine_runs_claim
            ON routine_runs(status, created_at);

        CREATE TABLE IF NOT EXISTS routine_run_events (
            event_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES routine_runs(run_id),
            seq INTEGER NOT NULL CHECK(seq >= 1),
            kind TEXT NOT NULL,
            payload_enc BLOB NOT NULL,
            terminal INTEGER NOT NULL DEFAULT 0 CHECK(terminal IN (0,1)),
            created_at TEXT NOT NULL,
            UNIQUE(run_id, seq)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_routine_run_one_terminal
            ON routine_run_events(run_id) WHERE terminal = 1;

        CREATE TABLE IF NOT EXISTS routine_deliveries (
            delivery_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES routine_runs(run_id),
            owner_user_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ({_sql_values(_DELIVERY_STATUSES)})),
            payload_enc BLOB,
            receipt_enc BLOB,
            retry_count INTEGER NOT NULL DEFAULT 0 CHECK(retry_count >= 0),
            next_attempt_at TEXT,
            lease_holder TEXT,
            lease_generation INTEGER NOT NULL DEFAULT 0 CHECK(lease_generation >= 0),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(run_id, channel)
        );

        CREATE TABLE IF NOT EXISTS routine_legacy_links (
            legacy_link_id TEXT PRIMARY KEY,
            routine_id TEXT REFERENCES routines(routine_id),
            run_id TEXT REFERENCES routine_runs(run_id),
            source_kind TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_ref_enc BLOB NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(source_kind, source_id)
        );

        CREATE TABLE IF NOT EXISTS routine_migration_quarantine (
            quarantine_id TEXT PRIMARY KEY,
            source_kind TEXT NOT NULL,
            source_id_hash TEXT NOT NULL,
            sealed_for TEXT NOT NULL,
            source_ref_enc BLOB NOT NULL,
            evidence_enc BLOB NOT NULL,
            reason_code TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'quarantined'
                CHECK(status IN ('quarantined','reclassified','discarded')),
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            UNIQUE(source_kind, source_id_hash)
        );

        CREATE TABLE IF NOT EXISTS routine_inbox_preferences (
            owner_user_id TEXT NOT NULL,
            routine_id TEXT NOT NULL DEFAULT '',
            policy_enc BLOB NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(owner_user_id, routine_id)
        );

        CREATE TABLE IF NOT EXISTS routine_tombstones (
            routine_id TEXT PRIMARY KEY,
            owner_user_id_hash TEXT NOT NULL,
            deleted_at TEXT NOT NULL,
            reason_code TEXT NOT NULL DEFAULT 'user_deleted'
        );
        """
    )


def _definition_snapshot(values: Mapping[str, Any]) -> dict[str, Any]:
    instruction = values["instruction"]
    if not isinstance(instruction, bytes):
        instruction = str(instruction).encode("utf-8")
    return {
        "name": str(values["name"]),
        "instruction_b64": base64.b64encode(instruction).decode("ascii"),
        "capability_scope": str(values["capability_scope"]),
        "workspace": dict(values.get("workspace") or {}),
        "trigger_kind": str(values["trigger_kind"]),
        "trigger_config": dict(values.get("trigger_config") or {}),
        "permission_policy": dict(values.get("permission_policy") or {}),
        "delivery_policy": dict(values.get("delivery_policy") or {}),
        "inbox_policy": dict(values.get("inbox_policy") or {}),
        "retention_policy": dict(values.get("retention_policy") or {}),
        "failure_policy": dict(values.get("failure_policy") or {}),
        "jarvis_restart_allowed": bool(values.get("jarvis_restart_allowed", False)),
    }


def _routine_values(row: sqlite3.Row, decrypt_for: str | None = None) -> dict[str, Any]:
    result = dict(row)
    if decrypt_for is not None:
        result.update(
            name=open_sealed(decrypt_for, bytes(row["name_enc"])).decode("utf-8"),
            instruction=open_sealed(decrypt_for, bytes(row["instruction_enc"])),
            workspace=_open_json(decrypt_for, row["workspace_enc"]),
            trigger_config=_open_json(decrypt_for, row["trigger_config_enc"]),
            permission_policy=_open_json(decrypt_for, row["permission_policy_enc"]),
            delivery_policy=_open_json(decrypt_for, row["delivery_policy_enc"]),
            inbox_policy=_open_json(decrypt_for, row["inbox_policy_enc"]),
            retention_policy=_open_json(decrypt_for, row["retention_policy_enc"]),
            failure_policy=_open_json(decrypt_for, row["failure_policy_enc"]),
        )
    for key in tuple(result):
        if key.endswith("_enc"):
            result.pop(key)
    result["jarvis_restart_allowed"] = bool(result["jarvis_restart_allowed"])
    return result


def create_routine(
    *, owner_user_id: str, access_scope: str, name: str, instruction: bytes,
    capability_scope: str, trigger_kind: str, trigger_config: Mapping[str, object],
    permission_policy: Mapping[str, object], delivery_policy: Mapping[str, object],
    inbox_policy: Mapping[str, object], retention_policy: Mapping[str, object],
    failure_policy: Mapping[str, object], created_by: str = "user",
    status: str = "active", workspace_name: str = "", workspace_kind: str = "",
    workspace_root: str = "", jarvis_restart_allowed: bool = False,
    routine_id: str | None = None,
) -> dict[str, Any]:
    owner = str(owner_user_id or "").strip()
    if not owner:
        raise ValueError("owner_user_id is required")
    AccessScope(access_scope)
    RoutineStatus(status)
    rid = routine_id or _id("routine")
    now = _now()
    values = {
        "name": name,
        "instruction": instruction,
        "capability_scope": capability_scope,
        "workspace": {"name": workspace_name, "kind": workspace_kind, "root": workspace_root},
        "trigger_kind": trigger_kind,
        "trigger_config": trigger_config,
        "permission_policy": permission_policy,
        "delivery_policy": delivery_policy,
        "inbox_policy": inbox_policy,
        "retention_policy": retention_policy,
        "failure_policy": failure_policy,
        "jarvis_restart_allowed": jarvis_restart_allowed,
    }
    snapshot = seal(owner, _json_bytes(_definition_snapshot(values)))
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            "INSERT INTO routines (routine_id,owner_user_id,access_scope,created_by,name_enc,"
            "instruction_enc,capability_scope,workspace_enc,trigger_kind,trigger_config_enc,"
            "permission_policy_enc,delivery_policy_enc,inbox_policy_enc,retention_policy_enc,"
            "failure_policy_enc,jarvis_restart_allowed,status,version,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
            (rid, owner, access_scope, created_by, seal(owner, name.encode("utf-8")),
             seal(owner, instruction), capability_scope, seal(owner, _json_bytes(values["workspace"])),
             trigger_kind, seal(owner, _json_bytes(trigger_config)),
             seal(owner, _json_bytes(permission_policy)), seal(owner, _json_bytes(delivery_policy)),
             seal(owner, _json_bytes(inbox_policy)), seal(owner, _json_bytes(retention_policy)),
             seal(owner, _json_bytes(failure_policy)), int(jarvis_restart_allowed), status, now, now),
        )
        conn.execute(
            "INSERT INTO routine_versions (routine_id,version,definition_snapshot_enc,created_at) "
            "VALUES (?,1,?,?)", (rid, snapshot, now),
        )
        row = conn.execute("SELECT * FROM routines WHERE routine_id=?", (rid,)).fetchone()
    return _routine_values(row, decrypt_for=owner)


def get_routine(routine_id: str, *, decrypt_for: str | None = None) -> dict[str, Any] | None:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
    return None if row is None else _routine_values(row, decrypt_for=decrypt_for)


def list_routines(
    *, owner_user_id: str, include_deleted: bool = False, decrypt_for: str | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM routines WHERE owner_user_id=?"
    params: list[object] = [owner_user_id]
    if not include_deleted:
        query += " AND status != 'deleted'"
    query += " ORDER BY updated_at DESC, routine_id"
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(query, params).fetchall()
    return [_routine_values(row, decrypt_for=decrypt_for) for row in rows]


def transition_routine(
    routine_id: str, *, to_status: str, expected_version: int | None = None,
) -> dict[str, Any]:
    RoutineStatus(to_status)
    now = _now()
    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
            if row is None:
                raise KeyError(routine_id)
            current_version = int(row["version"])
            if expected_version is not None and current_version != int(expected_version):
                raise ValueError("stale routine version")
            stopped_at = now if to_status == "stopped" else row["stopped_at"]
            archived_at = now if to_status == "archived" else row["archived_at"]
            deleted_at = now if to_status == "deleted" else row["deleted_at"]
            changed = conn.execute(
                "UPDATE routines SET status=?,updated_at=?,stopped_at=?,archived_at=?,"
                "deleted_at=? WHERE routine_id=? AND version=?",
                (to_status, now, stopped_at, archived_at, deleted_at,
                 routine_id, current_version),
            )
            if changed.rowcount != 1:
                raise ValueError("stale routine version")
            updated = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return _routine_values(updated)


def update_routine_definition(
    routine_id: str, *, expected_version: int, changes: Mapping[str, object],
    reactivate: bool = False,
) -> dict[str, Any]:
    """Atomically write a new immutable definition version."""
    allowed = {
        "name", "instruction", "capability_scope", "trigger_kind", "trigger_config",
        "permission_policy", "delivery_policy", "inbox_policy", "retention_policy",
        "failure_policy", "workspace_name", "workspace_kind", "workspace_root",
        "jarvis_restart_allowed",
    }
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"unknown routine fields: {sorted(unknown)}")
    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
            if row is None:
                raise KeyError(routine_id)
            if int(row["version"]) != int(expected_version):
                raise ValueError("stale routine version")
            owner = str(row["owner_user_id"])
            current = _routine_values(row, decrypt_for=owner)
            workspace = dict(current["workspace"])
            for field in ("name", "kind", "root"):
                change_key = f"workspace_{field}"
                if change_key in changes:
                    workspace[field] = str(changes[change_key])
            instruction = changes.get("instruction", current["instruction"])
            if isinstance(instruction, str):
                instruction = instruction.encode("utf-8")
            values = {
                "name": changes.get("name", current["name"]),
                "instruction": instruction,
                "capability_scope": changes.get("capability_scope", current["capability_scope"]),
                "workspace": workspace,
                "trigger_kind": changes.get("trigger_kind", current["trigger_kind"]),
                "trigger_config": changes.get("trigger_config", current["trigger_config"]),
                "permission_policy": changes.get("permission_policy", current["permission_policy"]),
                "delivery_policy": changes.get("delivery_policy", current["delivery_policy"]),
                "inbox_policy": changes.get("inbox_policy", current["inbox_policy"]),
                "retention_policy": changes.get("retention_policy", current["retention_policy"]),
                "failure_policy": changes.get("failure_policy", current["failure_policy"]),
                "jarvis_restart_allowed": changes.get(
                    "jarvis_restart_allowed", current["jarvis_restart_allowed"]
                ),
            }
            version = int(row["version"]) + 1
            status = "active" if reactivate else str(row["status"])
            now = _now()
            changed = conn.execute(
                "UPDATE routines SET name_enc=?,instruction_enc=?,capability_scope=?,workspace_enc=?,"
                "trigger_kind=?,trigger_config_enc=?,permission_policy_enc=?,delivery_policy_enc=?,"
                "inbox_policy_enc=?,retention_policy_enc=?,failure_policy_enc=?,"
                "jarvis_restart_allowed=?,status=?,version=?,updated_at=? "
                "WHERE routine_id=? AND version=?",
                (seal(owner, str(values["name"]).encode("utf-8")), seal(owner, instruction),
                 values["capability_scope"], seal(owner, _json_bytes(workspace)),
                 values["trigger_kind"], seal(owner, _json_bytes(values["trigger_config"])),
                 seal(owner, _json_bytes(values["permission_policy"])),
                 seal(owner, _json_bytes(values["delivery_policy"])),
                 seal(owner, _json_bytes(values["inbox_policy"])),
                 seal(owner, _json_bytes(values["retention_policy"])),
                 seal(owner, _json_bytes(values["failure_policy"])),
                 int(bool(values["jarvis_restart_allowed"])), status, version, now,
                 routine_id, expected_version),
            )
            if changed.rowcount != 1:
                raise ValueError("stale routine version")
            conn.execute(
                "INSERT INTO routine_versions (routine_id,version,definition_snapshot_enc,created_at) "
                "VALUES (?,?,?,?)",
                (routine_id, version, seal(owner, _json_bytes(_definition_snapshot(values))), now),
            )
            updated = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return _routine_values(updated, decrypt_for=owner)


def stop_routine(routine_id: str, *, expected_version: int | None = None) -> dict[str, Any]:
    """Stop a definition and revoke/cancel all unfinished work atomically."""
    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
            if row is None:
                raise KeyError(routine_id)
            if expected_version is not None and int(row["version"]) != int(expected_version):
                raise ValueError("stale routine version")
            if row["status"] != "stopped":
                now = _now()
                conn.execute(
                    "UPDATE routines SET status='stopped',stopped_at=?,updated_at=? WHERE routine_id=?",
                    (now, now, routine_id),
                )
                conn.execute(
                    "UPDATE routine_runs SET status='cancelled',finished_at=?,updated_at=? "
                    "WHERE routine_id=? AND status='queued'", (now, now, routine_id),
                )
                conn.execute(
                    "UPDATE routine_runs SET status='cancelling',lease_holder=NULL,"
                    "lease_generation=lease_generation+1,updated_at=? "
                    "WHERE routine_id=? AND status='running'", (now, routine_id),
                )
            updated = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return _routine_values(updated)


def create_run(
    *, routine_id: str, idempotency_key: str, trigger_source: str = "manual",
    execution_context: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    key = str(idempotency_key or "").strip()
    if not key:
        raise ValueError("idempotency_key is required")
    with connect() as conn:
        _ensure_tables(conn)
        existing = conn.execute(
            "SELECT * FROM routine_runs WHERE routine_id=? AND idempotency_key=?",
            (routine_id, key),
        ).fetchone()
        if existing is not None:
            return dict(existing)
        routine = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
        if routine is None:
            raise KeyError(routine_id)
        version = int(routine["version"])
        snapshot = conn.execute(
            "SELECT definition_snapshot_enc FROM routine_versions WHERE routine_id=? AND version=?",
            (routine_id, version),
        ).fetchone()[0]
        run_id = _id("run")
        now = _now()
        context_enc = seal(str(routine["owner_user_id"]), _json_bytes(dict(execution_context or {})))
        try:
            conn.execute(
                "INSERT INTO routine_runs (run_id,routine_id,owner_user_id,access_scope,"
                "idempotency_key,routine_version,definition_snapshot_enc,execution_context_enc,"
                "status,trigger_source,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, routine_id, routine["owner_user_id"], routine["access_scope"], key,
                 version, snapshot, context_enc, "queued", trigger_source, now, now),
            )
        except sqlite3.IntegrityError:
            replay = conn.execute(
                "SELECT * FROM routine_runs WHERE routine_id=? AND idempotency_key=?",
                (routine_id, key),
            ).fetchone()
            if replay is None:
                raise
            return dict(replay)
        return dict(conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone())


def get_run(run_id: str, *, decrypt_for: str | None = None) -> dict[str, Any] | None:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    if decrypt_for is not None:
        result["execution_context"] = _open_json(decrypt_for, row["execution_context_enc"])
        snapshot = _open_json(decrypt_for, row["definition_snapshot_enc"])
        snapshot["instruction"] = base64.b64decode(snapshot.pop("instruction_b64"))
        result["definition_snapshot"] = snapshot
        if row["result_enc"] is not None:
            result["result"] = open_sealed(decrypt_for, bytes(row["result_enc"]))
    for key in tuple(result):
        if key.endswith("_enc"):
            result.pop(key)
    return result


def list_runs(routine_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(
            "SELECT * FROM routine_runs WHERE routine_id=? ORDER BY created_at,run_id",
            (routine_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def cancel_run(run_id: str) -> dict[str, Any]:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        now = _now()
        if row["status"] == "queued":
            conn.execute(
                "UPDATE routine_runs SET status='cancelled',finished_at=?,updated_at=? WHERE run_id=?",
                (now, now, run_id),
            )
        elif row["status"] == "running":
            conn.execute(
                "UPDATE routine_runs SET status='cancelling',lease_holder=NULL,"
                "lease_generation=lease_generation+1,updated_at=? WHERE run_id=?",
                (now, run_id),
            )
        return dict(conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone())


def list_stopped_routines(*, before: str) -> list[dict[str, Any]]:
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(
            "SELECT * FROM routines WHERE status='stopped' AND stopped_at IS NOT NULL "
            "AND stopped_at < ? ORDER BY stopped_at,routine_id", (before,),
        ).fetchall()
    return [_routine_values(row, decrypt_for=str(row["owner_user_id"])) for row in rows]


def delete_routine_content(routine_id: str, *, reason_code: str = "user_deleted") -> bool:
    """Erase all private material and retain only a content-free audit tombstone."""
    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT owner_user_id FROM routines WHERE routine_id=?", (routine_id,),
            ).fetchone()
            if row is None:
                conn.rollback()
                return False
            owner_hash = hashlib.sha256(str(row["owner_user_id"]).encode("utf-8")).hexdigest()
            run_ids = [item[0] for item in conn.execute(
                "SELECT run_id FROM routine_runs WHERE routine_id=?", (routine_id,),
            ).fetchall()]
            for run_id in run_ids:
                conn.execute("DELETE FROM routine_deliveries WHERE run_id=?", (run_id,))
                conn.execute("DELETE FROM routine_run_events WHERE run_id=?", (run_id,))
            conn.execute("DELETE FROM routine_runs WHERE routine_id=?", (routine_id,))
            conn.execute("DELETE FROM routine_versions WHERE routine_id=?", (routine_id,))
            conn.execute("DELETE FROM routine_legacy_links WHERE routine_id=?", (routine_id,))
            conn.execute("DELETE FROM routine_inbox_preferences WHERE routine_id=?", (routine_id,))
            conn.execute("DELETE FROM routines WHERE routine_id=?", (routine_id,))
            conn.execute(
                "INSERT OR IGNORE INTO routine_tombstones "
                "(routine_id,owner_user_id_hash,deleted_at,reason_code) VALUES (?,?,?,?)",
                (routine_id, owner_hash, _now(), reason_code),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise


def read_run_events(run_id: str, *, decrypt_for: str | None = None) -> list[dict[str, Any]]:
    with connect() as conn:
        _ensure_tables(conn)
        run = conn.execute("SELECT owner_user_id FROM routine_runs WHERE run_id=?", (run_id,)).fetchone()
        if run is None:
            raise KeyError(run_id)
        rows = conn.execute(
            "SELECT * FROM routine_run_events WHERE run_id=? ORDER BY seq", (run_id,),
        ).fetchall()
    events = [dict(row) for row in rows]
    if decrypt_for is not None:
        for event in events:
            event["payload"] = _open_json(decrypt_for, event.pop("payload_enc"))
    return events


def claim_run(run_id: str, *, holder: str) -> dict[str, Any] | None:
    holder = str(holder or "").strip()
    if not holder:
        raise ValueError("holder is required")
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        if row["status"] == "running" and row["lease_holder"] == holder:
            return dict(row)
        if row["status"] != "queued" or row["lease_holder"]:
            return None
        now = _now()
        changed = conn.execute(
            "UPDATE routine_runs SET status='running',lease_holder=?,lease_generation=lease_generation+1,"
            "started_at=COALESCE(started_at,?),updated_at=? WHERE run_id=? AND status='queued' "
            "AND lease_holder IS NULL",
            (holder, now, now, run_id),
        )
        if changed.rowcount != 1:
            return None
        return dict(conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone())


def append_run_event(
    *, run_id: str, kind: str, payload: Mapping[str, object], terminal: bool = False,
    event_id: str | None = None, expected_generation: int | None = None,
) -> dict[str, Any]:
    with connect() as conn:
        _ensure_tables(conn)
        run = conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone()
        if run is None:
            raise KeyError(run_id)
        if expected_generation is not None and int(run["lease_generation"]) != int(expected_generation):
            raise ValueError("stale routine lease")
        if terminal:
            prior = conn.execute(
                "SELECT * FROM routine_run_events WHERE run_id=? AND terminal=1", (run_id,),
            ).fetchone()
            if prior is not None:
                return dict(prior)
        eid = event_id or _id("event")
        replay = conn.execute("SELECT * FROM routine_run_events WHERE event_id=?", (eid,)).fetchone()
        if replay is not None:
            return dict(replay)
        seq = int(conn.execute(
            "SELECT COALESCE(MAX(seq),0)+1 FROM routine_run_events WHERE run_id=?", (run_id,),
        ).fetchone()[0])
        conn.execute(
            "INSERT INTO routine_run_events (event_id,run_id,seq,kind,payload_enc,terminal,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (eid, run_id, seq, kind, seal(str(run["owner_user_id"]), _json_bytes(payload)),
             int(terminal), _now()),
        )
        return dict(conn.execute("SELECT * FROM routine_run_events WHERE event_id=?", (eid,)).fetchone())


def transition_run(
    run_id: str, *, to_status: str, expected_generation: int | None = None,
    result: bytes | None = None, diagnostic_code: str = "",
) -> dict[str, Any]:
    RunStatus(to_status)
    terminal = to_status in {"succeeded", "failed", "cancelled", "skipped"}
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        if expected_generation is not None and int(row["lease_generation"]) != int(expected_generation):
            raise ValueError("stale routine lease")
        result_enc = seal(str(row["owner_user_id"]), result) if result is not None else row["result_enc"]
        now = _now()
        conn.execute(
            "UPDATE routine_runs SET status=?,result_enc=?,diagnostic_code=?,updated_at=?,"
            "finished_at=? WHERE run_id=?",
            (to_status, result_enc, diagnostic_code, now, now if terminal else row["finished_at"], run_id),
        )
        updated = conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone()
    if terminal:
        append_run_event(
            run_id=run_id, kind=to_status, payload={"diagnostic_code": diagnostic_code}, terminal=True,
            expected_generation=expected_generation,
        )
    return dict(updated)


def create_delivery(
    *, run_id: str, channel: str, payload: bytes | None = None,
) -> dict[str, Any]:
    with connect() as conn:
        _ensure_tables(conn)
        existing = conn.execute(
            "SELECT * FROM routine_deliveries WHERE run_id=? AND channel=?", (run_id, channel),
        ).fetchone()
        if existing is not None:
            return dict(existing)
        run = conn.execute("SELECT owner_user_id FROM routine_runs WHERE run_id=?", (run_id,)).fetchone()
        if run is None:
            raise KeyError(run_id)
        owner = str(run["owner_user_id"])
        delivery_id = _id("delivery")
        now = _now()
        conn.execute(
            "INSERT INTO routine_deliveries (delivery_id,run_id,owner_user_id,channel,status,"
            "payload_enc,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (delivery_id, run_id, owner, channel, "pending",
             seal(owner, payload) if payload is not None else None, now, now),
        )
        return dict(conn.execute(
            "SELECT * FROM routine_deliveries WHERE delivery_id=?", (delivery_id,),
        ).fetchone())


def put_quarantine(
    *, source_kind: str, source_id_hash: str, source_reference: Mapping[str, object],
    classifier_evidence: Mapping[str, object], reason_code: str,
    sealed_for: str = "__migration_quarantine__",
) -> dict[str, Any]:
    with connect() as conn:
        _ensure_tables(conn)
        existing = conn.execute(
            "SELECT * FROM routine_migration_quarantine WHERE source_kind=? AND source_id_hash=?",
            (source_kind, source_id_hash),
        ).fetchone()
        if existing is not None:
            return dict(existing)
        quarantine_id = _id("quarantine")
        conn.execute(
            "INSERT INTO routine_migration_quarantine (quarantine_id,source_kind,source_id_hash,"
            "sealed_for,source_ref_enc,evidence_enc,reason_code,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (quarantine_id, source_kind, source_id_hash, sealed_for,
             seal(sealed_for, _json_bytes(source_reference)),
             seal(sealed_for, _json_bytes(classifier_evidence)), reason_code, _now()),
        )
        return dict(conn.execute(
            "SELECT * FROM routine_migration_quarantine WHERE quarantine_id=?", (quarantine_id,),
        ).fetchone())
