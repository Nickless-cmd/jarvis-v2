"""Signed, fail-closed ownership migration for legacy private recall data."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.services import scoped_recall_policy
from core.services.encryption import decrypt, encrypt


class InvalidRecallOwnershipReport(RuntimeError):
    pass


class RecallOwnershipSourceChanged(RuntimeError):
    pass


class MigrationDisabled(RuntimeError):
    pass


@dataclass(frozen=True)
class OwnershipItem:
    source_kind: str
    source_id_hash: str
    destination: str | None
    reason_code: str
    source_id: str = field(repr=False, default="")


@dataclass(frozen=True)
class RecallOwnershipReport:
    report_id: str
    watermark: str
    assigned: tuple[OwnershipItem, ...]
    quarantine: tuple[OwnershipItem, ...]

    @property
    def authoritative_count(self) -> int:
        return sum(item.reason_code == "authoritative_link" for item in self.assigned)

    @property
    def owner_fallback_count(self) -> int:
        return sum(item.reason_code == "owner_fallback" for item in self.assigned)

    @property
    def conflict_count(self) -> int:
        return len(self.quarantine)

    def destination_for(self, source_kind: str, source_id: str) -> str | None:
        return next(
            (item.destination for item in self.assigned
             if item.source_kind == source_kind and item.source_id == source_id),
            None,
        )

    def reason_for(self, source_kind: str, source_id: str) -> str | None:
        for item in (*self.assigned, *self.quarantine):
            if item.source_kind == source_kind and item.source_id == source_id:
                return item.reason_code
        return None


@dataclass(frozen=True)
class ApplyResult:
    updated: int
    quarantined: int
    already_applied: int


@dataclass(frozen=True)
class RollbackResult:
    restored: int
    quarantined_drift: int
    already_rolled_back: int


_DB_SOURCES = (
    ("experience", "cognitive_experiential_memories", "memory_id"),
    ("reasoning", "reasoning_conclusions", "conclusion_id"),
    ("active_recall", "recall_active_memories", "memory_id"),
    ("sensory", "sensory_memories", "id"),
)


def ensure_recall_ownership_migration_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recall_ownership_migration_log (
            report_id TEXT NOT NULL, source_kind TEXT NOT NULL,
            source_id_hash TEXT NOT NULL, previous_owner TEXT NOT NULL DEFAULT '',
            new_owner TEXT NOT NULL DEFAULT '', reason_code TEXT NOT NULL,
            applied_at TEXT NOT NULL, rolled_back_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (report_id, source_kind, source_id_hash)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recall_ownership_quarantine (
            source_kind TEXT NOT NULL, source_id_hash TEXT NOT NULL,
            reason_code TEXT NOT NULL, report_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (source_kind, source_id_hash)
        )
    """)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _source_hash(source_id: str) -> str:
    return hashlib.sha256(str(source_id).encode("utf-8")).hexdigest()


def _state_path() -> Path:
    from core.runtime import state_store

    return state_store._path("agent_observations")


def _report_dir() -> Path:
    from core.runtime.config import CACHE_DIR

    return Path(CACHE_DIR) / "recall-ownership-migration"


def report_path(report_id: str) -> Path:
    token = str(report_id or "")
    if not token.startswith("recall_") or not token.replace("_", "").isalnum():
        raise InvalidRecallOwnershipReport("invalid report id")
    return _report_dir() / f"{token}.json"


def _master_key() -> bytes:
    override = str(os.environ.get("JARVISX_ENCRYPTION_KEK") or "").strip()
    if override:
        return bytes.fromhex(override)
    from core.runtime.secrets import read_runtime_key

    return bytes.fromhex(str(read_runtime_key("encryption_kek")))


def _derived_key(label: str) -> bytes:
    return hmac.new(_master_key(), label.encode("utf-8"), hashlib.sha256).digest()


def _signature(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "signature"}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(_derived_key("recall-ownership-signing"), encoded, hashlib.sha256).hexdigest()


