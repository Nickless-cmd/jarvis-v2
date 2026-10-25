"""Explicit users.json -> canonical account cutover for Routine ownership.

This is deliberately separate from routine content migration.  A legacy
Discord identifier becomes evidence only after this cutover has created an
active ``users.user_id`` row with an encrypted external-identity link.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from core.identity.users import load_users
from core.runtime import db
from core.services.encryption import decrypt, encrypt
from core.services import keyring_store
from core.services.routine_migration import resolve_canonical_identity


_CANONICAL_NAMESPACE = uuid.UUID("4ad10883-12dd-4ca5-8ccc-3214ee2ba63b")


class IdentitySourceChanged(RuntimeError):
    """The source registry changed since the reviewed dry-run."""


class IdentityMigrationConflict(RuntimeError):
    """At least one legacy identity cannot be linked without guessing."""


@dataclass(frozen=True)
class IdentityCutoverItem:
    legacy_fingerprint: str
    canonical_user_id: str
    role: str
    workspace: str
    action: str
    reason_code: str = ""


@dataclass(frozen=True)
class IdentityCutoverReport:
    watermark: str
    items: tuple[IdentityCutoverItem, ...]

    @property
    def create_count(self) -> int:
        return sum(item.action == "create" for item in self.items)

    @property
    def linked_count(self) -> int:
        return sum(item.action == "already_linked" for item in self.items)

    @property
    def conflict_count(self) -> int:
        return sum(item.action == "conflict" for item in self.items)


@dataclass(frozen=True)
class IdentityCutoverResult:
    created: int
    already_linked: int


def _canonical_id(discord_id: str) -> str:
    # Stable across dry-run/apply and opaque enough for an internal primary key.
    # Authorization never relies on this value being secret or unguessable.
    return uuid.uuid5(_CANONICAL_NAMESPACE, f"legacy-discord:{discord_id}").hex


def _fingerprint(discord_id: str) -> str:
    return hashlib.sha256(f"legacy-discord:{discord_id}".encode()).hexdigest()


def _source_payload() -> list[dict[str, str]]:
    return sorted(
        ({
            "discord_id": str(user.discord_id),
            "name": str(user.name),
            "role": str(user.role),
            "workspace": str(user.workspace),
        } for user in load_users()),
        key=lambda item: (item["discord_id"], item["workspace"]),
    )


def _watermark(source: list[dict[str, str]]) -> str:
    identity_rows = [
        {
            "user_id": str(row.get("user_id") or ""),
            "workspace": str(row.get("workspace") or ""),
            "deleted_at": str(row.get("deleted_at") or ""),
            "discord_blob": hashlib.sha256(bytes(row.get("discord_id_enc") or b"")).hexdigest(),
        }
        for row in db.list_user_rows(include_deleted=True)
    ]
    encoded = json.dumps(
        {"source": source, "identity_rows": identity_rows},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _expected_target_matches(external_id: str, row: dict[str, object]) -> bool:
    """Verify our deterministic target without treating its ID as proof."""
    from core.runtime import db as runtime_db
    from core.services.keyring_store import get_user_key as load_user_key

    user_id = str(row.get("user_id") or "")
    blob = row.get("discord_id_enc")
    if not user_id or not blob:
        return False
    if not runtime_db.get_runtime_state_value(f"user_dek:{user_id}", ""):
        return False
    try:
        linked = decrypt(bytes(blob), load_user_key(user_id)).decode("utf-8")
    except Exception:  # Unreadable encrypted identity cannot prove a match.
        return False
    return linked == external_id


def plan_legacy_identity_cutover() -> IdentityCutoverReport:
    source = _source_payload()
    duplicate_ids = {
        item["discord_id"] for item in source
        if sum(other["discord_id"] == item["discord_id"] for other in source) > 1
    }
    items: list[IdentityCutoverItem] = []
    for legacy in source:
        external_id = legacy["discord_id"]
        canonical = resolve_canonical_identity(external_id)
        action = "already_linked" if canonical else "create"
        reason = ""
        if external_id in duplicate_ids:
            action, reason = "conflict", "duplicate_external_identity"
        elif not canonical:
            canonical = _canonical_id(external_id)
            target = db.get_user_row(canonical)
            if target and not target.get("deleted_at") and _expected_target_matches(
                external_id, target
            ):
                action = "already_linked"
            elif target and not target.get("deleted_at"):
                action, reason = "conflict", "canonical_target_collision"
            else:
                occupied = next((
                    row for row in db.list_user_rows(include_deleted=False)
                    if str(row.get("workspace") or "") == legacy["workspace"]
                ), None)
                if occupied:
                    action, reason = "conflict", "workspace_owned_by_unlinked_account"
        items.append(IdentityCutoverItem(
            legacy_fingerprint=_fingerprint(external_id),
            canonical_user_id=str(canonical or ""),
            role=legacy["role"],
            workspace=legacy["workspace"],
            action=action,
            reason_code=reason,
        ))
    return IdentityCutoverReport(watermark=_watermark(source), items=tuple(items))


def apply_legacy_identity_cutover(*, expected_watermark: str) -> IdentityCutoverResult:
    report = plan_legacy_identity_cutover()
    if not expected_watermark or expected_watermark != report.watermark:
        raise IdentitySourceChanged("identity source changed; run a new dry-run")
    if report.conflict_count:
        raise IdentityMigrationConflict("identity cutover contains unresolved conflicts")

    source_by_fingerprint = {
        _fingerprint(item["discord_id"]): item for item in _source_payload()
    }
    created = 0
    for item in report.items:
        if item.action != "create":
            continue
        legacy = source_by_fingerprint[item.legacy_fingerprint]
        user_id = item.canonical_user_id
        now = datetime.now(UTC).isoformat()
        discord_blob = encrypt(
            legacy["discord_id"].encode("utf-8"), keyring_store.get_user_key(user_id)
        )
        db.insert_user_row(
            user_id=user_id,
            email_hash=f"legacy-identity:{user_id}",
            email_enc=b"",
            name=legacy["name"],
            role=legacy["role"],
            workspace=legacy["workspace"],
            password_hash="",
            discord_id_enc=discord_blob,
            totp_seed_enc=b"",
            created_at=now,
            updated_at=now,
        )
        if legacy["role"] == "owner":
            db.update_user_row(user_id, {"tier": "owner", "updated_at": now})
        created += 1
    return IdentityCutoverResult(
        created=created,
        already_linked=report.linked_count,
    )


__all__ = [
    "IdentityCutoverItem",
    "IdentityCutoverReport",
    "IdentityCutoverResult",
    "IdentityMigrationConflict",
    "IdentitySourceChanged",
    "apply_legacy_identity_cutover",
    "plan_legacy_identity_cutover",
]
