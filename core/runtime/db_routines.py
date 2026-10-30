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
from datetime import UTC, datetime, timedelta
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
            lease_expires_at TEXT,
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

        CREATE TABLE IF NOT EXISTS routine_tool_effects (
            effect_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES routine_runs(run_id),
            call_id TEXT NOT NULL,
            tool_name_enc BLOB NOT NULL,
            lease_generation INTEGER NOT NULL CHECK(lease_generation >= 1),
            status TEXT NOT NULL CHECK(status IN ('dispatching','succeeded','failed','outcome_unknown')),
            started_at TEXT NOT NULL,
            finished_at TEXT,
            UNIQUE(run_id, call_id)
        );

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
    columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(routine_runs)")}
    if "lease_expires_at" not in columns:
        conn.execute("ALTER TABLE routine_runs ADD COLUMN lease_expires_at TEXT")


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
        conn.execute(
            "INSERT INTO routine_inbox_preferences "
            "(owner_user_id,routine_id,policy_enc,created_at,updated_at) VALUES (?,?,?,?,?)",
            (owner, rid, seal(owner, _json_bytes(inbox_policy)), now, now),
        )
        row = conn.execute("SELECT * FROM routines WHERE routine_id=?", (rid,)).fetchone()
    return _routine_values(row, decrypt_for=owner)


def get_routine(routine_id: str, *, decrypt_for: str | None = None) -> dict[str, Any] | None:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
    return None if row is None else _routine_values(row, decrypt_for=decrypt_for)


def list_routines(
    *, owner_user_id: str, include_deleted: bool = False,
    include_legacy_history: bool = False, decrypt_for: str | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM routines WHERE owner_user_id=?"
    params: list[object] = [owner_user_id]
    if not include_deleted:
        query += " AND status != 'deleted'"
    if not include_legacy_history:
        # De tidlige migrationer lavede én Routine-definition pr. historisk
        # ``auto-<origin>-<dag>``-session. De rækker er proveniens/historik,
        # ikke noget brugeren kan eller skal genoptage som 197 særskilte
        # rutiner. Bevar dem og deres krypterede links i databasen, men vis kun
        # egentlige definitioner i biblioteket. Nye systemdefinitioner har
        # ``created_by='system'`` og rammes derfor ikke af filteret.
        query += (
            " AND NOT (created_by='migration' AND EXISTS ("
            "SELECT 1 FROM routine_legacy_links legacy "
            "WHERE legacy.routine_id=routines.routine_id "
            "AND legacy.source_kind='autonomous_session'))"
        )
    query += " ORDER BY updated_at DESC, routine_id"
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(query, params).fetchall()
    return [_routine_values(row, decrypt_for=decrypt_for) for row in rows]


def routine_has_legacy_link(routine_id: str) -> bool:
    """Har rutinen en oprindelig (legacy) kilde der selv styrer dens tidsplan?

    Sandt betyder: ``recurring_tasks``/``scheduled_tasks`` fyrer den allerede
    gennem ``RoutineTriggerAdapters``. Scheduleren skal derfor holde sig væk —
    ellers får brugeren to runs af samme opgave. Målt 25/10-2026 havde 198
    rutiner et sådant link, og cutover var slukket, så legacy-vejen var den
    aktive for dem alle.
    """
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT 1 FROM routine_legacy_links WHERE routine_id=? LIMIT 1",
            (routine_id,),
        ).fetchone()
    return row is not None


def list_schedulable_routines() -> list[dict[str, Any]]:
    """Alle AKTIVE rutiner med en tids-trigger — på tværs af ALLE ejere.

    Returnerer kun de felter scheduleren må se: id, ejer og tidsanker. Selve
    ``trigger_config`` er krypteret og dekrypteres af kalderen med EJERENS
    nøgle (``get_routine(decrypt_for=...)``) — en scheduler må ikke kunne læse
    indhold den ikke ejer.

    Målt 25/10-2026: præcis to rækker kvalificerede (én ``interval`` for
    ejeren, én ``schedule`` for en partner), så en scheduler kan tændes uden
    at 201 migrerede rutiner pludselig fyrer.
    """
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(
            "SELECT routine_id, owner_user_id, trigger_kind, created_at "
            "FROM routines WHERE status='active' "
            "AND trigger_kind IN ('schedule','interval') "
            "ORDER BY created_at"
        ).fetchall()
    return [dict(row) for row in rows]


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
            if "inbox_policy" in changes:
                conn.execute(
                    "UPDATE routine_inbox_preferences SET policy_enc=?,updated_at=? "
                    "WHERE owner_user_id=? AND routine_id=?",
                    (seal(owner, _json_bytes(values["inbox_policy"])), now, owner, routine_id),
                )
            updated = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return _routine_values(updated, decrypt_for=owner)


