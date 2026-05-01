"""JarvisX user-routing middleware.

The Electron desktop app (apps/jarvisx/) injects three headers on every
outbound request from the renderer + embedded iframe:

    X-JarvisX-User       — discord_id of the speaker (used to resolve workspace)
    X-JarvisX-User-Name  — url-encoded display name (informational only)
    X-JarvisX-Client     — client identifier (e.g. "jarvisx-electron/0.1.0-poc")

This middleware reads the user header, resolves the user via
find_user_by_discord_id, and binds the workspace ContextVars so all
downstream services (chat sessions, prompt assembly, memory paths,
heartbeat ticks initiated from the request) automatically use the right
workspace — exactly the same pattern discord_gateway uses on its side.

When the header is absent (e.g. webchat from a browser without JarvisX,
internal calls, MC polling) the request runs with the default context
unchanged — full backwards compatibility.

Failure modes:
  • Unknown discord_id → fall back to the "public" workspace, which is
    the same behaviour user_context() applies for unknown Discord users.
    This avoids leaking Bjørn's workspace to unauthenticated callers.
  • Lookup raises → log and proceed with default context. We never let a
    middleware error break a request.
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import Request, Response

logger = logging.getLogger(__name__)

USER_HEADER = "x-jarvisx-user"
USER_NAME_HEADER = "x-jarvisx-user-name"
CLIENT_HEADER = "x-jarvisx-client"
PROJECT_HEADER = "x-jarvisx-project"


async def jarvisx_user_routing_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    user_id = (request.headers.get(USER_HEADER) or "").strip()
    project_root = (request.headers.get(PROJECT_HEADER) or "").strip()
    if not user_id and not project_root:
        # No JarvisX headers at all → default context, fast path.
        return await call_next(request)

    # Resolve the workspace. We import lazily so this module is cheap to
    # import at app boot even if identity isn't fully wired yet.
    try:
        from core.identity.users import find_user_by_discord_id
        from core.identity.workspace_context import set_context, reset_context
        from core.identity.project_context import (
            set_project_root,
            reset_project_root,
        )
    except Exception as exc:
        logger.warning("jarvisx middleware: identity import failed: %s", exc)
        return await call_next(request)

    if user_id:
        try:
            user = find_user_by_discord_id(user_id)
        except Exception as exc:
            logger.warning("jarvisx middleware: user lookup failed for %s: %s", user_id, exc)
            user = None
    else:
        # Project-only request (no user header) — keep workspace default,
        # but still bind the project anchor below.
        user = None

    if user_id and user is None:
        # Unknown discord_id — same fallback as discord_gateway / user_context.
        # We bind to "public" workspace so memory writes can't accidentally
        # land in an owner's workspace via a forged header.
        workspace_name = "public"
        display = ""
        from urllib.parse import unquote
        raw_name = request.headers.get(USER_NAME_HEADER) or ""
        if raw_name:
            try:
                display = unquote(raw_name)[:120]
            except Exception:
                display = ""
        bound_user_id = user_id
    elif user is not None:
        workspace_name = user.workspace
        display = user.name
        bound_user_id = user.discord_id
    else:
        # No user header at all (project-only request) — keep defaults.
        workspace_name = ""
        display = ""
        bound_user_id = ""

    ws_token = None
    if workspace_name:
        try:
            ws_token = set_context(
                workspace_name=workspace_name,
                user_id=bound_user_id,
                user_display_name=display,
            )
        except Exception as exc:
            logger.warning("jarvisx middleware: set_context failed: %s", exc)
            return await call_next(request)

    proj_token = None
    if project_root:
        try:
            proj_token = set_project_root(project_root)
        except Exception as exc:
            logger.warning("jarvisx middleware: set_project_root failed: %s", exc)

    try:
        return await call_next(request)
    finally:
        if ws_token is not None:
            try:
                reset_context(ws_token)
            except Exception:
                pass
        if proj_token is not None:
            try:
                reset_project_root(proj_token)
            except Exception:
                pass
