"""End-to-end test: simultaneous Bjørn + Mikkel sessions don't bleed.

Covers all the routing seams introduced in Tasks 1-6:
- workspace_dir() routes by current user context
- shared_dir() is invariant across users
- Missing context raises loudly
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

BJORN_ID = "1246415163603816499"
MIKKEL_ID = "238975101381378048"


@pytest.fixture
def e2e_env(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    cfg = tmp_path / "config"; cfg.mkdir(parents=True)
    (cfg / "users.json").write_text(json.dumps({
        "users": [
            {"discord_id": BJORN_ID, "name": "Bjørn", "role": "owner", "workspace": "bjorn", "created_at": "2026-01-01"},
            {"discord_id": MIKKEL_ID, "name": "Mikkel", "role": "member", "workspace": "mikkel", "created_at": "2026-01-01"},
        ]
    }))
    # Same pattern as Task 1 fixture
    import core.runtime.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg, raising=False)

    bjorn_ws = tmp_path / "workspaces" / "bjorn"
    mikkel_ws = tmp_path / "workspaces" / "mikkel"
    shared = tmp_path / "shared"
    for d in (bjorn_ws, mikkel_ws, shared):
        d.mkdir(parents=True)

    (bjorn_ws / "MEMORY.md").write_text("# Bjørn's memory\n\nworking on jarvis-v2.")
    (bjorn_ws / "USER.md").write_text("# Bjørn\nthe owner.")
    (mikkel_ws / "MEMORY.md").write_text("# Mikkel's memory\n\nshares a friendship with bjorn.")
    (mikkel_ws / "USER.md").write_text("# Mikkel\nbjorn's friend.")
    (shared / "SOUL.md").write_text("# Jarvis' soul\n\nI am Jarvis.")

    yield tmp_path


def test_memory_search_returns_only_current_user_workspace(e2e_env):
    """In Bjørn-context workspace_dir() resolves to bjorn/; Mikkel-context to mikkel/."""
    from core.identity.workspace_context import set_context, reset_context
    from core.runtime.workspace_paths import workspace_dir

    token = set_context(workspace_name="bjorn", user_id=BJORN_ID)
    try:
        wd = workspace_dir()
        assert wd == e2e_env / "workspaces" / "bjorn"
        assert (wd / "MEMORY.md").read_text().startswith("# Bjørn's memory")
    finally:
        reset_context(token)

    token = set_context(workspace_name="mikkel", user_id=MIKKEL_ID)
    try:
        wd = workspace_dir()
        assert wd == e2e_env / "workspaces" / "mikkel"
        assert (wd / "MEMORY.md").read_text().startswith("# Mikkel's memory")
    finally:
        reset_context(token)


def test_shared_dir_unchanged_across_users(e2e_env):
    """Both users see the same SOUL.md (same Jarvis)."""
    from core.identity.workspace_context import set_context, reset_context
    from core.runtime.workspace_paths import shared_dir

    soul_paths = []
    for uid, ws in [(BJORN_ID, "bjorn"), (MIKKEL_ID, "mikkel")]:
        token = set_context(workspace_name=ws, user_id=uid)
        try:
            soul_paths.append(shared_dir() / "SOUL.md")
        finally:
            reset_context(token)

    assert soul_paths[0] == soul_paths[1] == e2e_env / "shared" / "SOUL.md"
    assert soul_paths[0].read_text() == "# Jarvis' soul\n\nI am Jarvis."


def test_no_workspace_context_raises(e2e_env):
    """Without a user_context, workspace_dir() raises loudly."""
    from core.runtime.workspace_paths import workspace_dir, NoUserContextError
    # workspace_context default is "bjorn" workspace_name but empty user_id
    # → workspace_dir() should still raise because user_id is empty
    with pytest.raises(NoUserContextError):
        workspace_dir()
