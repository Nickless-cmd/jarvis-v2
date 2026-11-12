from __future__ import annotations

import pytest


def test_pbkdf2_deterministic_and_length() -> None:
    from core.services.keyring_store import derive_key_from_password
    salt = b"sixteenbytesalt!"
    k1 = derive_key_from_password("hunter2", salt)
    k2 = derive_key_from_password("hunter2", salt)
    assert k1 == k2 and len(k1) == 32


def test_pbkdf2_salt_changes_key() -> None:
    from core.services.keyring_store import derive_key_from_password
    a = derive_key_from_password("pw", b"saltsaltsaltsalt")
    b = derive_key_from_password("pw", b"differentsalt!!!")
    assert a != b


def test_get_user_key_via_fake_backend(monkeypatch) -> None:
    # Fake in-memory keyring → tester generate+gem+hent uden ægte OS-backend.
    import core.services.keyring_store as ks

    class _FakeKeyring:
        store: dict = {}
        def get_password(self, svc, uid): return self.store.get((svc, uid))
        def set_password(self, svc, uid, val): self.store[(svc, uid)] = val
        def delete_password(self, svc, uid): self.store.pop((svc, uid), None)

    fake = _FakeKeyring()
    monkeypatch.setattr(ks, "_keyring", lambda: fake)

    k1 = ks.get_user_key("mikkel")
    assert len(k1) == 32
    k2 = ks.get_user_key("mikkel")  # samme bruger → samme nøgle
    assert k1 == k2
    k_other = ks.get_user_key("mor")  # anden bruger → anden nøgle
    assert k_other != k1


def test_delete_user_key(monkeypatch) -> None:
    import core.services.keyring_store as ks

    class _FakeKeyring:
        def __init__(self): self.store = {}
        def get_password(self, svc, uid): return self.store.get((svc, uid))
        def set_password(self, svc, uid, val): self.store[(svc, uid)] = val
        def delete_password(self, svc, uid):
            if (svc, uid) not in self.store: raise KeyError
            del self.store[(svc, uid)]

    fake = _FakeKeyring()
    monkeypatch.setattr(ks, "_keyring", lambda: fake)
    ks.get_user_key("mikkel")
    assert ks.delete_user_key("mikkel") is True
    assert ks.delete_user_key("mikkel") is False  # væk nu


def test_headless_server_kek_dek(isolated_runtime, monkeypatch, tmp_path) -> None:
    # Headless (intet OS keyring) → server-side KEK/DEK: KEK i runtime.json,
    # wrapped DEK i DB. Samme bruger → samme DEK; delete → ulæseligt.
    import core.services.keyring_store as ks
    monkeypatch.setattr(ks, "_keyring", lambda: None)
    # Isolér runtime.json så testen ikke rører den ægte.
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")

    k1 = ks.get_user_key("mikkel")
    assert len(k1) == 32
    k2 = ks.get_user_key("mikkel")          # samme bruger → samme DEK (unwrapped)
    assert k1 == k2
    assert ks.get_user_key("mor") != k1      # anden bruger → anden DEK
    assert ks.delete_user_key("mikkel") is True
    assert ks.delete_user_key("mikkel") is False  # væk → GDPR-sletning effektiv


def test_keyring_probe_detects_fail_backend(monkeypatch) -> None:
    # Fail-backend (headless): get_password kaster → _keyring() skal returnere None.
    import core.services.keyring_store as ks
    import keyring as _kr

    class _FailBackend:
        def get_password(self, svc, uid):
            from keyring.errors import NoKeyringError
            raise NoKeyringError("no backend")

    monkeypatch.setattr(_kr, "get_keyring", lambda: _FailBackend())
    assert ks._keyring() is None


def test_keyring_probe_accepts_working_backend(monkeypatch) -> None:
    import core.services.keyring_store as ks
    import keyring as _kr

    class _OkBackend:
        def get_password(self, svc, uid):
            return None  # rigtig backend: ukendt key → None (ingen exception)

    monkeypatch.setattr(_kr, "get_keyring", lambda: _OkBackend())
    assert ks._keyring() is _kr


