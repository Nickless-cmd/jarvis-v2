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


def test_get_fresh_token_refreshes_when_expired(monkeypatch):
    _setup(monkeypatch)  # in-memory store + distinkt nøgle
    import core.services.oauth_flow as of
    ov.save_token("alice", "google", {"access_token": "old", "refresh_token": "r", "expires_at": 100.0})
    monkeypatch.setattr(of, "refresh_token", lambda prov, refresh, now=None: {"access_token": "new", "refresh_token": refresh, "expires_at": 9999.0})
    tok = ov.get_fresh_token("alice", "google", now=200.0)  # 200 > 100 → udløbet
    assert tok["access_token"] == "new"
    assert ov.get_token("alice", "google")["access_token"] == "new"  # re-saved


def test_get_fresh_token_keeps_valid(monkeypatch):
    _setup(monkeypatch)
    ov.save_token("alice", "google", {"access_token": "still-good", "refresh_token": "r", "expires_at": 9999.0})
    tok = ov.get_fresh_token("alice", "google", now=200.0)  # ikke udløbet
    assert tok["access_token"] == "still-good"


def test_blank_inputs_safe(monkeypatch):
    _setup(monkeypatch)
    assert ov.save_token("", "github", {"a": 1}) is False
    assert ov.save_token("alice", "", {"a": 1}) is False
    assert ov.save_token("alice", "github", "not-a-dict") is False  # type: ignore[arg-type]
    assert ov.get_token("", "github") is None
    assert ov.list_providers("") == []


# ── faldene skal efterlade et spor (31/10-2026) ──────────────────────────────
#
# MAALT 31/10-2026: fire `except Exception:` i denne fil returnerede en vaerdi
# uden at logge. `get_token` gav `None` for BAADE «intet token» og «dekrypteringen
# fejlede» — saa en doed refresh-token var strukturelt usynlig, og fladen sagde
# «ikke forbundet» om en forbindelse der findes men ikke kan laeses.
#
# Fail-soft er RIGTIGT og er bevaret: returvaerdien er uaendret. Det der blev
# tilfoejet er et spor, saa HVORFOR ikke forsvinder. Detektoren i
# `central_instrument` klassificerer ikke laengere disse som `except_silent` —
# maalt: et logget fald er slet ikke et fund.


def test_get_token_logger_naar_dekryptering_fejler(monkeypatch, caplog):
    """En token der FINDES men ikke kan laeses skal ikke se ud som ingen token."""
    store = _setup(monkeypatch)
    store["oauth_tokens"] = {"alice": {"github": " ikke-gyldig-base64 !!"}}
    with caplog.at_level("WARNING", logger="core.services.oauth_store"):
        assert ov.get_token("alice", "github") is None  # fail-soft bevaret
    assert any("kunne ikke laese token" in r.getMessage() for r in caplog.records), \
        "dekrypteringsfejl efterlod intet spor"


def test_get_token_logger_IKKE_naar_der_bare_ikke_er_noget(monkeypatch, caplog):
    """KONTROL: normal adfaerd maa ikke stoeje — ellers drukner de aegte fejl."""
    _setup(monkeypatch)
    with caplog.at_level("WARNING", logger="core.services.oauth_store"):
        assert ov.get_token("alice", "github") is None
    assert caplog.records == [], f"intet-token stoejede: {[r.message for r in caplog.records]}"


def test_save_token_logger_naar_gemning_fejler(monkeypatch, caplog):
    _setup(monkeypatch)

    def _braek(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(ov, "set_runtime_state_value", _braek)
    with caplog.at_level("WARNING", logger="core.services.oauth_store"):
        assert ov.save_token("alice", "github", {"access_token": "x"}) is False
    assert any("kunne ikke gemme token" in r.getMessage() for r in caplog.records), \
        "gemme-fejl efterlod intet spor"


def test_list_providers_logger_naar_laesning_fejler(monkeypatch, caplog):
    _setup(monkeypatch)

    def _braek(*a, **k):
        raise OSError("db locked")

    monkeypatch.setattr(ov, "get_runtime_state_value", _braek)
    with caplog.at_level("WARNING", logger="core.services.oauth_store"):
        assert ov.list_providers("alice") == []
    assert any("kunne ikke liste providere" in r.getMessage() for r in caplog.records), \
        "laase-fejl efterlod intet spor"
