"""Workspace path resolver — single source of truth for filesystem layout.

Replaces ~75 hardcoded `workspaces/default/` references across services.
Routes per-user requests to their workspace dir; routes Jarvis-state
requests to the shared dir.

Task 5 switched shared_dir() to `shared/` and renamed default → bjorn.

See: docs/superpowers/specs/2026-05-28-multi-user-workspace-isolation-design.md
"""
from __future__ import annotations

import os
from pathlib import Path


class NoUserContextError(RuntimeError):
    """Raised when workspace_dir() is called without a resolvable user_id.

    This is intentionally loud — we prefer a visible crash over a silent
    fallback to default/ that would leak the owner's data into a member's
    session.
    """


def _jarvis_home() -> Path:
    """JARVIS_HOME resolved at call time (so tests can override via env)."""
    return Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))


def shared_dir() -> Path:
    """Jarvis' own state. All users see the same instance.

    Contains: SOUL.md, IDENTITY.md, MANIFEST.md, INNER_VOICE.md,
    CHRONICLE.md, dreams/, creative_impulse/, shadow_scan/, etc.
    """
    return _jarvis_home() / "shared"


def workspace_dir(user_id: str | None = None) -> Path:
    """Per-relation workspace. Defaults to current_user_id() from context.

    Contains: MEMORY.md, USER.md (per-relation state).

    Args:
        user_id: explicit discord_id. If None, reads from workspace_context.
                 If unresolvable → NoUserContextError (never silent default).

    Raises:
        NoUserContextError: when user_id is empty and no context is set,
                            or when user_id is not in users.json.
    """
    if not user_id:
        from core.identity.workspace_context import current_user_id
        user_id = current_user_id()
    if not user_id:
        raise NoUserContextError(
            "workspace_dir() called without user_id arg and no current_user_id() "
            "in context. Caller must either pass user_id= explicitly or be inside "
            "a user_context() / set_context() block."
        )
    workspace_name = _user_id_to_workspace_name(user_id)
    return _jarvis_home() / "workspaces" / workspace_name


def _user_id_to_workspace_name(user_id: str) -> str:
    """Resolve discord_id → workspace folder name via users.json.

    Raises NoUserContextError if user_id is not registered.
    """
    from core.identity.users import find_user_by_discord_id
    user = find_user_by_discord_id(str(user_id).strip())
    if user is None:
        raise NoUserContextError(
            f"user_id={user_id!r} not found in users.json — refusing to default "
            "to 'default' workspace (would leak owner data). Register the user "
            "with scripts/users_cli.py add, or pass an explicit user_id."
        )
    return user.workspace
