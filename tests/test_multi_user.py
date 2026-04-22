"""Multi-user system tests — users registry + workspace context + isolation.

Kritiske tests:
- users.py: load/save/lookup round-trip + validation
- workspace_context: ContextVar inheritance og override
- workspace_bootstrap: bootstrap_user_workspace creates empty MEMORY/USER
- Cross-user isolation: Bjørn og Michelle deler IKKE MEMORY.md
- Unknown discord_id routing
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_user_registry_roundtrip(isolated_runtime):
    """Add user → save → reload → lookup round-trip works."""
    from core.identity.users import (
        add_user, find_user_by_discord_id, load_users, remove_user,
    )

    # Seed owner
    owner = add_user(
        discord_id="1111", name="Bjørn", role="owner", workspace="default",
    )
    assert owner is not None
    assert owner.discord_id == "1111"
    assert owner.role == "owner"

    # Seed member
    member = add_user(
        discord_id="2222", name="Michelle", role="member", workspace="michelle",
    )
    assert member is not None
    assert member.role == "member"

    # Lookups
    found = find_user_by_discord_id("1111")
    assert found is not None and found.name == "Bjørn"
    found = find_user_by_discord_id("2222")
    assert found is not None and found.workspace == "michelle"
    assert find_user_by_discord_id("9999") is None

    # All users
    users = load_users()
    assert len(users) == 2

    # Remove
    assert remove_user(discord_id="2222") is True
    assert find_user_by_discord_id("2222") is None
    assert len(load_users()) == 1


def test_user_registry_rejects_duplicates(isolated_runtime):
    """Can't add duplicate discord_id or duplicate workspace."""
    from core.identity.users import add_user

    first = add_user(discord_id="1111", name="A", workspace="ws_a")
    assert first is not None

    # Duplicate discord_id
    dup = add_user(discord_id="1111", name="B", workspace="ws_b")
    assert dup is None

    # Duplicate workspace
    dup2 = add_user(discord_id="2222", name="C", workspace="ws_a")
    assert dup2 is None


def test_workspace_context_default_is_default(isolated_runtime):
    """Without binding, current_workspace_name returns 'default'."""
    from core.identity.workspace_context import (
        current_workspace_name, current_user_id,
    )
    assert current_workspace_name() == "default"
    assert current_user_id() == ""


def test_workspace_context_binds_and_resets(isolated_runtime):
    """user_context contextmanager binds and then resets cleanly."""
    from core.identity.workspace_context import (
        current_workspace_name, current_user_id, user_context,
    )

    with user_context(workspace_override="michelle", user_display_name_override="Michelle"):
        assert current_workspace_name() == "michelle"

    # After exit: back to default
    assert current_workspace_name() == "default"


def test_workspace_context_looks_up_user_by_discord_id(isolated_runtime):
    """When discord_id is known, context picks up the user's workspace."""
    from core.identity.users import add_user
    from core.identity.workspace_context import (
        current_workspace_name, current_user_id, user_context,
    )

    add_user(discord_id="42", name="TestUser", workspace="test_ws", role="member")

    with user_context(discord_id="42"):
        assert current_workspace_name() == "test_ws"
        assert current_user_id() == "42"


def test_workspace_context_unknown_discord_id_falls_to_public(isolated_runtime):
    """Unknown discord_id routes to 'public' workspace (shared)."""
    from core.identity.workspace_context import current_workspace_name, user_context

    with user_context(discord_id="99999", user_display_name_override="stranger"):
        assert current_workspace_name() == "public"


def test_ensure_default_workspace_honors_context(isolated_runtime):
    """ensure_default_workspace() returns context-bound workspace, not 'default'."""
    from core.identity.workspace_bootstrap import ensure_default_workspace
    from core.identity.workspace_context import user_context

    # Without context: default
    ws = ensure_default_workspace()
    assert ws.name == "default"

    # With context: override
    with user_context(workspace_override="michelle_ws"):
        ws = ensure_default_workspace()
        assert ws.name == "michelle_ws"

    # After exit: back to default
    ws = ensure_default_workspace()
    assert ws.name == "default"


