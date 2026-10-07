"""Tests for workspace_bootstrap — især §16 .enc-aware seeding."""
from __future__ import annotations

import pytest


@pytest.fixture
def _member_env(isolated_runtime, tmp_path, monkeypatch):
    """Isolér users.json + WORKSPACES_DIR; registrér member 'mikkel'."""
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    ws_root = tmp_path / "workspaces"
    monkeypatch.setattr("core.identity.workspace_bootstrap.WORKSPACES_DIR", str(ws_root))
    from core.identity.users import add_user
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")
    return ws_root


def test_bootstrap_skips_reseed_over_enc(_member_env) -> None:
    """En krypteret MEMORY.md.enc må IKKE få en plaintext-stub oven på (§16)."""
    from core.identity.workspace_bootstrap import bootstrap_user_workspace
    ws = _member_env / "mikkel"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "MEMORY.md.enc").write_bytes(b"ciphertext")
    (ws / "USER.md.enc").write_bytes(b"ciphertext")

    bootstrap_user_workspace("mikkel", display_name="Mikkel")

    # Ingen plaintext-stub gen-sået oven på de krypterede filer
    assert not (ws / "MEMORY.md").exists()
    assert not (ws / "USER.md").exists()


def test_bootstrap_creates_stub_when_absent(_member_env, monkeypatch) -> None:
    """Uden eksisterende fil (plaintext eller .enc) skabes stub som normalt.

    2026-10-01: testen antog plaintext, men `JARVISX_ENCRYPT_WORKSPACES=1` er
    sat i driftsmiljøet, så member-filer skrives som `.enc`. Den var derfor grøn
    i CI (uden flaget) og rød i drift (med). Krypterings-tilstanden pinnes nu
    eksplicit; .enc-vejen — den der faktisk kører — har sin egen test nedenfor.
    """
    monkeypatch.delenv("JARVISX_ENCRYPT_WORKSPACES", raising=False)
    from core.identity.workspace_bootstrap import bootstrap_user_workspace
    bootstrap_user_workspace("mikkel", display_name="Mikkel")
    ws = _member_env / "mikkel"
    assert (ws / "MEMORY.md").exists()
    assert (ws / "USER.md").exists()


def test_bootstrap_skriver_krypteret_stub_naar_flaget_er_til(_member_env, monkeypatch) -> None:
    """Med ENCRYPT_ON_WRITE til skal stubbene opstå som .enc, ikke plaintext.

    Det er den vej der kører i drift, og som den gamle test fejlede på uden at
    sige hvorfor: den ledte efter `MEMORY.md` mens filen lå som `MEMORY.md.enc`.
    """
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    from core.identity.workspace_bootstrap import bootstrap_user_workspace
    bootstrap_user_workspace("mikkel", display_name="Mikkel")
    ws = _member_env / "mikkel"
    assert (ws / "MEMORY.md.enc").exists()
    assert (ws / "USER.md.enc").exists()
    assert not (ws / "MEMORY.md").exists()
