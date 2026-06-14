"""Per-bruger nøgle-håndtering (spec §16.3, Lag 1).

Primær: OS keyring (gnome-keyring/kwallet/Keychain/Credential Manager via `keyring`).
Fallback: PBKDF2-deriveret nøgle fra et password (600.000 iterationer, salt pr. bruger).

Nøgle-lifecycle (§16.3): logges aldrig, sendes aldrig over netværk (denne modul gør
ingen af delene), persisteres aldrig i klartekst (kun i OS keyring). Ny nøgle ved
user-delete invaliderer gammel krypteret data (GDPR sletningsret).
"""
from __future__ import annotations

import base64
import hashlib
import os

_SERVICE = "jarvis-v2-encryption"
_PBKDF2_ITERATIONS = 600_000
_KEY_BYTES = 32


def _keyring():
    try:
        import keyring
        return keyring
    except Exception:
        return None


def get_user_key(user_id: str) -> bytes:
    """Hent (eller generér) en brugers 256-bit krypteringsnøgle fra OS keyring.

    Genererer en tilfældig nøgle ved første kald og gemmer den i keyring. Rejser
    RuntimeError hvis intet keyring-backend findes (brug derive_key_from_password).
    """
    uid = str(user_id or "").strip()
    if not uid:
        raise ValueError("user_id påkrævet")
    kr = _keyring()
    if kr is None:
        raise RuntimeError("intet OS keyring-backend; brug derive_key_from_password")
    stored = kr.get_password(_SERVICE, uid)
    if stored:
        return base64.b64decode(stored)
    key = os.urandom(_KEY_BYTES)
    kr.set_password(_SERVICE, uid, base64.b64encode(key).decode("ascii"))
    return key


def delete_user_key(user_id: str) -> bool:
    """Slet en brugers nøgle (GDPR §16.7) — krypteret data bliver derefter ulæseligt."""
    uid = str(user_id or "").strip()
    kr = _keyring()
    if kr is None or not uid:
        return False
    try:
        kr.delete_password(_SERVICE, uid)
        return True
    except Exception:
        return False


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256 nøgle-derivation (fallback, §16.3). 600k iterationer."""
    return hashlib.pbkdf2_hmac(
        "sha256", str(password or "").encode("utf-8"), salt,
        _PBKDF2_ITERATIONS, dklen=_KEY_BYTES,
    )


def new_salt() -> bytes:
    """Tilfældigt 16-byte salt (gemmes pr. bruger, ikke hemmeligt)."""
    return os.urandom(16)
