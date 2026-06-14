from __future__ import annotations

import os

import pytest


@pytest.fixture
def _users(isolated_runtime, tmp_path, monkeypatch):
    """Isolér users.json + runtime.json (KEK) + brug headless server-DEK."""
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    import core.services.keyring_store as ks
    monkeypatch.setattr(ks, "_keyring", lambda: None)  # headless → KEK/DEK
    from core.identity.users import add_user
    add_user(discord_id="d-bjorn", name="Bjørn", role="owner")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member")
    yield tmp_path


def test_owner_writes_plaintext(_users) -> None:
    from core.services.workspace_crypto import write_workspace_file, read_workspace_file
    p = str(_users / "owner_MEMORY.md")
    written = write_workspace_file(p, "Bjørns ting", "d-bjorn")
    assert written == p and not written.endswith(".enc")
    assert os.path.exists(p)
    assert read_workspace_file(p, "d-bjorn").decode() == "Bjørns ting"


def test_member_writes_encrypted(_users) -> None:
    from core.services.workspace_crypto import write_workspace_file, read_workspace_file
    p = str(_users / "mikkel_MEMORY.md")
    written = write_workspace_file(p, "Mikkels hemmelighed", "d-mikkel")
    assert written.endswith(".enc")
    assert not os.path.exists(p)               # ingen plaintext tilbage
    # Filen på disk er IKKE læsbar som klartekst
    with open(written, "rb") as f:
        raw = f.read()
    assert b"hemmelighed" not in raw
    # Men dekrypteres korrekt i memory
    assert read_workspace_file(p, "d-mikkel").decode() == "Mikkels hemmelighed"


def test_member_data_unreadable_after_key_delete(_users) -> None:
    # GDPR §16.7: slet key → krypteret data kan ikke længere dekrypteres.
    from core.services.workspace_crypto import write_workspace_file, read_workspace_file
    from core.services.keyring_store import delete_user_key
    from core.services.encryption import DecryptionError
    p = str(_users / "mikkel2.md")
    write_workspace_file(p, "slet mig", "d-mikkel")
    assert delete_user_key("d-mikkel") is True
    with pytest.raises(DecryptionError):
        read_workspace_file(p, "d-mikkel")  # ny DEK ≠ gammel → ulæseligt


def test_unknown_user_fails_safe_encrypted(_users) -> None:
    # Ukendt bruger → krypteres (fail-safe mod læk), ikke plaintext.
    from core.services.workspace_crypto import write_workspace_file
    p = str(_users / "unknown.md")
    written = write_workspace_file(p, "x", "ukendt-id")
    assert written.endswith(".enc")


# ── Sti-nøglet API (reader/writer-migration, Task 3.2) ──────────────────────

@pytest.fixture
def _ws_tree(_users, tmp_path, monkeypatch):
    """Byg en JARVIS_HOME/workspaces/{bjorn,mikkel,freelance}-struktur."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from core.identity.users import add_user
    # _users har allerede d-bjorn(owner)/d-mikkel(member); giv dem workspace-navne.
    add_user(discord_id="d-bjorn", name="Bjørn", role="owner", workspace="bjorn")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")
    ws = tmp_path / "workspaces"
    for name in ("bjorn", "mikkel", "freelance"):
        (ws / name).mkdir(parents=True, exist_ok=True)
    return ws


def test_member_user_id_for_path(_ws_tree) -> None:
    from core.services.workspace_crypto import member_user_id_for_path
    assert member_user_id_for_path(_ws_tree / "mikkel" / "MEMORY.md") == "d-mikkel"
    assert member_user_id_for_path(_ws_tree / "bjorn" / "MEMORY.md") is None    # owner
    assert member_user_id_for_path(_ws_tree / "freelance" / "x.md") is None      # projekt
    assert member_user_id_for_path("/etc/passwd") is None                        # uden for workspaces


def test_write_text_for_path_flag_off_is_plaintext(_ws_tree, monkeypatch) -> None:
    # ENCRYPT_ON_WRITE FRA → selv member-filer skrives plaintext (no-op-migration).
    monkeypatch.delenv("JARVISX_ENCRYPT_WORKSPACES", raising=False)
    from core.services.workspace_crypto import write_text_for_path, read_text_for_path
    p = _ws_tree / "mikkel" / "MEMORY.md"
    written = write_text_for_path(p, "Mikkels ting")
    assert written == str(p) and not written.endswith(".enc")
    assert read_text_for_path(p) == "Mikkels ting"


def test_write_text_for_path_flag_on_member_encrypted(_ws_tree, monkeypatch) -> None:
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    import core.services.keyring_store as ks
    monkeypatch.setattr(ks, "_keyring", lambda: None)
    from core.services.workspace_crypto import write_text_for_path, read_text_for_path
    p = _ws_tree / "mikkel" / "MEMORY.md"
    written = write_text_for_path(p, "hemmelig")
    assert written.endswith(".enc")
    assert not os.path.exists(p)                     # ingen plaintext tilbage
    with open(written, "rb") as f:
        assert b"hemmelig" not in f.read()           # disk = ciphertext
    assert read_text_for_path(p) == "hemmelig"        # transparent dekryptering


def test_write_text_for_path_flag_on_owner_plaintext(_ws_tree, monkeypatch) -> None:
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    from core.services.workspace_crypto import write_text_for_path
    p = _ws_tree / "bjorn" / "MEMORY.md"
    written = write_text_for_path(p, "Bjørns ting")  # owner → plaintext selv med flag on
    assert written == str(p) and not written.endswith(".enc")


def test_read_text_for_path_missing_returns_none(_ws_tree) -> None:
    from core.services.workspace_crypto import read_text_for_path
    assert read_text_for_path(_ws_tree / "mikkel" / "NOPE.md") is None