def transfer_ownership(
    routine_id: str, *, to_owner_user_id: str,
) -> dict[str, Any]:
    """Move a Routine and its entire history to another owner.

    Routine content is sealed per owner (``routine_crypto.seal`` binds every
    ``_enc`` column to the owner's keyring entry), so changing the
    ``owner_user_id`` column alone leaves rows the new owner cannot open — the
    next read raises ``DecryptionError``. Every sealed value must therefore be
    opened with the OLD key and re-sealed with the NEW one, in the same
    transaction.

    The history is not optional: ``get_run(decrypt_for=<the run's own owner>)``
    means the new owner's view of their own Routine includes its past runs. A
    transfer that only re-seals ``routines`` and ``routine_versions`` leaves
    those runs unreadable, and ``create_run`` copies the version snapshot
    verbatim, so a stale snapshot breaks the next scheduled fire.

    Measured 29/10-2026 on a real Routine: 7 tables, 244 sealed values.
    """
    new_owner = str(to_owner_user_id or "").strip()
    if not new_owner:
        raise ValueError("to_owner_user_id is required")

    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
            if row is None:
                raise KeyError(routine_id)
            old_owner = str(row["owner_user_id"])
            if old_owner == new_owner:
                conn.rollback()
                return _routine_values(row, decrypt_for=new_owner)

            def reseal(blob: object) -> object:
                if blob is None:
                    return None
                return seal(new_owner, open_sealed(old_owner, bytes(blob)))

            enc_columns = (
                "name_enc", "instruction_enc", "workspace_enc", "trigger_config_enc",
                "permission_policy_enc", "delivery_policy_enc", "inbox_policy_enc",
                "retention_policy_enc", "failure_policy_enc",
            )
            conn.execute(
                "UPDATE routines SET " + ",".join(f"{c}=?" for c in enc_columns)
                + ",owner_user_id=?,updated_at=? WHERE routine_id=?",
                (*[reseal(row[c]) for c in enc_columns], new_owner, _now(), routine_id),
            )

            # Version snapshots carry no owner column but are sealed per owner,
            # and create_run copies the current one into every new run.
            for version_row in conn.execute(
                "SELECT version, definition_snapshot_enc FROM routine_versions WHERE routine_id=?",
                (routine_id,),
            ).fetchall():
                conn.execute(
                    "UPDATE routine_versions SET definition_snapshot_enc=? "
                    "WHERE routine_id=? AND version=?",
                    (reseal(version_row["definition_snapshot_enc"]), routine_id, version_row["version"]),
                )

            run_columns = (
                "definition_snapshot_enc", "execution_context_enc", "usage_enc",
                "result_enc", "diagnostic_projection_enc",
            )
            run_ids: list[str] = []
            for run_row in conn.execute(
                "SELECT * FROM routine_runs WHERE routine_id=?", (routine_id,),
            ).fetchall():
                run_ids.append(str(run_row["run_id"]))
                conn.execute(
                    "UPDATE routine_runs SET " + ",".join(f"{c}=?" for c in run_columns)
                    + ",owner_user_id=?,updated_at=? WHERE run_id=?",
                    (*[reseal(run_row[c]) for c in run_columns], new_owner, _now(), run_row["run_id"]),
                )

            if run_ids:
                marks = ",".join("?" for _ in run_ids)
                for event_row in conn.execute(
                    f"SELECT event_id, payload_enc FROM routine_run_events WHERE run_id IN ({marks})",
                    run_ids,
                ).fetchall():
                    conn.execute(
                        "UPDATE routine_run_events SET payload_enc=? WHERE event_id=?",
                        (reseal(event_row["payload_enc"]), event_row["event_id"]),
                    )
                for effect_row in conn.execute(
                    f"SELECT effect_id, tool_name_enc FROM routine_tool_effects WHERE run_id IN ({marks})",
                    run_ids,
                ).fetchall():
                    conn.execute(
                        "UPDATE routine_tool_effects SET tool_name_enc=? WHERE effect_id=?",
                        (reseal(effect_row["tool_name_enc"]), effect_row["effect_id"]),
                    )
                for delivery_row in conn.execute(
                    f"SELECT delivery_id, payload_enc, receipt_enc FROM routine_deliveries "
                    f"WHERE run_id IN ({marks})",
                    run_ids,
                ).fetchall():
                    conn.execute(
                        "UPDATE routine_deliveries SET payload_enc=?,receipt_enc=?,owner_user_id=? "
                        "WHERE delivery_id=?",
                        (reseal(delivery_row["payload_enc"]), reseal(delivery_row["receipt_enc"]),
                         new_owner, delivery_row["delivery_id"]),
                    )

            conn.execute(
                "UPDATE routine_inbox_preferences SET policy_enc=?,owner_user_id=?,updated_at=? "
                "WHERE routine_id=?",
                (seal(new_owner, _json_bytes(_open_json(old_owner, row["inbox_policy_enc"]))),
                 new_owner, _now(), routine_id),
            )

            moved = conn.execute("SELECT * FROM routines WHERE routine_id=?", (routine_id,)).fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return _routine_values(moved, decrypt_for=new_owner)


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
                conn.execute("DELETE FROM routine_tool_effects WHERE run_id=?", (run_id,))
                conn.execute("DELETE FROM routine_run_events WHERE run_id=?", (run_id,))
            conn.execute("DELETE FROM routine_runs WHERE routine_id=?", (routine_id,))
            conn.execute("DELETE FROM routine_versions WHERE routine_id=?", (routine_id,))
            # Keep the content-free cutover marker when private Routine data is
            # erased, otherwise its legacy chat would reappear in navigation.
            conn.execute(
                "UPDATE routine_legacy_links SET routine_id=NULL WHERE routine_id=?",
                (routine_id,),
            )
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


