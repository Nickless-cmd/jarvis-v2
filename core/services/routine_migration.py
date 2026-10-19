"""Fail-closed, evidence-driven migration of legacy autonomous sources."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime import db_routines
from core.services.encryption import decrypt, encrypt
from core.services.routine_crypto import seal


from core.services.routine_trigger_adapters import SYSTEM_PRODUCERS
_QUARANTINE_PRINCIPAL = "__migration_quarantine__"
_SYSTEM_SESSION_ORIGINS = {
    "council": "council",
    "dream": "dream",
    "heartbeat": "heartbeat",
    "wakeup": "wakeup",
}


class InvalidMigrationReport(RuntimeError):
    """A report is missing, malformed, or fails signature verification."""


class MigrationSourceChanged(RuntimeError):
    """Legacy sources changed after classification; a fresh dry-run is required."""


@dataclass(frozen=True)
class MigrationItem:
    source_kind: str
    source_id_hash: str
    reason_code: str
    evidence_codes: tuple[str, ...]
    destination: str | None = None
    content: None = None


@dataclass(frozen=True)
class MigrationReport:
    report_id: str
    watermark: str
    assigned: tuple[MigrationItem, ...]
    quarantine: tuple[MigrationItem, ...]

    @property
    def assigned_count(self) -> int:
        return len(self.assigned)

    @property
    def quarantine_count(self) -> int:
        return len(self.quarantine)


@dataclass(frozen=True)
class ApplyResult:
    created_routines: int
    created_quarantine: int
    already_applied: int


def resolve_canonical_identity(value: object) -> str | None:
    """Resolve a structured token to one active canonical database user."""
    token = str(value or "").strip()
    if not token:
        return None
    from core.runtime import db

    direct = db.get_user_row(token)
    if direct and not direct.get("deleted_at"):
        return str(direct["user_id"])

    # External IDs are encrypted. A dry-run must not create missing DEKs, so
    # only identities with an already-persisted wrapped key are decryptable.
    from core.services.encryption import decrypt
    from core.services.keyring_store import get_user_key

    matches: list[str] = []
    for row in db.list_user_rows(include_deleted=False):
        user_id = str(row.get("user_id") or "")
        encrypted = row.get("discord_id_enc")
        if not user_id or not encrypted:
            continue
        if not db.get_runtime_state_value(f"user_dek:{user_id}", ""):
            continue
        try:
            candidate = decrypt(bytes(encrypted), get_user_key(user_id)).decode("utf-8")
        except Exception:  # Unreadable legacy identity is ambiguity, never authority.
            continue
        if candidate == token:
            matches.append(user_id)
    return matches[0] if len(matches) == 1 else None


def _report_dir() -> Path:
    from core.runtime.config import CACHE_DIR

    return Path(CACHE_DIR) / "routine-migration"


def report_path(report_id: str) -> Path:
    token = str(report_id or "")
    if not token.startswith("migration_") or not token.replace("_", "").isalnum():
        raise InvalidMigrationReport("invalid report id")
    return _report_dir() / f"{token}.json"


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,),
    ).fetchone() is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _selected(row: sqlite3.Row, names: set[str]) -> dict[str, object]:
    return {name: row[name] for name in sorted(names)}


def _source_rows(conn: sqlite3.Connection) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    if _table_exists(conn, "recurring_tasks"):
        columns = _columns(conn, "recurring_tasks")
        wanted = columns & {
            "task_id", "focus", "source", "status", "interval_minutes", "channel",
            "user_id", "structured_recipient", "verified_owner_user_id", "updated_at",
        }
        for row in conn.execute("SELECT * FROM recurring_tasks ORDER BY task_id"):
            sources.append({"source_kind": "recurring", **_selected(row, wanted)})
    if _table_exists(conn, "scheduled_tasks"):
        columns = _columns(conn, "scheduled_tasks")
        wanted = columns & {
            "task_id", "focus", "source", "status", "run_at", "scheduled_for_user_id",
            "initiated_by", "updated_at",
        }
        for row in conn.execute("SELECT * FROM scheduled_tasks ORDER BY task_id"):
            sources.append({"source_kind": "scheduled", **_selected(row, wanted)})
    if _table_exists(conn, "visible_runs"):
        columns = _columns(conn, "visible_runs")
        wanted = columns & {
            "run_id", "lane", "status", "user_id", "workspace_name", "finished_at",
        }
        for row in conn.execute(
            "SELECT * FROM visible_runs WHERE lane IN ('autonomous','recurring','scheduled') "
            "ORDER BY run_id"
        ):
            sources.append({"source_kind": "visible_run", **_selected(row, wanted)})
    if _table_exists(conn, "chat_sessions"):
        columns = _columns(conn, "chat_sessions")
        wanted = columns & {"session_id", "updated_at", "workspace_kind", "workspace_root"}
        for row in conn.execute(
            "SELECT * FROM chat_sessions WHERE session_id LIKE 'auto-%' ORDER BY session_id"
        ):
            sources.append({"source_kind": "autonomous_session", **_selected(row, wanted)})
    return sources


def _source_id(row: dict[str, object]) -> str:
    for key in ("task_id", "run_id", "session_id"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return "unknown"


def _source_hash(kind: str, source_id: str) -> str:
    return hashlib.sha256(f"{kind}:{source_id}".encode("utf-8")).hexdigest()


def _watermark(rows: list[dict[str, object]]) -> str:
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _signing_key() -> bytes:
    return hmac.new(_report_master_key(), b"routine-migration-signing", hashlib.sha256).digest()


def _report_master_key() -> bytes:
    override = str(os.environ.get("JARVISX_ENCRYPTION_KEK") or "").strip()
    if override:
        return bytes.fromhex(override)
    from core.runtime.secrets import read_runtime_key

    return bytes.fromhex(str(read_runtime_key("encryption_kek")))


def _artifact_key(principal: str) -> bytes:
    return hmac.new(
        _report_master_key(), f"routine-migration:{principal}".encode("utf-8"),
        hashlib.sha256,
    ).digest()


def _signature(payload: dict[str, object]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "signature"}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(_signing_key(), encoded, hashlib.sha256).hexdigest()


def _sealed_json(principal: str, value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return base64.b64encode(encrypt(encoded, _artifact_key(principal))).decode("ascii")


def _open_json(principal: str, value: str) -> dict[str, object]:
    raw = decrypt(base64.b64decode(value.encode("ascii")), _artifact_key(principal))
    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise InvalidMigrationReport("invalid sealed report entry")
    return decoded


def _system_owner() -> str | None:
    from core.identity.owner_resolver import owner_user_id

    return resolve_canonical_identity(owner_user_id())


def _registered_system_producer(row: dict[str, object]) -> str:
    producer = str(row.get("source") or "").strip()
    if producer in SYSTEM_PRODUCERS:
        return producer
    session_id = str(row.get("session_id") or "").strip()
    for origin, registered in _SYSTEM_SESSION_ORIGINS.items():
        if session_id.startswith(f"auto-{origin}-"):
            return registered
    return ""


def _classify(row: dict[str, object]) -> tuple[str | None, str, tuple[str, ...]]:
    source_kind = str(row["source_kind"])
    producer = _registered_system_producer(row)
    if producer:
        owner = _system_owner()
        if owner:
            evidence = (
                "registered_system_session_origin"
                if source_kind == "autonomous_session"
                else "registered_system_producer"
            )
            return owner, "system_owner", (evidence, "canonical_owner")
        return None, "system_owner_unresolved", ("registered_system_producer",)

    verified = str(row.get("verified_owner_user_id") or "").strip()
    recipient = verified or str(
        row.get("structured_recipient") or row.get("scheduled_for_user_id") or ""
    ).strip()
    if not recipient:
        return None, "missing_structured_owner", ("no_authoritative_recipient",)
    resolved_recipient = resolve_canonical_identity(recipient)
    if not resolved_recipient:
        return None, "unresolved_structured_owner", ("recipient_resolution_failed",)

    creator_token = str(row.get("user_id") or row.get("initiated_by") or "").strip()
    creator = resolve_canonical_identity(creator_token) if creator_token else None
    if creator and creator != resolved_recipient:
        return None, "identity_conflict", ("creator_recipient_disagreement",)
    evidence = ["canonical_ownership_link" if verified else "structured_recipient"]
    if creator:
        evidence.append("creator_corrobates_recipient")
    if source_kind in {"visible_run", "autonomous_session"}:
        evidence.append("legacy_segment")
    return resolved_recipient, "user_private", tuple(evidence)


def _definition(row: dict[str, object]) -> dict[str, object]:
    kind = str(row["source_kind"])
    source_id = _source_id(row)
    if kind == "recurring":
        trigger_kind = "interval"
        trigger_config = {"interval_minutes": int(row.get("interval_minutes") or 60)}
    elif kind == "scheduled":
        trigger_kind = "schedule"
        trigger_config = {"run_at": str(row.get("run_at") or "")}
    else:
        trigger_kind = "manual"
        trigger_config = {}
    # KLASSIFIKATION (19/10-2026): en legacy-opgave har ikke noget *valg* —
    # kun de felter nogen skrev dengang. Vi afleder derfor det nærmeste vi kan
    # komme og siger det højt, frem for at lade feltet stå tomt så runneren
    # skal gætte:
    #
    # * `session_id` sat  -> opgaven var bundet til en samtale dengang, så
    #   `session` er den tro adfærd. Ellers `background` (den isolerede silo).
    # * `importance`      -> `normal`. Der findes ingen evidens for andet, og
    #   at gætte `high` ville fremhæve støj i indbakken.
    #
    # En migreret rutine oprettes `paused`, så klassifikationen kan gennemgås
    # før den første affyring — den er et udgangspunkt, ikke en dom.
    from core.services.routine_classification import classify_routine

    klassifikation = classify_routine(
        execution_mode="session" if str(row.get("session_id") or "").strip() else "background",
        importance="normal",
    )
    return {
        "name": f"Migrated {kind}",
        "instruction": str(row.get("focus") or "Legacy autonomous work"),
        "capability_scope": "system" if _registered_system_producer(row) else "chat",
        "trigger_kind": trigger_kind,
        "trigger_config": trigger_config,
        "delivery_policy": {
            "channel": str(row.get("channel") or "auto"),
            "classification": klassifikation.as_dict(),
        },
        "source_id": source_id,
    }


def classify_legacy_sources(conn: sqlite3.Connection) -> MigrationReport:
    """Classify without mutating source, Routine, link, or quarantine rows."""
    rows = _source_rows(conn)
    report_id = f"migration_{uuid.uuid4().hex}"
    assigned_public: list[MigrationItem] = []
    quarantine_public: list[MigrationItem] = []
    stored_items: list[dict[str, object]] = []
    for row in rows:
        kind = str(row["source_kind"])
        source_id = _source_id(row)
        source_hash = _source_hash(kind, source_id)
        owner, classification, evidence = _classify(row)
        public = MigrationItem(
            source_kind=kind,
            source_id_hash=source_hash,
            reason_code="assigned" if owner else classification,
            evidence_codes=evidence,
            destination=classification if owner else None,
        )
        principal = owner or _QUARANTINE_PRINCIPAL
        stored: dict[str, object] = {
            "source_kind": kind,
            "source_id_hash": source_hash,
            "reason_code": public.reason_code,
            "evidence_codes": list(evidence),
            "owner_user_id": owner or "",
            "access_scope": classification if owner else "",
            "source_ref_enc": _sealed_json(principal, {"source_id": source_id}),
        }
        if owner:
            stored["definition_enc"] = _sealed_json(owner, _definition(row))
            assigned_public.append(public)
        else:
            quarantine_public.append(public)
        stored_items.append(stored)
    payload: dict[str, object] = {
        "report_id": report_id,
        "created_at": datetime.now(UTC).isoformat(),
        "watermark": _watermark(rows),
        "items": stored_items,
    }
    payload["signature"] = _signature(payload)
    path = report_path(report_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.chmod(path, 0o600)
    return MigrationReport(
        report_id=report_id,
        watermark=str(payload["watermark"]),
        assigned=tuple(assigned_public),
        quarantine=tuple(quarantine_public),
    )


def _load_report(report_id: str) -> dict[str, object]:
    path = report_path(report_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise InvalidMigrationReport("migration report cannot be loaded") from exc
    if not isinstance(payload, dict) or not hmac.compare_digest(
        str(payload.get("signature") or ""), _signature(payload)
    ):
        raise InvalidMigrationReport("migration report signature is invalid")
    return payload


def _legacy_link_exists(conn: sqlite3.Connection, kind: str, source_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM routine_legacy_links WHERE source_kind=? AND source_id=?",
        (kind, source_id),
    ).fetchone() is not None


def apply_report(report_id: str) -> ApplyResult:
    """Apply one signed report iff its exact legacy source watermark is current."""
    from core.runtime.db_core import connect

    payload = _load_report(report_id)
    with connect() as conn:
        if _watermark(_source_rows(conn)) != payload.get("watermark"):
            raise MigrationSourceChanged("legacy sources changed; run a new dry-run")
    created = 0
    quarantined = 0
    already = 0
    for raw in payload.get("items", []):
        if not isinstance(raw, dict):
            raise InvalidMigrationReport("invalid migration item")
        owner = str(raw.get("owner_user_id") or "")
        principal = owner or _QUARANTINE_PRINCIPAL
        source = _open_json(principal, str(raw["source_ref_enc"]))
        source_id = str(source["source_id"])
        kind = str(raw["source_kind"])
        with connect() as conn:
            if _legacy_link_exists(conn, kind, source_id):
                already += 1
                continue
        if not owner:
            with connect() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM routine_migration_quarantine "
                    "WHERE source_kind=? AND source_id_hash=?",
                    (kind, str(raw["source_id_hash"])),
                ).fetchone()
            if exists is not None:
                already += 1
                continue
            db_routines.put_quarantine(
                source_kind=kind,
                source_id_hash=str(raw["source_id_hash"]),
                source_reference=source,
                classifier_evidence={"codes": list(raw.get("evidence_codes") or [])},
                reason_code=str(raw["reason_code"]),
            )
            quarantined += 1
            continue
        definition = _open_json(owner, str(raw["definition_enc"]))
        routine_id = f"routine_migrated_{str(raw['source_id_hash'])[:24]}"
        with connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM routines WHERE routine_id=?", (routine_id,),
            ).fetchone()
        if exists is None:
            db_routines.create_routine(
                routine_id=routine_id,
                owner_user_id=owner,
                access_scope=str(raw["access_scope"]),
                created_by="migration",
                status="paused",
                name=str(definition["name"]),
                instruction=str(definition["instruction"]).encode("utf-8"),
                capability_scope=str(definition["capability_scope"]),
                trigger_kind=str(definition["trigger_kind"]),
                trigger_config=dict(definition.get("trigger_config") or {}),
                permission_policy={},
                delivery_policy=dict(definition.get("delivery_policy") or {}),
                inbox_policy={},
                retention_policy={"archive_stopped_days": 30},
                failure_policy={"consecutive_failures": 3},
            )
            created += 1
        with connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO routine_legacy_links "
                "(legacy_link_id,routine_id,run_id,source_kind,source_id,source_ref_enc,created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (f"legacy_{str(raw['source_id_hash'])[:24]}", routine_id, None, kind,
                 source_id, seal(owner, json.dumps(source).encode("utf-8")),
                 datetime.now(UTC).isoformat()),
            )
    return ApplyResult(created, quarantined, already)
