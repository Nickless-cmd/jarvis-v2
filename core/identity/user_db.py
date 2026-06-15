"""Højniveau-bruger-adapter (spec 2026-06-15) ovenpå users-tabellen.

Følsomme felter (email, discord_id, totp_seed, api_key) krypteres per-bruger med
keyring_store.get_user_key + encryption.encrypt. email_hash (HMAC-SHA256 over
normaliseret email + en server-pepper) er deterministisk så login kan slå op
uden at dekryptere alle brugere. Aldrig klartekst-password lagret (kun bcrypt).
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any

from core.identity.passwords import hash_password, verify_password
from core.runtime.secrets import read_runtime_key
from core.services.encryption import decrypt, encrypt
from core.services.keyring_store import get_user_key
from core.runtime import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def _email_hash(email: str) -> str:
    """Deterministisk opslags-hash. Pepper fra runtime (eller fast fallback)."""
    try:
        pepper = str(read_runtime_key("user_email_pepper"))
    except Exception:
        pepper = "jarvis-user-email-pepper-v1"
    return hmac.new(pepper.encode("utf-8"), _norm_email(email).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _enc(user_id: str, value: str) -> bytes:
    if not value:
        return b""
    return encrypt(value.encode("utf-8"), get_user_key(user_id))


def _dec(user_id: str, blob: bytes | None) -> str:
    if not blob:
        return ""
    try:
        return decrypt(bytes(blob), get_user_key(user_id)).decode("utf-8")
    except Exception:
        return ""


def _row_to_public(row: dict[str, Any]) -> dict[str, Any]:
    uid = str(row["user_id"])
    return {
        "user_id": uid,
        "email": _dec(uid, row.get("email_enc")),
        "name": row.get("name", ""),
        "role": row.get("role", "member"),
        "workspace": row.get("workspace", ""),
        "discord_id": _dec(uid, row.get("discord_id_enc")),
        "api_key": _dec(uid, row.get("api_key_enc")),
        "api_key_jti": row.get("api_key_jti", "") or "",
        "has_api_key": bool(row.get("api_key_jti")),
        "email_verified": bool(row.get("email_verified")),
        "tier": row.get("tier", "") or "",
        "muted": bool(row.get("muted")),
        "consent_data_processing": bool(row.get("consent_data_processing")),
        "consent_marketing": bool(row.get("consent_marketing")),
        "consent_blind_access": bool(row.get("consent_blind_access")),
        "created_at": row.get("created_at", ""),
        "updated_at": row.get("updated_at", ""),
        "deleted_at": row.get("deleted_at"),
    }


def create_user(*, email: str, name: str, password: str, role: str = "member",
                workspace: str | None = None) -> dict[str, Any]:
    norm = _norm_email(email)
    if not norm:
        raise ValueError("email påkrævet")
    eh = _email_hash(norm)
    if db.get_user_row_by_email_hash(eh):
        raise ValueError("email allerede registreret")
    user_id = uuid.uuid4().hex
    ws = workspace or user_id
    now = _now()
    db.insert_user_row(
        user_id=user_id, email_hash=eh, email_enc=_enc(user_id, norm), name=name,
        role=role, workspace=ws, password_hash=hash_password(password),
        discord_id_enc=b"", totp_seed_enc=b"", created_at=now, updated_at=now,
    )
    return get_user(user_id)  # type: ignore[return-value]


def get_user(user_id: str) -> dict[str, Any] | None:
    row = db.get_user_row(user_id)
    return _row_to_public(row) if row else None


def find_user_by_email(email: str) -> dict[str, Any] | None:
    row = db.get_user_row_by_email_hash(_email_hash(email))
    return _row_to_public(row) if row else None


def verify_login(email: str, password: str) -> dict[str, Any] | None:
    row = db.get_user_row_by_email_hash(_email_hash(email))
    if not row or row.get("deleted_at"):
        return None
    if not verify_password(password, str(row.get("password_hash") or "")):
        return None
    return _row_to_public(row)


def set_email_verified(user_id: str, verified: bool = True) -> bool:
    return db.update_user_row(user_id, {"email_verified": 1 if verified else 0,
                                        "updated_at": _now()})


def mute_user(user_id: str) -> bool:
    return db.update_user_row(user_id, {"muted": 1, "updated_at": _now()})


def unmute_user(user_id: str) -> bool:
    return db.update_user_row(user_id, {"muted": 0, "updated_at": _now()})


def set_quota_tier(user_id: str, tier: str) -> bool:
    if tier not in ("free", "plus", "pro", "owner"):
        raise ValueError(f"ukendt tier '{tier}'")
    return db.update_user_row(user_id, {"tier": tier, "updated_at": _now()})


def set_consent(user_id: str, *, data_processing: bool | None = None,
                marketing: bool | None = None, blind_access: bool | None = None) -> bool:
    fields: dict[str, Any] = {"updated_at": _now()}
    if data_processing is not None:
        fields["consent_data_processing"] = 1 if data_processing else 0
    if marketing is not None:
        fields["consent_marketing"] = 1 if marketing else 0
    if blind_access is not None:
        fields["consent_blind_access"] = 1 if blind_access else 0
    return db.update_user_row(user_id, fields)


def list_users(*, include_deleted: bool = False) -> list[dict[str, Any]]:
    return [_row_to_public(r) for r in db.list_user_rows(include_deleted=include_deleted)]