def claim_run(
    run_id: str, *, holder: str, now: datetime | None = None, lease_seconds: int = 90,
) -> dict[str, Any] | None:
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
        claimed_at = now or datetime.now(UTC)
        now_text = claimed_at.isoformat()
        expires_at = (claimed_at + timedelta(seconds=lease_seconds)).isoformat()
        changed = conn.execute(
            "UPDATE routine_runs SET status='running',lease_holder=?,lease_generation=lease_generation+1,"
            "lease_expires_at=?,started_at=COALESCE(started_at,?),updated_at=? "
            "WHERE run_id=? AND status='queued' "
            "AND lease_holder IS NULL",
            (holder, expires_at, now_text, now_text, run_id),
        )
        if changed.rowcount != 1:
            return None
        return dict(conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone())


def renew_run_lease(
    run_id: str, *, holder: str, expected_generation: int,
    now: datetime | None = None, lease_seconds: int = 90,
) -> dict[str, Any]:
    current = now or datetime.now(UTC)
    with connect() as conn:
        _ensure_tables(conn)
        changed = conn.execute(
            "UPDATE routine_runs SET lease_expires_at=?,updated_at=? WHERE run_id=? "
            "AND status='running' AND lease_holder=? AND lease_generation=?",
            ((current + timedelta(seconds=lease_seconds)).isoformat(), current.isoformat(),
             run_id, holder, expected_generation),
        )
        if changed.rowcount != 1:
            raise ValueError("stale routine lease")
        return dict(conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone())


def release_run_claim(
    run_id: str, *, holder: str, expected_generation: int,
) -> dict[str, Any]:
    """Return an unstarted dispatch to the queue without changing occurrence identity."""
    with connect() as conn:
        _ensure_tables(conn)
        changed = conn.execute(
            "UPDATE routine_runs SET status='queued',lease_holder=NULL,"
            "lease_expires_at=NULL,updated_at=? WHERE run_id=? AND status='running' "
            "AND lease_holder=? AND lease_generation=?",
            (_now(), run_id, holder, expected_generation),
        )
        if changed.rowcount != 1:
            raise ValueError("stale routine lease")
        return dict(conn.execute(
            "SELECT * FROM routine_runs WHERE run_id=?", (run_id,),
        ).fetchone())