# ── En BLOKERET nøgleringe må ikke hænge processen (12/11-2026) ─────────────────
#
# Målt på CT105: den delte bash-session (daemon startet 4/11 fra en login-session)
# har DBUS_SESSION_BUS_ADDRESS, men jarvis-api/-runtime har den ikke. Hver
# Python-proces startet fra shellen fik derfor SecretService som backend; dens
# samling er låst, og `get_password` ventede evigt på en oplåsnings-dialog
# (stak: secretstorage.exec_prompt ← keyring_store._keyring ← get_user_key ←
# routine_migration.resolve_canonical_identity ← resolve_owner_target_session).
# 33 bash-kald i dag ramte 120 s-timeouten og blev kørt igen via fallback.
# Prober der hænger = ingen nøgleringe: brug server-KEK/DEK, som servicene gør.
@pytest.fixture
def _frisk_probe(monkeypatch):
    import core.services.keyring_store as ks

    monkeypatch.setattr(ks, "_KEYRING_BLOKERET", False)
    monkeypatch.setattr(ks, "_PROBE_TIMEOUT_S", 0.2)
    return ks


def test_en_blokeret_noegleringe_regnes_for_utilgaengelig(monkeypatch, _frisk_probe) -> None:
    import threading
    import time

    import keyring as _kr

    ks = _frisk_probe
    frigiv = threading.Event()

    class _Blokeret:
        def get_password(self, svc, uid):
            frigiv.wait(30)   # som secretstorage.exec_prompt: venter paa en dialog
            return None

    monkeypatch.setattr(_kr, "get_keyring", lambda: _Blokeret())
    try:
        t = time.monotonic()
        assert ks._keyring() is None
        assert time.monotonic() - t < 2.0
    finally:
        frigiv.set()


def test_blokeret_udfald_huskes_saa_hvert_kald_ikke_betaler_timeouten_igen(
        monkeypatch, _frisk_probe) -> None:
    import threading
    import time

    import keyring as _kr

    ks = _frisk_probe
    frigiv = threading.Event()
    kald: list[int] = []

    class _Blokeret:
        def get_password(self, svc, uid):
            kald.append(1)
            frigiv.wait(30)
            return None

    monkeypatch.setattr(_kr, "get_keyring", lambda: _Blokeret())
    try:
        assert ks._keyring() is None
        t = time.monotonic()
        assert ks._keyring() is None
        assert time.monotonic() - t < 0.1       # ingen ny ventetid
        assert len(kald) == 1                    # og ingen ny hængende tråd
    finally:
        frigiv.set()


def test_en_langsom_men_svarende_noegleringe_bruges_stadig(monkeypatch, _frisk_probe) -> None:
    import time

    import keyring as _kr

    ks = _frisk_probe

    class _Langsom:
        def get_password(self, svc, uid):
            time.sleep(0.05)
            return None

    monkeypatch.setattr(_kr, "get_keyring", lambda: _Langsom())
    assert ks._keyring() is _kr


def test_get_user_key_falder_til_server_dek_naar_noegleringen_blokerer(
        isolated_runtime, monkeypatch, _frisk_probe) -> None:
    """Hele vejen: en blokeret nøgleringe giver SAMME nøgle som servicenes
    server-DEK — ikke en ny tilfældig nøgle gemt i nøgleringen (split-brain)."""
    import threading

    import keyring as _kr

    ks = _frisk_probe
    frigiv = threading.Event()

    class _Blokeret:
        def get_password(self, svc, uid):
            frigiv.wait(30)

        def set_password(self, svc, uid, val):
            raise AssertionError("der maa ikke skrives en nøgle i en blokeret nøgleringe")

    monkeypatch.setattr(_kr, "get_keyring", lambda: _Blokeret())
    try:
        k = ks.get_user_key("bjorn")
        monkeypatch.setattr(ks, "_keyring", lambda: None)   # servicenes vej
        assert ks.get_user_key("bjorn") == k
    finally:
        frigiv.set()
