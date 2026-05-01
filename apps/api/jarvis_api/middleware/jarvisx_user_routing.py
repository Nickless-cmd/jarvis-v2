"""JarvisX user-routing + bearer-token auth middleware.

The Electron desktop app injects identity on every request. v1 of this
middleware trusted X-JarvisX-User as plaintext identity — fine for
solo localhost use but a forge-anywhere hole the moment the API listens
on anything but 127.0.0.1.

v2 (this version) prefers a signed bearer token:

    Authorization: Bearer <jwt>      ← signed identity (trusted)
    X-JarvisX-User: <discord_id>     ← legacy plaintext (untrusted)
    X-JarvisX-User-Name: …           ← informational only
    X-JarvisX-Client:  …             ← informational only
    X-JarvisX-Project: …             ← workspace anchor (no identity claim)

Resolution order:
  1. If `Authorization: Bearer …` is present and verifies → use the
     token's claims as canonical identity. Header X-JarvisX-User is
     ignored (a forged value can't bypass a verified one).
  2. If no token AND auth_required() → reject with 401.
  3. If no token AND auth_required() is false → fall back to the legacy
     X-JarvisX-User header (dev mode / single-user localhost). Logged
     so the operator notices when their box is running unauthenticated.

Failure modes:
  • Token expired/forged AND auth required → 401, no fallback. The
    client must reissue.
  • Unknown user_id (token or header) → bind to "public" workspace.
    This avoids leaking Bjørn's workspace to anyone who happens to
    know his discord_id.
  • Lookup raises → log and proceed with default context. We never
    let a middleware error break the request — the worst case should
    be "as if no identity was supplied".
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

USER_HEADER = "x-jarvisx-user"
USER_NAME_HEADER = "x-jarvisx-user-name"
CLIENT_HEADER = "x-jarvisx-client"
PROJECT_HEADER = "x-jarvisx-project"
AUTH_HEADER = "authorization"

# Endpoints that must remain unauthenticated even when auth is required —
# otherwise the client can't bootstrap or recover from a stale token.
# Token issuance itself IS protected (owner-only), via _require_owner()
# inside the route handler.
_PUBLIC_PATHS = (
    "/health",
    "/api/auth/whoami-token",  # let clients self-check token validity
    "/docs",
    "/openapi.json",
    "/redoc",
)


def _is_public_path(path: str) -> bool:
    for p in _PUBLIC_PATHS:
        if path == p or path.startswith(p + "/"):
            return True
    return False


async def jarvisx_user_routing_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    project_root = (request.headers.get(PROJECT_HEADER) or "").strip()
    raw_auth = request.headers.get(AUTH_HEADER) or ""
    legacy_user_id = (request.headers.get(USER_HEADER) or "").strip()

    # ── Step 1: try to verify a bearer token (canonical identity) ─
    token_claims: dict | None = None
    token_error: str | None = None
    if raw_auth.lower().startswith("bearer "):
        try:
            from core.runtime.jarvisx_auth import verify_token
            token_claims = verify_token(raw_auth)
        except Exception as exc:
            token_error = str(exc)
            token_claims = None

    # ── Step 2: enforce auth_required() globally ──────────────────
    # If we require auth and the request didn't bring a valid token,
    # block it before any context binding happens.
    if not token_claims and not _is_public_path(request.url.path):
        try:
            from core.runtime.jarvisx_auth import auth_required
            require = auth_required()
        except Exception:
            require = False
        if require:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "authentication required",
                    "error": token_error or "missing or invalid bearer token",
                },
            )

    # ── Step 3: resolve effective identity ────────────────────────
    if token_claims:
        user_id = str(token_claims.get("sub") or "").strip()
    else:
        user_id = legacy_user_id

    if not user_id and not project_root:
        # No identity at all + no project anchor → default context, fast path.
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