def reclaim_run(
    run_id: str, *, expected_generation: int, holder: str,
    now: datetime | None = None, lease_seconds: int = 90,
) -> dict[str, Any]:
    current = now or datetime.now(UTC)
    with connect() as conn:
        _ensure_tables(conn)
        changed = conn.execute(
            "UPDATE routine_runs SET lease_holder=?,lease_generation=lease_generation+1,"
            "lease_expires_at=?,updated_at=? WHERE run_id=? AND status='running' "
            "AND lease_generation=?",
            (holder, (current + timedelta(seconds=lease_seconds)).isoformat(), current.isoformat(),
             run_id, expected_generation),
        )
        if changed.rowcount != 1:
            raise ValueError("stale routine lease")
        return dict(conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone())


def assert_current_run_lease(
    run_id: str, *, expected_generation: int, holder: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute("SELECT * FROM routine_runs WHERE run_id=?", (run_id,)).fetchone()
    current = now or datetime.now(UTC)
    if (
        row is None
        or row["status"] != "running"
        or int(row["lease_generation"]) != int(expected_generation)
        or (holder is not None and row["lease_holder"] != holder)
        or not row["lease_expires_at"]
        or str(row["lease_expires_at"]) <= current.isoformat()
    ):
        raise ValueError("stale routine lease")
    return dict(row)


def next_queued_run() -> dict[str, Any] | None:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM routine_runs WHERE status='queued' ORDER BY created_at,run_id LIMIT 1"
        ).fetchone()
    return None if row is None else dict(row)


def record_tool_effect_started(
    *, run_id: str, call_id: str, tool_name: str, expected_generation: int,
    holder: str | None = None, now: datetime | None = None,
) -> dict[str, Any]:
    effect_id = _id("effect")
    current = now or datetime.now(UTC)
    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            run = conn.execute(
                "SELECT * FROM routine_runs WHERE run_id=?", (run_id,),
            ).fetchone()
            if (
                run is None
                or run["status"] != "running"
                or int(run["lease_generation"]) != int(expected_generation)
                or (holder is not None and run["lease_holder"] != holder)
                or not run["lease_expires_at"]
                or str(run["lease_expires_at"]) <= current.isoformat()
            ):
                raise ValueError("stale routine lease")
            conn.execute(
                "INSERT INTO routine_tool_effects "
                "(effect_id,run_id,call_id,tool_name_enc,lease_generation,status,started_at) "
                "VALUES (?,?,?,?,?,'dispatching',?)",
                (effect_id, run_id, call_id,
                 seal(str(run["owner_user_id"]), tool_name.encode("utf-8")),
                 expected_generation, current.isoformat()),
            )
            effect = conn.execute(
                "SELECT * FROM routine_tool_effects WHERE effect_id=?", (effect_id,),
            ).fetchone()
            conn.commit()
            return dict(effect)
        except Exception:
            conn.rollback()
            raise


def settle_tool_effect(
    *, run_id: str, call_id: str, expected_generation: int, succeeded: bool,
    holder: str | None = None, now: datetime | None = None,
) -> dict[str, Any]:
    current = now or datetime.now(UTC)
    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            run = conn.execute(
                "SELECT * FROM routine_runs WHERE run_id=?", (run_id,),
            ).fetchone()
            if (
                run is None
                or run["status"] != "running"
                or int(run["lease_generation"]) != int(expected_generation)
                or (holder is not None and run["lease_holder"] != holder)
                or not run["lease_expires_at"]
                or str(run["lease_expires_at"]) <= current.isoformat()
            ):
                raise ValueError("stale routine lease")
            changed = conn.execute(
                "UPDATE routine_tool_effects SET status=?,finished_at=? "
                "WHERE run_id=? AND call_id=? AND status='dispatching' "
                "AND lease_generation=?",
                ("succeeded" if succeeded else "failed", current.isoformat(),
                 run_id, call_id, expected_generation),
            )
            if changed.rowcount != 1:
                raise ValueError("stale routine lease")
            effect = conn.execute(
                "SELECT * FROM routine_tool_effects WHERE run_id=? AND call_id=?",
                (run_id, call_id),
            ).fetchone()
            conn.commit()
            return dict(effect)
        except Exception:
            conn.rollback()
            raise


