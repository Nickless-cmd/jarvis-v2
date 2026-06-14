"""AES-256-GCM kryptering for bruger-data at-rest (spec §16, Lag 1).

Authenticated encryption (GCM) — krypteret OG tamper-proof. IV (12 byte) tilfældig
pr. operation, præfikset til ciphertext. Nøglen er 256-bit; den holdes i memory som
bytearray og kan zeroes eksplicit (§16.3 regel 4).

§16.2: owners egen workspace krypteres IKKE; andre brugeres data + chat-historik +
private brain-records gør. §16.6: selv med owner-override kan Jarvis ikke dekryptere
en anden brugers indhold uden deres key — kryptografisk håndhævet privatliv.
"""
from __future__ import annotations

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_IV_BYTES = 12
_KEY_BYTES = 32  # 256-bit
_ENC_SUFFIX = ".enc"


class DecryptionError(Exception):
    """Dekryptering fejlede — forkert nøgle eller manipuleret data (GCM-tag)."""


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """AES-256-GCM. Returnerer IV(12) || ciphertext+tag. key skal være 32 byte."""
    if len(key) != _KEY_BYTES:
        raise ValueError(f"key skal være {_KEY_BYTES} byte (256-bit)")
    iv = os.urandom(_IV_BYTES)
    ct = AESGCM(bytes(key)).encrypt(iv, plaintext, None)
    return iv + ct


def decrypt(blob: bytes, key: bytes) -> bytes:
    """Dekryptér IV || ciphertext. Rejser DecryptionError ved forkert key/tamper."""
    if len(key) != _KEY_BYTES:
        raise ValueError(f"key skal være {_KEY_BYTES} byte (256-bit)")
    if len(blob) < _IV_BYTES + 16:
        raise DecryptionError("for kort til at indeholde IV + GCM-tag")
    iv, ct = blob[:_IV_BYTES], blob[_IV_BYTES:]
    try:
        return AESGCM(bytes(key)).decrypt(iv, ct, None)
    except InvalidTag as exc:
        raise DecryptionError("forkert nøgle eller manipuleret data") from exc


def encrypt_file(path: str, key: bytes) -> str:
    """Krypter en fil → <path>.enc, fjern originalen. Returnér .enc-stien."""
    with open(path, "rb") as f:
        data = f.read()
    enc_path = path + _ENC_SUFFIX
    with open(enc_path, "wb") as f:
        f.write(encrypt(data, key))
    os.replace(enc_path, enc_path)  # no-op flush-sikring
    try:
        os.remove(path)
    except OSError:
        pass
    return enc_path


def decrypt_file(enc_path: str, key: bytes) -> bytes:
    """Dekryptér en .enc-fil i memory (skrives ALDRIG i klartekst til disk, §16.5)."""
    with open(enc_path, "rb") as f:
        return decrypt(f.read(), key)


def new_key() -> bytearray:
    """Ny tilfældig 256-bit nøgle som bytearray (kan zeroes)."""
    return bytearray(os.urandom(_KEY_BYTES))


def zero_key(key: bytearray) -> None:
    """Nulstil nøgle-bytes i memory (§16.3 regel 4). Best-effort i Python."""
    try:
        for i in range(len(key)):
            key[i] = 0
    except (TypeError, ValueError):
        pass
