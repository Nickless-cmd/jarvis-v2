"""Krypteret workspace-fil-I/O (spec §16, Lag 3 Task 3.1).

Ren wrapper: skriv/læs en workspace-fil krypteret for NON-owner-brugere, plaintext
for owner (§16.2). Krypterede filer får `.enc`; dekryptering sker KUN i memory (§16.5),
aldrig skrevet i klartekst til disk.

**Dette modul wirer IKKE sig selv ind i memory-laget** — det er Task 3.2 (den
data-rørende integration). Her er kun byggestenen, fuldt testbar på tmp-filer.
"""
from __future__ import annotations

import os

_ENC = ".enc"


def should_encrypt(user_id: str) -> bool:
    """True hvis denne brugers data skal krypteres (alle undtagen owner, §16.2).

    Owner (Bjørns egen workspace) er plaintext. Ubundet ("") = owner-kontekst.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return False  # ubundet = owner
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(uid)
        if u is not None and u.role == "owner":
            return False
    except Exception:
        pass
    # Kendt non-owner ELLER ukendt → krypter (fail-safe mod læk).
    return True


def write_workspace_file(path: str, content: str | bytes, user_id: str) -> str:
    """Skriv en workspace-fil. Non-owner → krypteret (.enc); owner → plaintext.

    Returnerer den faktiske sti der blev skrevet. Ved kryptering fjernes en evt.
    gammel plaintext-variant så data ikke ligger ukrypteret tilbage.
    """
    data = content.encode("utf-8") if isinstance(content, str) else content
    if not should_encrypt(user_id):
        with open(path, "wb") as f:
            f.write(data)
        # Ryd en evt. forældet .enc (owner skiftede ikke fra krypteret her, men defensivt)
        return path

    from core.services.encryption import encrypt
    from core.services.keyring_store import get_user_key
    key = get_user_key(user_id)
    enc_path = path + _ENC
    with open(enc_path, "wb") as f:
        f.write(encrypt(data, key))
    # Fjern en evt. gammel plaintext-variant
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
    return enc_path


def read_workspace_file(path: str, user_id: str) -> bytes:
    """Læs en workspace-fil. Prøver krypteret (.enc) først for non-owner, ellers
    plaintext. Rejser FileNotFoundError hvis ingen variant findes."""
    enc_path = path + _ENC
    if should_encrypt(user_id) and os.path.exists(enc_path):
        from core.services.encryption import decrypt
        from core.services.keyring_store import get_user_key
        with open(enc_path, "rb") as f:
            return decrypt(f.read(), get_user_key(user_id))
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    if os.path.exists(enc_path):
        # Krypteret findes men should_encrypt=False (rolle-skift?) — kræver key.
        from core.services.encryption import decrypt
        from core.services.keyring_store import get_user_key
        with open(enc_path, "rb") as f:
            return decrypt(f.read(), get_user_key(user_id))
    raise FileNotFoundError(path)
