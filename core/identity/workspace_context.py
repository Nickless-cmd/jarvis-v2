"""Workspace Context — thread-local/async-safe current-user binding.

ContextVar-baseret resolver der lader discord_gateway (eller andre
entry-points) sætte "current workspace" for en request, så nedstrøms
services som ensure_default_workspace() og workspace_memory_paths()
automatisk bruger den rigtige bruger-workspace UDEN at require alle
66 call-sites bliver ændret.

Design:
- ContextVar er thread-safe og asyncio-safe
- Default er "default" (bagudkompatibelt — eksisterende kode virker uændret)
- discord_gateway sætter binding før start_autonomous_run og rydder efter
- Explicit bypass: pass name="default" eller navngiv eksplicit

Flow:
    # In discord_gateway.on_message:
    with user_context(discord_id="123"):
        start_autonomous_run(...)  # nedstrøms services ser Michelles workspace

    # Inside any service:
    ws = ensure_default_workspace()  # returnerer Michelles workspace-dir
    uid = current_user_id()  # "123"
"""
from __future__ import annotations

import contextvars
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ContextState:
    workspace_name: str
    user_id: str  # discord_id or similar external identifier
    user_display_name: str


# Default: workspace="default", user_id="" (owner implicit, bagudkompatibelt)
_DEFAULT_STATE = _ContextState(
    workspace_name="default",
    user_id="",
    user_display_name="",
)

_current_state: contextvars.ContextVar[_ContextState] = contextvars.ContextVar(
    "jarvis_workspace_context",
    default=_DEFAULT_STATE,
)


def current_workspace_name() -> str:
    """Return current workspace name. Default 'default' if unset."""
    return _current_state.get().workspace_name


def current_user_id() -> str:
    """Return current user_id (discord_id). Empty string if none set."""
    return _current_state.get().user_id


def current_user_display_name() -> str:
    return _current_state.get().user_display_name


def current_context_snapshot() -> dict[str, str]:
    s = _current_state.get()
    return {
        "workspace": s.workspace_name,
        "user_id": s.user_id,
        "user_display_name": s.user_display_name,
    }


def set_context(
    *,
    workspace_name: str,
    user_id: str = "",
    user_display_name: str = "",
) -> contextvars.Token:
    """Set workspace context explicitly. Returns Token for reset.

    Caller is responsible for resetting via reset_context(token).
    Prefer the user_context() contextmanager for scoped blocks.
    """
    state = _ContextState(
        workspace_name=str(workspace_name or "default").strip() or "default",
        user_id=str(user_id or "").strip(),
        user_display_name=str(user_display_name or "").strip(),
    )
    return _current_state.set(state)


def reset_context(token: contextvars.Token) -> None:
    _current_state.reset(token)


@contextmanager
def user_context(
    *,
    discord_id: str = "",
    workspace_override: str = "",
    user_display_name_override: str = "",
) -> Iterator[_ContextState]:
    """Set workspace context for the duration of a block.

    If discord_id is provided, looks up user in users.json.
    If user unknown → falls back to 'public' workspace (shared/anonymous).
    If workspace_override is given, overrides lookup (use for explicit routes).
    """
    from core.identity.users import find_user_by_discord_id

    workspace_name = "default"
    user_id = ""
    display = ""

    if workspace_override:
        workspace_name = str(workspace_override).strip()
        if user_display_name_override:
            display = str(user_display_name_override).strip()
    elif discord_id:
        user = find_user_by_discord_id(discord_id)
        if user:
            workspace_name = user.workspace
            user_id = user.discord_id
            display = user.name
        else:
            # Unknown discord_id → public workspace (shared)
            workspace_name = "public"
            user_id = str(discord_id).strip()
            display = user_display_name_override or "unknown"
    elif user_display_name_override:
        display = str(user_display_name_override).strip()

    token = set_context(
        workspace_name=workspace_name,
        user_id=user_id,
        user_display_name=display,
    )
    try:
        yield _current_state.get()
    finally:
        reset_context(token)


def bind_context_if_unset(
    *,
    workspace_name: str = "default",
    user_id: str = "",
    user_display_name: str = "",
) -> contextvars.Token | None:
    """Bind context only if still on default — useful for late-binding
    without overwriting explicit scopes. Returns Token if binding happened
    (caller must reset), else None."""
    current = _current_state.get()
    if current.workspace_name != "default" or current.user_id:
        return None
    return set_context(
        workspace_name=workspace_name,
        user_id=user_id,
        user_display_name=user_display_name,
    )
