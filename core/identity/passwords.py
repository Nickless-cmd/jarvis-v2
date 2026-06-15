"""Password-hashing (spec 2026-06-15 §5.2) — bcrypt, cost-factor 12.

Ren helper: hash + verify. Aldrig logning af klartekst-passwords.
"""
from __future__ import annotations

import bcrypt

_ROUNDS = 12


def hash_password(plaintext: str) -> str:
    """bcrypt-hash (cost 12). Returnerer en utf-8-streng ($2b$…)."""
    h = bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt(rounds=_ROUNDS))
    return h.decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    """True hvis password matcher hash. Fejl-tolerant (ugyldigt hash → False)."""
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
