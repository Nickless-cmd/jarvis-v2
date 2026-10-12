import pytest

from core.services.encryption import DecryptionError
from core.services.routine_crypto import open_sealed, seal


def test_routine_seal_is_owner_bound(monkeypatch):
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda owner: (owner.encode("utf-8") + b"x" * 32)[:32],
    )
    blob = seal("user-a", b"private")
    assert b"private" not in blob
    assert open_sealed("user-a", blob) == b"private"
    with pytest.raises(DecryptionError):
        open_sealed("user-b", blob)
