"""Krypteret workspace-fil-I/O (spec §16, Lag 3).

To brugsformer:

1. **Eksplicit bruger** (`should_encrypt` / `write_workspace_file` / `read_workspace_file`):
   kalderen kender brugerens discord_id. Owner → plaintext; non-owner/ukendt →
   krypteret (.enc), fail-safe mod læk.

2. **Sti-nøglet** (`read_text_for_path` / `write_text_for_path`): kalderen har KUN
   en filsti og ved ikke hvilken bruger den tilhører (fx prompt-assembly der bygger
   for den aktive session, eller warmer-loop der itererer alle workspaces). Ejeren
   udledes fra `workspaces/<navn>/…` i stien. **Kun** filer under en registreret
   NON-owner members workspace krypteres; owner-workspace, shared Jarvis-state og
   ikke-bruger projekt-mapper forbliver plaintext. Dette er den sti readers/writers
   migreres til (Task 3.2).

**Feature-flag `ENCRYPT_ON_WRITE`** (env `JARVISX_ENCRYPT_WORKSPACES=1`, default OFF):
mens den er slået FRA skriver `write_text_for_path` altid plaintext, så readers/writers
kan migreres til helperen som en ren no-op. `read_text_for_path` læser ALTID `.enc`
transparent hvis den findes — uafhængigt af flaget — så læsning virker korrekt under og
efter udrulning. Krypteringen aktiveres først når hele læse-stien er migreret + verificeret.

Dekryptering sker KUN i memory (§16.5), aldrig skrevet i klartekst tilbage til disk.
"""
from __future__ import annotations

import os
from pathlib import Path

_ENC = ".enc"


def encrypt_on_write() -> bool:
    """True hvis non-owner skrivninger faktisk skal krypteres (sti-nøglet path).

    Default FALSE — så reader/writer-migration er en ren no-op indtil flippet.
    Aktivér med env JARVISX_ENCRYPT_WORKSPACES=1 (eller "true"/"yes").
    """
    return str(os.environ.get("JARVISX_ENCRYPT_WORKSPACES", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }


# ── Eksplicit-bruger API (member write med kendt discord_id) ────────────────

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
        return path

    from core.services.encryption import encrypt
    from core.services.keyring_store import get_user_key
    key = get_user_key(user_id)
    enc_path = path + _ENC
    with open(enc_path, "wb") as f:
        f.write(encrypt(data, key))
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
        from core.services.encryption import decrypt
        from core.services.keyring_store import get_user_key
        with open(enc_path, "rb") as f:
            return decrypt(f.read(), get_user_key(user_id))
    raise FileNotFoundError(path)


# ── Sti-nøglet API (readers/writers migreres hertil, Task 3.2) ──────────────

def member_user_id_for_path(path: str | os.PathLike) -> str | None:
    """Udled discord_id for filens NON-owner ejer ud fra `workspaces/<navn>/…`.

    Returnerer None hvis stien ikke ligger under en registreret members workspace
    (dvs. owner-workspace, shared/, projekt-mapper, eller ukendt → ikke-krypteres).
    """
    parts = Path(path).expanduser().parts
    try:
        i = len(parts) - 1 - parts[::-1].index("workspaces")
    except ValueError:
        return None
    if i + 1 >= len(parts):
        return None
    ws_name = parts[i + 1]
    # Ekskludér daemon-state under runtime/ — disse læses/skrives af daemons med
    # rå I/O (heartbeat-triggers, pkl-index) og må IKKE krypteres (§16 scope).
    rest = parts[i + 2:]
    if rest and rest[0] == "runtime":
        return None
    try:
        from core.identity.users import find_user_by_workspace
        u = find_user_by_workspace(ws_name)
    except Exception:
        return None
    if u is None or u.role == "owner":
        return None  # ukendt projekt-mappe eller owner → plaintext
    return u.discord_id


def read_text_for_path(path: str | os.PathLike, *, encoding: str = "utf-8") -> str | None:
    """Læs workspace-fil-tekst sti-nøglet. Returnerer None hvis hverken plaintext
    eller .enc findes. Dekrypterer transparent for member-filer (altid, uafhængigt
    af ENCRYPT_ON_WRITE — så læsning virker under/efter udrulning)."""
    p = str(path)
    member = member_user_id_for_path(p)
    enc_path = p + _ENC
    if member and os.path.exists(enc_path):
        from core.services.encryption import decrypt
        from core.services.keyring_store import get_user_key
        with open(enc_path, "rb") as f:
            return decrypt(f.read(), get_user_key(member)).decode(encoding, errors="replace")
    if os.path.exists(p):
        with open(p, "rb") as f:
            return f.read().decode(encoding, errors="replace")
    return None


def write_text_for_path(path: str | os.PathLike, content: str | bytes) -> str:
    """Skriv workspace-fil-tekst sti-nøglet. Mens ENCRYPT_ON_WRITE er FRA skrives
    altid plaintext (ren no-op-migration). Når den er TIL: member-filer → .enc med
    members DEK, owner/shared/projekt → plaintext. Returnerer skrevet sti."""
    p = str(path)
    data = content.encode("utf-8") if isinstance(content, str) else content
    member = member_user_id_for_path(p)
    if member and encrypt_on_write():
        from core.services.encryption import encrypt
        from core.services.keyring_store import get_user_key
        enc_path = p + _ENC
        with open(enc_path, "wb") as f:
            f.write(encrypt(data, get_user_key(member)))
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
        return enc_path
    with open(p, "wb") as f:
        f.write(data)
    return p
