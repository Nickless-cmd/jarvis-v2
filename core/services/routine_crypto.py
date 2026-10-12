"""Owner-bound authenticated encryption for Routine content."""
from __future__ import annotations

from core.services.encryption import decrypt, encrypt


def _owner_key(owner_user_id: str) -> bytes:
    owner = str(owner_user_id or "").strip()
    if not owner:
        raise ValueError("owner_user_id is required for sealed routine content")
    # Import at call time so test isolation and key lifecycle patches remain valid.
    from core.services.keyring_store import get_user_key

    return get_user_key(owner)


def seal(owner_user_id: str, payload: bytes) -> bytes:
    if not isinstance(payload, bytes):
        raise TypeError("routine payload must be bytes")
    return encrypt(payload, _owner_key(owner_user_id))


def open_sealed(owner_user_id: str, blob: bytes) -> bytes:
    if not isinstance(blob, bytes):
        blob = bytes(blob)
    return decrypt(blob, _owner_key(owner_user_id))
