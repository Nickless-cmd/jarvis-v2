from __future__ import annotations

import os

import pytest

KEY = bytes(range(32))


def test_roundtrip() -> None:
    from core.services.encryption import encrypt, decrypt
    pt = "Mikkels private MEMORY.md\nhemmeligt".encode("utf-8")
    blob = encrypt(pt, KEY)
    assert blob != pt
    assert decrypt(blob, KEY) == pt


def test_wrong_key_fails() -> None:
    from core.services.encryption import encrypt, decrypt, DecryptionError
    blob = encrypt(b"hej", KEY)
    with pytest.raises(DecryptionError):
        decrypt(blob, bytes(range(1, 33)))


def test_tamper_detected() -> None:
    from core.services.encryption import encrypt, decrypt, DecryptionError
    blob = bytearray(encrypt(b"vigtigt", KEY))
    blob[-1] ^= 0x01  # flip én byte i tag/ciphertext
    with pytest.raises(DecryptionError):
        decrypt(bytes(blob), KEY)


def test_iv_random_per_op() -> None:
    from core.services.encryption import encrypt
    assert encrypt(b"x", KEY) != encrypt(b"x", KEY)  # forskellig IV


def test_key_length_validation() -> None:
    from core.services.encryption import encrypt
    with pytest.raises(ValueError):
        encrypt(b"x", b"kort")


def test_file_roundtrip(tmp_path) -> None:
    from core.services.encryption import encrypt_file, decrypt_file
    p = tmp_path / "MEMORY.md"
    p.write_text("indhold", encoding="utf-8")
    enc = encrypt_file(str(p), KEY)
    assert enc.endswith(".enc")
    assert not os.path.exists(str(p))  # original fjernet
    assert decrypt_file(enc, KEY).decode("utf-8") == "indhold"


def test_zero_key() -> None:
    from core.services.encryption import new_key, zero_key
    k = new_key()
    assert any(b != 0 for b in k)
    zero_key(k)
    assert all(b == 0 for b in k)
