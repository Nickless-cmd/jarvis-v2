"""JarvisX bearer-token issuance + verification route group.

The middleware verifies tokens on every request; these endpoints let the
owner mint new tokens (e.g. for Mikkel's device), rotate refresh tokens,
and let clients self-check a stored token. Extracted from routes/jarvisx.py.

Behavior-preserving: pure code movement, no logic changes.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from apps.api.jarvis_api.routes.jarvisx_common import _require_owner

router = APIRouter(prefix="/api", tags=["jarvisx"])


# ── Authentication: bearer-token issuance + verification ──────────
# The middleware verifies tokens on every request; these endpoints let
# the owner mint new tokens (e.g. for Mikkel's device) and let clients
# self-check that a stored token is still valid.


class _IssueTokenPayload(BaseModel):
    user_id: str
    role: str = "member"
    ttl_days: int = 30


class _RefreshTokenPayload(BaseModel):
    refresh_token: str
    app_id: str = ""


@router.post("/auth/refresh")
def refresh_auth_token(payload: _RefreshTokenPayload) -> dict[str, Any]:
    """Veksl en refresh-token til et nyt access+refresh-par (§22.6). PUBLIC —
    bruges når access-tokenet er udløbet. Den gamle refresh-token roteres væk;
    401 hvis den er ugyldig/udløbet."""
    from core.runtime.refresh_tokens import rotate_refresh_token
    res = rotate_refresh_token(payload.refresh_token, app_id=payload.app_id)
    if not res.get("ok"):
        raise HTTPException(status_code=401, detail=res.get("reason", "invalid_refresh_token"))
    return res


@router.post("/auth/issue")
def issue_auth_token(payload: _IssueTokenPayload) -> dict[str, Any]:
    """Mint a signed bearer token for a user. Owner-only.

    Returns the token + metadata. The owner is expected to deliver the
    token to the recipient out-of-band (Discord DM, paper, etc.) — we
    don't transport it through any third-party channel.
    """
    _require_owner()
    from core.runtime.jarvisx_auth import issue_token
    try:
        out = issue_token(
            user_id=payload.user_id,
            role=payload.role,
            ttl_days=payload.ttl_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return out


@router.get("/auth/whoami-token")
def whoami_token(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Inspect the bearer token attached to this request.

    Public endpoint (in the middleware's auth-bypass list) so clients
    can verify a stored token without already being authenticated.
    Returns the claims if valid, or the error reason if not.
    """
    if not authorization:
        return {"valid": False, "error": "no Authorization header"}
    try:
        from core.runtime.jarvisx_auth import verify_token
        claims = verify_token(authorization)
    except Exception as exc:
        return {"valid": False, "error": str(exc)}
    return {
        "valid": True,
        "user_id": claims.get("sub"),
        "role": claims.get("role"),
        "issued_at": claims.get("iat"),
        "expires_at": claims.get("exp"),
        "issuer": claims.get("iss"),
    }
