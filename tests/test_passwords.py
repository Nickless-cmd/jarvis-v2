"""Tests for password hashing (spec 2026-06-15 §5.2)."""
from __future__ import annotations

from core.identity.passwords import hash_password, verify_password


def test_hash_then_verify_true() -> None:
    h = hash_password("hemmelig123")
    assert isinstance(h, str) and h.startswith("$2")
    assert verify_password("hemmelig123", h) is True


def test_verify_wrong_password_false() -> None:
    h = hash_password("rigtig")
    assert verify_password("forkert", h) is False


def test_two_hashes_of_same_password_differ() -> None:
    assert hash_password("x") != hash_password("x")  # random salt


def test_verify_handles_garbage_hash() -> None:
    assert verify_password("x", "ikke-et-hash") is False
