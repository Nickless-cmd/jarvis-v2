"""Per-bruger krypteret OAuth-token-hvælv — round-trip + kryptografisk isolation."""
from __future__ import annotations

import hashlib

import core.services.oauth_store as ov
from core.services.encryption import DecryptionError, decrypt


def _setup(monkeypatch):
    """In-memory runtime_state + distinkt 32-byte nøgle pr. bruger (som keyring)."""
    store: dict = {}
    monkeypatch.setattr(ov, "get_runtime_state_value", lambda k, d=None: store.get(k, d))
    monkeypatch.setattr(ov, "set_runtime_state_value", lambda k, v, **kw: store.__setitem__(k, v))
    monkeypatch.setattr(
        ov, "get_user_key",
        lambda uid: hashlib.sha256(f"oauth-test-key:{uid}".encode()).digest(),
    )
    return store


def test_save_and_get_roundtrip(monkeypatch):
    _setup(monkeypatch)
    tok = {"access_token": "gho_abc", "refresh_token": "r1", "expires_at": 123}
    assert ov.save_token("alice", "github", tok) is True
    assert ov.get_token("alice", "github") == tok


def test_provider_case_insensitive(monkeypatch):
    _setup(monkeypatch)
    ov.save_token("alice", "GitHub", {"access_token": "x"})
    assert ov.get_token("alice", "github") == {"access_token": "x"}


def test_cryptographic_isolation_between_users(monkeypatch):
    """Bruger B kan ALDRIG læse A's token — hverken via API eller med B's nøgle."""
    store = _setup(monkeypatch)
    ov.save_token("alice", "github", {"access_token": "alice-secret"})

    # API: bob har ingen token
    assert ov.get_token("bob", "github") is None

    # Kryptografisk: B's nøgle kan ikke dekryptere A's gemte blob
    import base64
    a_blob = base64.b64decode(store["oauth_tokens"]["alice"]["github"])
    bob_key = hashlib.sha256(b"oauth-test-key:bob").digest()
    try:
        decrypt(a_blob, bob_key)
        assert False, "B's nøgle dekrypterede A's token — isolation brudt!"
    except DecryptionError:
        pass  # forventet — privatliv kryptografisk håndhævet


def test_has_token_and_list_providers(monkeypatch):
    _setup(monkeypatch)
    assert ov.has_token("alice", "github") is False
    ov.save_token("alice", "github", {"access_token": "x"})
    ov.save_token("alice", "google", {"access_token": "y"})
    assert ov.has_token("alice", "github") is True
    assert ov.list_providers("alice") == ["github", "google"]
    assert ov.list_providers("bob") == []


def test_revoke(monkeypatch):
    _setup(monkeypatch)
    ov.save_token("alice", "github", {"access_token": "x"})
    assert ov.revoke_token("alice", "github") is True
    assert ov.get_token("alice", "github") is None


def test_blank_inputs_safe(monkeypatch):
    _setup(monkeypatch)
    assert ov.save_token("", "github", {"a": 1}) is False
    assert ov.save_token("alice", "", {"a": 1}) is False
    assert ov.save_token("alice", "github", "not-a-dict") is False  # type: ignore[arg-type]
    assert ov.get_token("", "github") is None
    assert ov.list_providers("") == []