def test_bootstrap_user_workspace_creates_empty_user_and_memory(isolated_runtime):
    """bootstrap_user_workspace creates MEMORY.md and USER.md as empty stubs."""
    from core.identity.workspace_bootstrap import bootstrap_user_workspace

    result = bootstrap_user_workspace("new_user_ws", display_name="NewUser")
    ws_dir = result.workspace_dir
    assert ws_dir.exists()

    # USER.md is a stub mentioning "don't know yet"
    user_md = ws_dir / "USER.md"
    assert user_md.exists()
    content = user_md.read_text(encoding="utf-8")
    assert "NewUser" in content
    assert "endnu ikke" in content.lower() or "don't know" in content.lower()

    # MEMORY.md is an empty stub
    memory_md = ws_dir / "MEMORY.md"
    assert memory_md.exists()
    mem_content = memory_md.read_text(encoding="utf-8")
    assert "Ingen erindringer" in mem_content

    # Shared identity files are copied
    assert (ws_dir / "SOUL.md").exists()
    assert (ws_dir / "IDENTITY.md").exists()
    assert (ws_dir / "STANDING_ORDERS.md").exists()


def test_cross_user_memory_isolation(isolated_runtime):
    """Bjørn's MEMORY.md is NOT visible in Michelle's workspace context."""
    from core.identity.users import add_user
    from core.identity.workspace_bootstrap import (
        bootstrap_user_workspace, workspace_memory_paths,
    )
    from core.identity.workspace_context import user_context

    # Two users
    add_user(discord_id="1111", name="Bjørn", role="owner", workspace="default")
    add_user(discord_id="2222", name="Michelle", role="member", workspace="michelle")
    bootstrap_user_workspace("default", display_name="Bjørn")
    bootstrap_user_workspace("michelle", display_name="Michelle")

    # Write to Bjørns MEMORY.md under Bjørn's context
    with user_context(discord_id="1111"):
        paths = workspace_memory_paths()
        paths["curated_memory"].write_text("# Bjørns private memory\nSecret stuff.\n", encoding="utf-8")

    # Under Michelle's context: different file
    with user_context(discord_id="2222"):
        paths = workspace_memory_paths()
        michelle_memory_content = paths["curated_memory"].read_text(encoding="utf-8")
        assert "Secret stuff" not in michelle_memory_content
        assert "Ingen erindringer" in michelle_memory_content

    # And verify paths are different
    with user_context(discord_id="1111"):
        bjorn_path = workspace_memory_paths()["curated_memory"]
    with user_context(discord_id="2222"):
        michelle_path = workspace_memory_paths()["curated_memory"]
    assert bjorn_path != michelle_path
    assert bjorn_path.parent.name == "default"
    assert michelle_path.parent.name == "michelle"


def test_user_attribution_migrations_idempotent(isolated_runtime):
    """Running migrations multiple times is safe."""
    from core.identity.user_attribution_migrations import (
        run_user_attribution_migrations, list_user_attribution_schema,
    )

    # First run
    r1 = run_user_attribution_migrations()
    first_total = len(r1["added"]) + len(r1["already_present"])

    # Second run — nothing new added
    r2 = run_user_attribution_migrations()
    assert len(r2["added"]) == 0

    # Schema reflects the columns
    schema = list_user_attribution_schema()
    # Every entry should be either 'present' or 'table_missing'
    for entry in schema:
        assert entry["status"] in ("present", "table_missing"), entry


def test_get_owner_returns_single_owner(isolated_runtime):
    """get_owner returns the owner user, None if no owner exists."""
    from core.identity.users import add_user, get_owner

    assert get_owner() is None

    add_user(discord_id="1111", name="Owner", role="owner", workspace="default")
    add_user(discord_id="2222", name="Member", role="member", workspace="other")

    owner = get_owner()
    assert owner is not None
    assert owner.role == "owner"
    assert owner.name == "Owner"


def test_is_known_discord_id(isolated_runtime):
    from core.identity.users import add_user, is_known_discord_id

    assert is_known_discord_id("1111") is False
    add_user(discord_id="1111", name="X", workspace="ws_x")
    assert is_known_discord_id("1111") is True
    assert is_known_discord_id("9999") is False


def test_workspace_context_snapshot(isolated_runtime):
    """current_context_snapshot returns full state dict."""
    from core.identity.workspace_context import current_context_snapshot, user_context

    snap = current_context_snapshot()
    assert snap["workspace"] == "default"
    assert snap["user_id"] == ""

    with user_context(workspace_override="x", user_display_name_override="Xenia"):
        snap = current_context_snapshot()
        assert snap["workspace"] == "x"
        assert snap["user_display_name"] == "Xenia"
