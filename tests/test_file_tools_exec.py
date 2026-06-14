"""Tests for de udskilte fil-tool executors + encryption-aware I/O-helpers."""
from __future__ import annotations

import os

import pytest


def test_ws_helpers_plaintext_roundtrip(tmp_path) -> None:
    from core.tools.file_tools_exec import _ws_read_text, _ws_write_text, _ws_path_exists
    p = tmp_path / "note.md"
    _ws_write_text(p, "hej verden")
    assert _ws_path_exists(p) is True
    assert _ws_read_text(p) == "hej verden"
    assert _ws_read_text(tmp_path / "nope.md") is None


def test_exec_read_file_plaintext(tmp_path) -> None:
    from core.tools.file_tools_exec import _exec_read_file
    p = tmp_path / "f.txt"
    p.write_text("indhold", encoding="utf-8")
    res = _exec_read_file({"path": str(p)})
    assert res["status"] == "ok"
    assert res["text"] == "indhold"


def test_exec_read_file_missing(tmp_path) -> None:
    from core.tools.file_tools_exec import _exec_read_file
    res = _exec_read_file({"path": str(tmp_path / "missing.txt")})
    assert res["status"] == "error"
    assert "not found" in res["error"].lower()


def test_ws_helpers_member_enc_roundtrip(isolated_runtime, tmp_path, monkeypatch) -> None:
    """Member .enc læses/skrives transparent via de udskilte helpers (§16)."""
    from core.identity.users import add_user
    from core.tools import file_tools_exec as fx
    import core.services.keyring_store as ks

    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    monkeypatch.setattr(ks, "_keyring", lambda: None)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")

    p = tmp_path / "workspaces" / "mikkel" / "MEMORY.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    fx._ws_write_text(p, "- mikkels note\n")
    assert (tmp_path / "workspaces" / "mikkel" / "MEMORY.md.enc").exists()
    assert not p.exists()
    assert fx._ws_path_exists(p) is True
    assert fx._ws_read_text(p) == "- mikkels note\n"


def test_exec_read_file_decrypts_member_enc(isolated_runtime, tmp_path, monkeypatch) -> None:
    """read_file-toolet dekrypterer en members .enc-fil efter flip (§16)."""
    from core.identity.users import add_user
    from core.tools import file_tools_exec as fx
    import core.services.keyring_store as ks

    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    monkeypatch.setattr(ks, "_keyring", lambda: None)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")

    p = tmp_path / "workspaces" / "mikkel" / "USER.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    fx._ws_write_text(p, "hemmelig profil")
    res = fx._exec_read_file({"path": str(p)})
    assert res["status"] == "ok"
    assert res["text"] == "hemmelig profil"
