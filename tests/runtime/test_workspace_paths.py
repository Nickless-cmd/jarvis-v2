"""Tests for workspace_paths helper — see plan task 1."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.runtime.workspace_paths import (
    NoUserContextError,
    shared_dir,
    workspace_dir,
    _user_id_to_workspace_name,
)


def test_shared_dir_returns_default_during_transition(monkeypatch, tmp_path):
    """During migration, shared_dir() returns workspaces/default for
    backwards compat. Switched to shared/ in Task 5."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    expected = tmp_path / "workspaces" / "default"
    assert shared_dir() == expected


def test_workspace_dir_for_known_owner(monkeypatch, tmp_path, users_json):
    """Bjørn's discord_id resolves to workspaces/default during
    transition (renamed to bjorn in Task 5)."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    # Bjørn's discord_id from users.json
    result = workspace_dir(user_id="1246415163603816499")
    assert result == tmp_path / "workspaces" / "default"


def test_workspace_dir_for_member_user(monkeypatch, tmp_path, users_json):
    """Member user_id resolves to their named workspace dir."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    # Mikkel's discord_id from users.json
    result = workspace_dir(user_id="238975101381378048")
    assert result == tmp_path / "workspaces" / "mikkel"


def test_workspace_dir_raises_without_context(monkeypatch, tmp_path):
    """No user_id and no context → loud error, never silent default."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    with pytest.raises(NoUserContextError):
        workspace_dir()  # no user_id arg, no context set


def test_workspace_dir_uses_current_user_id_when_unset(monkeypatch, tmp_path, users_json):
    """workspace_dir() reads current_user_id() from workspace_context."""
    from core.identity.workspace_context import set_context, reset_context
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    token = set_context(workspace_name="mikkel", user_id="238975101381378048")
    try:
        result = workspace_dir()
        assert result == tmp_path / "workspaces" / "mikkel"
    finally:
        reset_context(token)


def test_unknown_user_id_raises(monkeypatch, tmp_path, users_json):
    """Unknown discord_id → NoUserContextError, never falls back to default."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    with pytest.raises(NoUserContextError):
        workspace_dir(user_id="not-a-real-discord-id-9999")


@pytest.fixture
def users_json(tmp_path, monkeypatch):
    """Provide a users.json under test HOME so find_user_by_discord_id resolves."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "users.json").write_text("""
{
  "users": [
    {"discord_id": "1246415163603816499", "name": "Bjørn", "role": "owner", "workspace": "default", "created_at": "2026-04-22T00:00:00Z"},
    {"discord_id": "238975101381378048", "name": "Mikkel", "role": "member", "workspace": "mikkel", "created_at": "2026-04-30T00:00:00Z"}
  ]
}
""")
    # users.py reads CONFIG_DIR which is derived from Path.home() at import time.
    # Patch both HOME and CONFIG_DIR so find_user_by_discord_id resolves correctly.
    monkeypatch.setenv("HOME", str(tmp_path))
    import core.runtime.config as _cfg
    monkeypatch.setattr(_cfg, "CONFIG_DIR", config_dir)
    yield