def list_open_tool_effects(run_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(
            "SELECT effect_id,run_id,call_id,lease_generation,status,started_at,finished_at "
            "FROM routine_tool_effects WHERE run_id=? AND status='dispatching' ORDER BY started_at",
            (run_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def reconcile_expired_runs(*, now: datetime) -> list[dict[str, Any]]:
    outcomes: list[dict[str, Any]] = []
    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            rows = conn.execute(
                "SELECT * FROM routine_runs WHERE status='running' AND lease_expires_at<=?",
                (now.isoformat(),),
            ).fetchall()
            for row in rows:
                open_effect = conn.execute(
                    "SELECT 1 FROM routine_tool_effects WHERE run_id=? AND status='dispatching' LIMIT 1",
                    (row["run_id"],),
                ).fetchone()
                if open_effect:
                    conn.execute(
                        "UPDATE routine_tool_effects SET status='outcome_unknown',finished_at=? "
                        "WHERE run_id=? AND status='dispatching'",
                        (now.isoformat(), row["run_id"]),
                    )
                    conn.execute(
                        "UPDATE routine_runs SET status='failed',diagnostic_code='tool_outcome_unknown',"
                        "lease_holder=NULL,lease_expires_at=NULL,finished_at=?,updated_at=? WHERE run_id=?",
                        (now.isoformat(), now.isoformat(), row["run_id"]),
                    )
                    outcomes.append({"run_id": row["run_id"], "status": "failed",
                                     "diagnostic_code": "tool_outcome_unknown"})
                else:
                    conn.execute(
                        "UPDATE routine_runs SET status='queued',diagnostic_code='lease_expired',"
                        "lease_holder=NULL,lease_expires_at=NULL,lease_generation=lease_generation+1,"
                        "updated_at=? WHERE run_id=?",
                        (now.isoformat(), row["run_id"]),
                    )
                    outcomes.append({"run_id": row["run_id"], "status": "queued",
                                     "diagnostic_code": "lease_expired"})
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    for outcome in outcomes:
        if outcome["status"] == "failed":
            append_run_event(
                run_id=str(outcome["run_id"]), kind="failed",
                payload={"diagnostic_code": "tool_outcome_unknown"}, terminal=True,
            )
    return outcomes


def update_execution_failure_count(routine_id: str, *, success: bool) -> int:
    with connect() as conn:
        _ensure_tables(conn)
        if success:
            conn.execute(
                "UPDATE routines SET consecutive_failures=0,updated_at=? WHERE routine_id=?",
                (_now(), routine_id),
            )
        else:
            conn.execute(
                "UPDATE routines SET consecutive_failures=consecutive_failures+1,updated_at=? "
                "WHERE routine_id=?", (_now(), routine_id),
            )
        row = conn.execute(
            "SELECT consecutive_failures FROM routines WHERE routine_id=?", (routine_id,),
        ).fetchone()
    if row is None:
        raise KeyError(routine_id)
    return int(row[0])


def get_execution_failure_count(routine_id: str) -> int:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT consecutive_failures FROM routines WHERE routine_id=?", (routine_id,),
        ).fetchone()
    if row is None:
        raise KeyError(routine_id)
    return int(row[0])


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


def complete_run_success(
    run_id: str, *, expected_generation: int, result: bytes,
    delivery_channel: str | None,
) -> dict[str, Any]:
    """Atomically persist success, its terminal event, and private outbox row."""
    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT * FROM routine_runs WHERE run_id=?", (run_id,),
            ).fetchone()
            if (
                row is None
                or row["status"] != "running"
                or int(row["lease_generation"]) != int(expected_generation)
            ):
                raise ValueError("stale routine lease")
            owner = str(row["owner_user_id"])
            now = _now()
            conn.execute(
                "UPDATE routine_runs SET status='succeeded',result_enc=?,diagnostic_code='',"
                "updated_at=?,finished_at=? WHERE run_id=?",
                (seal(owner, result), now, now, run_id),
            )
            channel = str(delivery_channel or "").strip().lower()
            if channel and channel != "none":
                conn.execute(
                    "INSERT INTO routine_deliveries "
                    "(delivery_id,run_id,owner_user_id,channel,status,payload_enc,created_at,updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (_id("delivery"), run_id, owner, channel, "pending",
                     seal(owner, result), now, now),
                )
            seq = int(conn.execute(
                "SELECT COALESCE(MAX(seq),0)+1 FROM routine_run_events WHERE run_id=?",
                (run_id,),
            ).fetchone()[0])
            conn.execute(
                "INSERT INTO routine_run_events "
                "(event_id,run_id,seq,kind,payload_enc,terminal,created_at) "
                "VALUES (?,?,?,?,?,1,?)",
                (_id("event"), run_id, seq, "succeeded",
                 seal(owner, _json_bytes({"diagnostic_code": ""})), now),
            )
            updated = conn.execute(
                "SELECT * FROM routine_runs WHERE run_id=?", (run_id,),
            ).fetchone()
            conn.commit()
            return dict(updated)
        except Exception:
            conn.rollback()
            raise


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


