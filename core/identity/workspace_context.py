"""Workspace Context — thread-local/async-safe current-user binding.

ContextVar-baseret resolver der lader discord_gateway (eller andre
entry-points) sætte "current workspace" for en request, så nedstrøms
services som ensure_default_workspace() og workspace_memory_paths()
automatisk bruger den rigtige bruger-workspace UDEN at require alle
66 call-sites bliver ændret.

Design:
- ContextVar er thread-safe og asyncio-safe
- Default er "bjorn" (omdøbt fra "default" i Task 5)
- discord_gateway sætter binding før start_autonomous_run og rydder efter
- Explicit bypass: pass name="bjorn" eller navngiv eksplicit

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
    role: str = ""  # bearer-token role: owner|member|guest, "" = unbound (legacy)
    channel: str = ""  # transport channel: jarvisx-electron|webchat|discord|telegram|...
    session_id: str = ""  # aktuel session — bruges af effective_role til override-elevering


# Default: workspace="bjorn" (renamed from "default" in Task 5), user_id="" (owner implicit)
_DEFAULT_STATE = _ContextState(
    workspace_name="bjorn",
    user_id="",
    user_display_name="",
    role="",
    channel="",
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
    role: str = "",
    channel: str = "",
    session_id: str = "",
) -> contextvars.Token:
    """Set workspace context explicitly. Returns Token for reset.

    Caller is responsible for resetting via reset_context(token).
    Prefer the user_context() contextmanager for scoped blocks.
    """
    state = _ContextState(
        workspace_name=str(workspace_name or "bjorn").strip() or "bjorn",
        user_id=str(user_id or "").strip(),
        user_display_name=str(user_display_name or "").strip(),
        role=str(role or "").strip().lower(),
        channel=str(channel or "").strip().lower(),
        session_id=str(session_id or "").strip(),
    )
    return _current_state.set(state)


def current_session_id() -> str:
    """Aktuel session-id ("" hvis ikke sat)."""
    return _current_state.get().session_id


def set_session_id(session_id: str) -> contextvars.Token:
    """Opdatér KUN session_id på den nuværende kontekst (bevar role/user/workspace).

    Bruges inde i run-generatoren (streaming-kontekst), hvor role allerede er sat
    af middleware/gateway men session_id mangler — så effective_role kan slå
    override op. Returnerer Token (caller bør reset, men i streaming-gen er det
    ofte ok at lade den følge request-konteksten)."""
    cur = _current_state.get()
    new = _ContextState(
        workspace_name=cur.workspace_name,
        user_id=cur.user_id,
        user_display_name=cur.user_display_name,
        role=cur.role,
        channel=cur.channel,
        session_id=str(session_id or "").strip(),
    )
    return _current_state.set(new)


def effective_role() -> str:
    """Rollen efter TOTP-override-elevering (§6.0).

    Returnerer 'owner' hvis sessionen har en AKTIV TOTP-override — så Bjørn
    får fuld owner tool-adgang fra en fremmed session efter `!override`. Hver
    elevering FORNYER samtidig override-vinduet til 5 min (aktivitet = fornyelse,
    spec §9). Owner-sessioner returnerer 'owner' uændret (ingen override-tjek).
    """
    base = current_role()
    if base == "owner":
        return base
    try:
        from core.services.override_store import is_active, touch
        sid = current_session_id()
        if sid and is_active(sid):
            touch(sid)  # 5-min rullende fornyelse
            return "owner"
    except Exception:
        pass
    return base


def is_override_active() -> bool:
    """True hvis sessionen er TOTP-override-elevet (IKKE en native owner-session).

    Native owner (base role = owner) er ikke en override. Kun en non-owner session
    der er blevet elevet via `!override` + TOTP tæller. Bruges til at håndhæve §6.5:
    override giver KONTROL (action-tools), men må aldrig løfte privatlivs-scopingen
    på data-læsninger — ellers er bagdøren en data-bagdør, ikke en kontrol-bagdør.
    """
    base = current_role()
    if base == "owner":
        return False
    try:
        from core.services.override_store import is_active
        sid = current_session_id()
        return bool(sid and is_active(sid))
    except Exception:
        return False


def privacy_scoped_user_id() -> str | None:
    """user_id til PRIVATLIVS-scopede data-læsninger (session-søgning, chat-historik).

    Returnerer None hvis sessionen er override-elevet → kalderen SKAL returnere INTET
    (§6.5: kontrol ja, privat-data nej — Bjørn må ikke læse en andens private session
    via kill-switch-bagdøren). Ellers den faktiske current_user_id().
    """
    if is_override_active():
        return None
    return current_user_id()


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

    workspace_name = "bjorn"
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
    workspace_name: str = "bjorn",
    user_id: str = "",
    user_display_name: str = "",
) -> contextvars.Token | None:
    """Bind context only if still on default — useful for late-binding
    without overwriting explicit scopes. Returns Token if binding happened
    (caller must reset), else None."""
    current = _current_state.get()
    if current.workspace_name != "bjorn" or current.user_id:
        return None
    return set_context(
        workspace_name=workspace_name,
        user_id=user_id,
        user_display_name=user_display_name,
    )


def current_role() -> str:
    """Return current bearer-token role ("owner"|"member"|"guest"|"").
    Empty string when no token-backed identity is bound (legacy / single-user dev).
    """
    return _current_state.get().role


def current_channel() -> str:
    """Return the transport channel the current request came in on.

    "jarvisx-electron" | "webchat" | "discord" | "telegram" | "" (unbound).
    Set by the auth middleware from the X-JarvisX-Client header.
    """
    return _current_state.get().channel