def _seal(report_id: str, value: dict[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    cipher = encrypt(raw, _derived_key(f"recall-ownership:{report_id}"))
    return base64.b64encode(cipher).decode("ascii")


def _open(report_id: str, value: str) -> dict[str, Any]:
    raw = decrypt(base64.b64decode(value), _derived_key(f"recall-ownership:{report_id}"))
    decoded = json.loads(raw.decode())
    if not isinstance(decoded, dict):
        raise InvalidRecallOwnershipReport("invalid sealed item")
    return decoded


def _linked_users(
    conn: sqlite3.Connection, *, session_id: str = "", run_id: str = "",
    explicit: list[str] | None = None,
) -> set[str]:
    def canonical(value: object) -> str:
        token = str(value or "").strip()
        if not token:
            return ""
        from core.services.routine_migration import resolve_canonical_identity
        return str(resolve_canonical_identity(token) or token)

    users = {canonical(value) for value in (explicit or []) if canonical(value)}
    if session_id and _table_exists(conn, "chat_messages"):
        users.update(
            canonical(row[0]) for row in conn.execute(
                "SELECT DISTINCT user_id FROM chat_messages "
                "WHERE session_id=? AND user_id IS NOT NULL AND user_id<>''", (session_id,)
            ).fetchall() if canonical(row[0])
        )
    if run_id and _table_exists(conn, "visible_runs"):
        cols = _columns(conn, "visible_runs")
        if "user_id" in cols:
            row = conn.execute("SELECT user_id FROM visible_runs WHERE run_id=?", (run_id,)).fetchone()
            if row and str(row[0] or "").strip():
                users.add(canonical(row[0]))
    return users


def _classify(users: set[str], owner_user_id: str) -> tuple[str | None, str]:
    if len(users) == 1:
        return next(iter(users)), "authoritative_link"
    if len(users) > 1:
        return None, "identity_conflict"
    return owner_user_id, "owner_fallback"


def _candidate_rows(conn: sqlite3.Connection, owner_user_id: str) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows: list[dict[str, Any]] = []
    for kind, table, pk in _DB_SOURCES:
        if not _table_exists(conn, table):
            continue
        cols = _columns(conn, table)
        if pk not in cols or "user_id" not in cols:
            continue
        select = [pk, "user_id"] + [name for name in ("session_id", "run_id") if name in cols]
        for row in conn.execute(
            f"SELECT {', '.join(select)} FROM {table} WHERE user_id IS NULL OR user_id='' ORDER BY {pk}"
        ):
            data = dict(row)
            source_id = str(data[pk])
            users = _linked_users(
                conn, session_id=str(data.get("session_id") or ""),
                run_id=str(data.get("run_id") or ""),
            )
            destination, reason = _classify(users, owner_user_id)
            rows.append({"kind": kind, "id": source_id, "destination": destination,
                         "reason": reason, "users": sorted(users)})

    if _table_exists(conn, "chat_messages"):
        sessions = conn.execute(
            "SELECT DISTINCT session_id FROM chat_messages "
            "WHERE user_id IS NULL OR user_id='' ORDER BY session_id"
        ).fetchall()
        for session in sessions:
            source_id = str(session[0])
            users = _linked_users(conn, session_id=source_id)
            destination, reason = _classify(users, owner_user_id)
            rows.append({"kind": "chat_session", "id": source_id, "destination": destination,
                         "reason": reason, "users": sorted(users)})

    if _table_exists(conn, "memory_write_queue"):
        for row in conn.execute(
            "SELECT queue_id, payload_json FROM memory_write_queue "
            "WHERE status IN ('pending','processing') ORDER BY queue_id"
        ):
            try:
                payload = json.loads(row[1] or "{}")
            except Exception:
                payload = {}
            if str(payload.get("user_id") or "").strip():
                continue
            users = _linked_users(
                conn, session_id=str(payload.get("session_id") or ""),
                run_id=str(payload.get("run_id") or ""),
                explicit=[str(payload.get("owner_user_id") or "")],
            )
            destination, reason = _classify(users, owner_user_id)
            rows.append({"kind": "memory_queue", "id": str(row[0]), "destination": destination,
                         "reason": reason, "users": sorted(users)})

    observations: list[dict[str, Any]] = []
    path = _state_path()
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            observations = loaded if isinstance(loaded, list) else []
        except Exception:
            observations = []
    for index, record in enumerate(observations):
        if not isinstance(record, dict) or str(record.get("user_id") or "").strip():
            continue
        source_id = str(record.get("obs_id") or f"index-{index}")
        users = _linked_users(
            conn, session_id=str(record.get("session_id") or ""),
            run_id=str(record.get("run_id") or ""),
            explicit=[str(record.get("owner_user_id") or "")],
        )
        destination, reason = _classify(users, owner_user_id)
        rows.append({"kind": "agent_observation", "id": source_id,
                     "destination": destination, "reason": reason, "users": sorted(users)})

    if _table_exists(conn, "private_brain_records") and "user_id" in _columns(conn, "private_brain_records"):
        for row in conn.execute(
            "SELECT record_id FROM private_brain_records WHERE user_id IS NULL OR user_id='' ORDER BY record_id"
        ):
            rows.append({"kind": "private_brain_audit", "id": str(row[0]), "destination": None,
                         "reason": "blank_private_brain_owner", "users": []})
    return rows


def _watermark(rows: list[dict[str, Any]]) -> str:
    ownership_only = [
        {"kind": row["kind"], "id_hash": _source_hash(row["id"]),
         "destination": row["destination"], "reason": row["reason"], "users": row["users"]}
        for row in rows
    ]
    return hashlib.sha256(
        json.dumps(ownership_only, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def classify_recall_ownership(
    conn: sqlite3.Connection, *, owner_user_id: str | None = None,
) -> RecallOwnershipReport:
    owner = str(owner_user_id or "").strip()
    if owner_user_id is None:
        from core.identity.owner_resolver import owner_user_id as resolve_owner
        from core.services.routine_migration import resolve_canonical_identity
        raw_owner = str(resolve_owner() or "").strip()
        owner = str(resolve_canonical_identity(raw_owner) or "").strip()
    if not owner:
        raise InvalidRecallOwnershipReport("canonical owner is unresolved")
    rows = _candidate_rows(conn, owner)
    report_id = f"recall_{uuid.uuid4().hex}"
    assigned: list[OwnershipItem] = []
    quarantine: list[OwnershipItem] = []
    sealed: list[str] = []
    for row in rows:
        item = OwnershipItem(
            source_kind=row["kind"], source_id_hash=_source_hash(row["id"]),
            destination=row["destination"], reason_code=row["reason"], source_id=row["id"],
        )
        (assigned if item.destination else quarantine).append(item)
        sealed.append(_seal(report_id, {"source_kind": item.source_kind, "source_id": item.source_id,
                                        "destination": item.destination, "reason_code": item.reason_code}))
    payload: dict[str, Any] = {
        "version": 1, "report_id": report_id,
        "owner": _seal(report_id, {"owner_user_id": owner}),
        "watermark": _watermark(rows), "items": sealed,
        "created_at": datetime.now(UTC).isoformat(),
    }
    payload["signature"] = _signature(payload)
    directory = _report_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    path = report_path(report_id)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.chmod(path, 0o600)
    return RecallOwnershipReport(report_id, payload["watermark"], tuple(assigned), tuple(quarantine))


def _load_report(report_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        payload = json.loads(report_path(report_id).read_text(encoding="utf-8"))
    except Exception as exc:
        raise InvalidRecallOwnershipReport("report missing or unreadable") from exc
    if not isinstance(payload, dict) or not hmac.compare_digest(
        str(payload.get("signature") or ""), _signature(payload)
    ):
        raise InvalidRecallOwnershipReport("report signature mismatch")
    items = [_open(report_id, str(value)) for value in payload.get("items", [])]
    return payload, items


def _update_item(conn: sqlite3.Connection, item: dict[str, Any], destination: str) -> bool:
    kind, source_id = str(item["source_kind"]), str(item["source_id"])
    mapping = {source_kind: (table, pk) for source_kind, table, pk in _DB_SOURCES}
    if kind in mapping:
        table, pk = mapping[kind]
        cur = conn.execute(
            f"UPDATE {table} SET user_id=? WHERE {pk}=? AND (user_id IS NULL OR user_id='')",
            (destination, source_id),
        )
        return cur.rowcount > 0
    if kind == "chat_session":
        cur = conn.execute(
            "UPDATE chat_messages SET user_id=? WHERE session_id=? AND (user_id IS NULL OR user_id='')",
            (destination, source_id),
        )
        return cur.rowcount > 0
    if kind == "memory_queue":
        row = conn.execute(
            "SELECT payload_json FROM memory_write_queue WHERE queue_id=?", (source_id,)
        ).fetchone()
        if not row:
            return False
        payload = json.loads(row[0] or "{}")
        if str(payload.get("user_id") or "").strip():
            return False
        payload["user_id"] = destination
        conn.execute("UPDATE memory_write_queue SET payload_json=? WHERE queue_id=?",
                     (json.dumps(payload, ensure_ascii=False), source_id))
        return True
    return False


def _observation_backup_path(report_id: str) -> Path:
    path = _state_path()
    return path.with_name(path.name + f".recall-owner.{report_id}.bak")


def _apply_observation_items(
    report_id: str, items: list[dict[str, Any]],
) -> tuple[int, Path | None, str, str]:
    targets = {str(item["source_id"]): str(item["destination"]) for item in items
               if item.get("source_kind") == "agent_observation" and item.get("destination")}
    if not targets:
        return 0, None, "", ""
    path = _state_path()
    if not path.exists():
        return 0, None, "", ""
    before = path.read_bytes()
    records = json.loads(before.decode("utf-8"))
    changed = 0
    for index, record in enumerate(records if isinstance(records, list) else []):
        source_id = str(record.get("obs_id") or f"index-{index}") if isinstance(record, dict) else ""
        if source_id in targets and not str(record.get("user_id") or "").strip():
            record["user_id"] = targets[source_id]
            changed += 1
    if not changed:
        return 0, None, hashlib.sha256(before).hexdigest(), hashlib.sha256(before).hexdigest()
    backup = _observation_backup_path(report_id)
    backup.write_bytes(before)
    os.chmod(backup, 0o600)
    temp = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)
    after_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return changed, backup, hashlib.sha256(before).hexdigest(), after_hash


def apply_report(report_id: str) -> ApplyResult:
    from core.runtime.db_core import connect

    if not scoped_recall_policy.recall_migration_enabled():
        raise MigrationDisabled("recall ownership migration kill switch is off")
    backup: Path | None = None
    try:
        payload, items = _load_report(report_id)
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            ensure_recall_ownership_migration_tables(conn)
            applied_rows = conn.execute(
                "SELECT COUNT(*) FROM recall_ownership_migration_log "
                "WHERE report_id=? AND rolled_back_at=''", (report_id,)
            ).fetchone()[0]
            assignment_count = sum(bool(item.get("destination")) for item in items)
            if assignment_count and applied_rows >= assignment_count:
                return ApplyResult(0, 0, assignment_count)
            owner = str(_open(report_id, str(payload["owner"]))["owner_user_id"])
            current = _candidate_rows(conn, owner)
            if _watermark(current) != payload.get("watermark"):
                raise RecallOwnershipSourceChanged("recall sources changed after dry-run")

            observation_changed, backup, before_hash, after_hash = _apply_observation_items(report_id, items)
            now = datetime.now(UTC).isoformat()
            updated = observation_changed
            quarantined = 0
            try:
                conn.commit()
                conn.execute("BEGIN IMMEDIATE")
                for item in items:
                    kind = str(item["source_kind"])
                    source_id = str(item["source_id"])
                    source_hash = _source_hash(source_id)
                    destination = str(item.get("destination") or "")
                    reason = str(item.get("reason_code") or "")
                    if not destination:
                        conn.execute(
                            "INSERT OR IGNORE INTO recall_ownership_quarantine "
                            "(source_kind, source_id_hash, reason_code, report_id, created_at) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (kind, source_hash, reason, report_id, now),
                        )
                        quarantined += int(conn.execute("SELECT changes()").fetchone()[0] > 0)
                        continue
                    changed = kind != "agent_observation" and _update_item(conn, item, destination)
                    if changed:
                        updated += 1
                    if changed or kind == "agent_observation":
                        previous = before_hash if kind == "agent_observation" else ""
                        new_owner = after_hash if kind == "agent_observation" else destination
                        conn.execute(
                            "INSERT OR IGNORE INTO recall_ownership_migration_log "
                            "(report_id, source_kind, source_id_hash, previous_owner, new_owner, "
                            "reason_code, applied_at, rolled_back_at) VALUES (?, ?, ?, ?, ?, ?, ?, '')",
                            (report_id, kind, source_hash, previous, new_owner, reason, now),
                        )
                conn.commit()
            except Exception:
                conn.rollback()
                if backup and backup.exists():
                    os.replace(backup, _state_path())
                raise
        return ApplyResult(updated, quarantined, 0)
    finally:
        scoped_recall_policy.set_recall_migration_enabled(False)


def rollback_report(report_id: str) -> RollbackResult:
    from core.runtime.db_core import connect

    if not scoped_recall_policy.recall_migration_enabled():
        raise MigrationDisabled("recall ownership migration kill switch is off")
    try:
        _payload, items = _load_report(report_id)
        by_key = {(str(item["source_kind"]), _source_hash(str(item["source_id"]))): item for item in items}
        restored = drift = already = 0
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            ensure_recall_ownership_migration_tables(conn)
            logs = conn.execute(
                "SELECT * FROM recall_ownership_migration_log WHERE report_id=?", (report_id,)
            ).fetchall()
            now = datetime.now(UTC).isoformat()
            conn.commit()
            conn.execute("BEGIN IMMEDIATE")
            observation_restored = False
            for log in logs:
                if log["rolled_back_at"]:
                    already += 1
                    continue
                key = (str(log["source_kind"]), str(log["source_id_hash"]))
                item = by_key.get(key)
                if not item:
                    drift += 1
                    continue
                kind, source_id = key[0], str(item["source_id"])
                destination = str(item.get("destination") or "")
                if kind == "agent_observation":
                    if observation_restored:
                        restored += 1
                    else:
                        path = _state_path()
                        backup = _observation_backup_path(report_id)
                        current_hash = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
                        backup_hash = hashlib.sha256(backup.read_bytes()).hexdigest() if backup.exists() else ""
                        if current_hash == str(log["new_owner"]) and backup_hash == str(log["previous_owner"]):
                            os.replace(backup, path)
                            observation_restored = True
                            restored += 1
                        else:
                            drift += 1
                            conn.execute(
                                "INSERT OR IGNORE INTO recall_ownership_quarantine "
                                "(source_kind, source_id_hash, reason_code, report_id, created_at) "
                                "VALUES (?, ?, 'rollback_drift', ?, ?)", (kind, key[1], report_id, now),
                            )
                    conn.execute(
                        "UPDATE recall_ownership_migration_log SET rolled_back_at=? "
                        "WHERE report_id=? AND source_kind=? AND source_id_hash=?",
                        (now, report_id, kind, key[1]),
                    )
                    continue
                mapping = {source_kind: (table, pk) for source_kind, table, pk in _DB_SOURCES}
                if kind in mapping:
                    table, pk = mapping[kind]
                    cur = conn.execute(
                        f"UPDATE {table} SET user_id=NULL WHERE {pk}=? AND user_id=?",
                        (source_id, destination),
                    )
                elif kind == "chat_session":
                    cur = conn.execute(
                        "UPDATE chat_messages SET user_id='' WHERE session_id=? AND user_id=?",
                        (source_id, destination),
                    )
                elif kind == "memory_queue":
                    row = conn.execute("SELECT payload_json FROM memory_write_queue WHERE queue_id=?", (source_id,)).fetchone()
                    cur = None
                    if row:
                        queue_payload = json.loads(row[0] or "{}")
                        if queue_payload.get("user_id") == destination:
                            queue_payload.pop("user_id", None)
                            conn.execute("UPDATE memory_write_queue SET payload_json=? WHERE queue_id=?",
                                         (json.dumps(queue_payload, ensure_ascii=False), source_id))
                            restored += 1
                else:
                    cur = None
                if cur is not None and cur.rowcount:
                    restored += 1
                elif kind != "memory_queue":
                    drift += 1
                    conn.execute(
                        "INSERT OR IGNORE INTO recall_ownership_quarantine "
                        "(source_kind, source_id_hash, reason_code, report_id, created_at) "
                        "VALUES (?, ?, 'rollback_drift', ?, ?)", (kind, key[1], report_id, now),
                    )
                conn.execute(
                    "UPDATE recall_ownership_migration_log SET rolled_back_at=? "
                    "WHERE report_id=? AND source_kind=? AND source_id_hash=?",
                    (now, report_id, kind, key[1]),
                )
            conn.commit()
        return RollbackResult(restored, drift, already)
    finally:
        scoped_recall_policy.set_recall_migration_enabled(False)


__all__ = [
    "ApplyResult", "InvalidRecallOwnershipReport", "MigrationDisabled",
    "RecallOwnershipReport", "RecallOwnershipSourceChanged", "RollbackResult",
    "apply_report", "classify_recall_ownership", "ensure_recall_ownership_migration_tables",
    "report_path", "rollback_report",
]