def claim_delivery_for_run(run_id: str, *, holder: str) -> dict[str, Any] | None:
    holder = str(holder or "").strip()
    if not holder:
        raise ValueError("holder is required")
    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT * FROM routine_deliveries WHERE run_id=? ORDER BY created_at LIMIT 1",
                (run_id,),
            ).fetchone()
            if row is None:
                conn.rollback()
                return None
            if row["status"] == "claimed" and row["lease_holder"] == holder:
                conn.commit()
                return dict(row)
            due = not row["next_attempt_at"] or str(row["next_attempt_at"]) <= _now()
            if row["status"] not in {"pending", "retry"} or not due:
                conn.rollback()
                return None
            now = _now()
            changed = conn.execute(
                "UPDATE routine_deliveries SET status='claimed',lease_holder=?,"
                "lease_generation=lease_generation+1,updated_at=? WHERE delivery_id=? "
                "AND status IN ('pending','retry')",
                (holder, now, row["delivery_id"]),
            )
            if changed.rowcount != 1:
                conn.rollback()
                return None
            claimed = conn.execute(
                "SELECT * FROM routine_deliveries WHERE delivery_id=?", (row["delivery_id"],),
            ).fetchone()
            conn.commit()
            return dict(claimed)
        except Exception:
            conn.rollback()
            raise


def claim_next_delivery(*, holder: str) -> dict[str, Any] | None:
    """Claim the oldest due outbox item across all Routine runs.

    The run worker and delivery worker are intentionally separate: retrying a
    delivery must never execute the Routine again.  This selector only sees
    durable outbox state and uses the same lease transition as the per-run
    claim path.
    """
    holder = str(holder or "").strip()
    if not holder:
        raise ValueError("holder is required")
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT run_id FROM routine_deliveries "
            "WHERE status IN ('pending','retry') "
            "AND (next_attempt_at IS NULL OR next_attempt_at='' OR next_attempt_at<=?) "
            "ORDER BY created_at,delivery_id LIMIT 1",
            (_now(),),
        ).fetchone()
    if row is None:
        return None
    return claim_delivery_for_run(str(row["run_id"]), holder=holder)


