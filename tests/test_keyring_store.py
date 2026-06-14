from __future__ import annotations


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
