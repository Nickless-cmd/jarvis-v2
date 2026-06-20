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


def team_dir(team_id: str) -> Path:
    """Delt team-workspace som git-repo (Teams-feature, spec 2026-06-20).

    Tredje workspace-art ved siden af shared_dir()/workspace_dir(). Ligger i
    <home>/teams/<team_id>/workspace/; repoet git-init'es på <home>/teams/<team_id>/
    (repo-rod OVER workspace, så .git ikke forurener arbejdsfilerne). Gatet på
    medlemskab i kald-laget — INGEN per-bruger-kryptering (delt repo). Opretter +
    git-init'er ved første kald; idempotent.
    """
    import subprocess

    base = _jarvis_home() / "teams" / team_id
    ws = base / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    if not (base / ".git").exists():
        try:
            subprocess.run(["git", "init", "-q"], cwd=str(base), check=False)
            subprocess.run(["git", "config", "user.email", "teams@jarvis"], cwd=str(base), check=False)
            subprocess.run(["git", "config", "user.name", "Jarvis Teams"], cwd=str(base), check=False)
        except Exception:
            pass  # git mangler → workspace virker stadig, bare uden rollback
    return ws


def _user_id_to_workspace_name(user_id: str) -> str:
    """Resolve user_id → workspace folder name.

    Hybrid (users.json→SQLite-cutover): legacy users.json prøves FØRST (discord-id-
    brugere opfører sig 100% uændret — nul regression), SQLite users-tabellen som
    fallback (nyregistrerede brugere med user_id=UUID). Bevarer den LOUD
    NoUserContextError hvis ingen af dem kender brugeren (aldrig stille default →
    ingen data-lækage).
    """
    uid = str(user_id).strip()
    # 1) Legacy users.json (discord-id). Uændret adfærd for kendte brugere.
    try:
        from core.identity.users import find_user_by_discord_id
        user = find_user_by_discord_id(uid)
        if user is not None:
            return user.workspace
    except Exception:
        pass
    # 2) SQLite users-tabel (user_id = UUID). Nyregistrerede selvbetjenings-brugere.
    try:
        from core.runtime.db_users import get_user_row
        row = get_user_row(uid)
        if row and not row.get("deleted_at"):
            ws = str(row.get("workspace") or "").strip()
            if ws:
                return ws
    except Exception:
        pass
    raise NoUserContextError(
        f"user_id={user_id!r} ikke fundet i users.json eller SQLite-tabellen — "
        "nægter at defaulte til 'default'-workspace (ville lække owner-data). "
        "Registrér brugeren (scripts/users_cli.py add eller register_user), eller "
        "pass et eksplicit user_id."
    )