def settle_delivery(
    delivery_id: str, *, holder: str, outcome: str,
    next_attempt_at: str | None = None, receipt: bytes | None = None,
) -> dict[str, Any]:
    if outcome not in {"delivered", "retry", "failed"}:
        raise ValueError("invalid delivery outcome")
    with connect() as conn:
        _ensure_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT * FROM routine_deliveries WHERE delivery_id=?", (delivery_id,),
            ).fetchone()
            if row is None:
                raise KeyError(delivery_id)
            if row["status"] != "claimed" or str(row["lease_holder"] or "") != holder:
                raise ValueError("stale delivery lease")
            receipt_enc = row["receipt_enc"]
            if receipt is not None:
                receipt_enc = seal(str(row["owner_user_id"]), receipt)
            retry_count = int(row["retry_count"]) + (1 if outcome == "retry" else 0)
            conn.execute(
                "UPDATE routine_deliveries SET status=?,receipt_enc=?,retry_count=?,"
                "next_attempt_at=?,lease_holder=NULL,updated_at=? WHERE delivery_id=?",
                (outcome, receipt_enc, retry_count,
                 next_attempt_at if outcome == "retry" else None, _now(), delivery_id),
            )
            updated = conn.execute(
                "SELECT * FROM routine_deliveries WHERE delivery_id=?", (delivery_id,),
            ).fetchone()
            conn.commit()
            return dict(updated)
        except Exception:
            conn.rollback()
            raise


def count_runs(routine_id: str) -> int:
    with connect() as conn:
        _ensure_tables(conn)
        return int(conn.execute(
            "SELECT COUNT(*) FROM routine_runs WHERE routine_id=?", (routine_id,),
        ).fetchone()[0])


def set_inbox_preference(
    owner_user_id: str, *, routine_id: str = "", policy: Mapping[str, object],
) -> dict[str, object]:
    owner = str(owner_user_id or "").strip()
    if not owner:
        raise ValueError("owner_user_id is required")
    now = _now()
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            "INSERT INTO routine_inbox_preferences "
            "(owner_user_id,routine_id,policy_enc,created_at,updated_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(owner_user_id,routine_id) DO UPDATE SET "
            "policy_enc=excluded.policy_enc,updated_at=excluded.updated_at",
            (owner, routine_id, seal(owner, _json_bytes(policy)), now, now),
        )
    return dict(policy)


def get_inbox_preference(owner_user_id: str, *, routine_id: str = "") -> dict[str, object]:
    owner = str(owner_user_id or "").strip()
    if not owner:
        return {}
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT policy_enc FROM routine_inbox_preferences "
            "WHERE owner_user_id=? AND routine_id=?", (owner, routine_id),
        ).fetchone()
    return {} if row is None else dict(_open_json(owner, row[0]))


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


def get_legacy_routine_id(*, source_kind: str, source_id: str) -> str | None:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT routine_id FROM routine_legacy_links WHERE source_kind=? AND source_id=?",
            (source_kind, source_id),
        ).fetchone()
    return None if row is None or not row[0] else str(row[0])


def hidden_migrated_source_ids(
    *, source_kind: str, source_ids: list[str] | tuple[str, ...],
) -> set[str]:
    """Return only legacy rows covered by applied migration artifacts.

    Assigned rows have an exact legacy link. Quarantined rows remain sealed;
    their one-way source hash is enough to remove the corresponding legacy
    session from ordinary navigation without opening its private reference.
    """
    candidates = tuple(dict.fromkeys(str(value) for value in source_ids if value))
    if not candidates:
        return set()
    placeholders = ",".join("?" for _ in candidates)
    with connect() as conn:
        _ensure_tables(conn)
        linked = conn.execute(
            f"SELECT source_id FROM routine_legacy_links "
            f"WHERE source_kind=? AND source_id IN ({placeholders})",
            (source_kind, *candidates),
        ).fetchall()
        hashes = {
            hashlib.sha256(f"{source_kind}:{source_id}".encode("utf-8")).hexdigest(): source_id
            for source_id in candidates
        }
        quarantined = conn.execute(
            f"SELECT source_id_hash FROM routine_migration_quarantine "
            f"WHERE source_kind=? AND status='quarantined' "
            f"AND source_id_hash IN ({placeholders})",
            (source_kind, *hashes),
        ).fetchall()
    hidden = {str(row[0]) for row in linked}
    hidden.update(hashes[str(row[0])] for row in quarantined if str(row[0]) in hashes)
    return hidden


def run_exists_for_trigger(*, routine_id: str, idempotency_key: str) -> bool:
    with connect() as conn:
        _ensure_tables(conn)
        return conn.execute(
            "SELECT 1 FROM routine_runs WHERE routine_id=? AND idempotency_key=?",
            (routine_id, idempotency_key),
        ).fetchone() is not None
