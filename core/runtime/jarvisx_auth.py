"""JarvisX bearer-token authentication.

Threat model: today the runtime trusts X-JarvisX-User as identity.
Anyone who can hit the API can claim to be Bjørn by setting that
header. Fine on localhost-only deployments, catastrophic the moment
a port opens to the LAN or the internet.

This module introduces signed bearer tokens so the API can verify
*who* is calling, not just what they claim. Owner mints tokens for
each device/user via /api/auth/issue; tokens carry user_id + role +
expiry; middleware verifies the HMAC signature on every request.

Design choices:

  - JWT format (HS256). Standard, well-tested libs, easy to debug.
    Not because we need to interop — we don't — but because pyjwt
    is already a runtime dep and rolling our own MAC framing is the
    classic "just one bug away from forgeable tokens" hole.

  - Secret stored in ~/.jarvis-v2/config/runtime.json under
    "jarvisx_auth_secret". Auto-generated on first use if missing
    (32 random bytes, hex-encoded). Rotating it invalidates every
    issued token, by design — that's the "panic button" if a token
    leaks.

  - Token claims: sub (user_id), role, iat, exp, iss="jarvisx".
    No nbf — clock skew between machines is a real problem on
    LAN-deployed Jarvis instances and not worth the complexity.

  - No revocation list yet. If a token is compromised before its
    exp, the only fix is rotating the secret (kills *all* tokens).
    Acceptable for v1 with a 30-day default TTL; revocation list is
    a future upgrade if the user base ever grows past family-and-
    friends scale.
"""
from __future__ import annotations

import json
import logging
import os
import secrets as _secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt  # PyJWT

from core.runtime.config import CONFIG_DIR

logger = logging.getLogger(__name__)

_SETTINGS_FILE = Path(CONFIG_DIR) / "runtime.json"
_SECRET_KEY = "jarvisx_auth_secret"  # pragma: allowlist secret
_ALGO = "HS256"
_ISSUER = "jarvisx"
_DEFAULT_TTL_DAYS = 30
_MIN_SECRET_BYTES = 32


class AuthError(RuntimeError):
    """Raised when a token is missing, malformed, expired, or forged."""


def _load_settings() -> dict[str, Any]:
    if not _SETTINGS_FILE.is_file():
        return {}
    try:
        return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_settings(data: dict[str, Any]) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _SETTINGS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(_SETTINGS_FILE)


def _read_secret() -> str:
    """Read the auth secret, generating one on first use.

    Generation only happens once per machine; subsequent reads return
    the same value. We mutate runtime.json directly instead of asking
    the user to seed it because forcing manual setup for a security
    primitive is the fastest way to get people to skip it.
    """
    env = os.environ.get("JARVISX_AUTH_SECRET")
    if env and len(env) >= _MIN_SECRET_BYTES:
        return env
    data = _load_settings()
    secret = str(data.get(_SECRET_KEY) or "")
    if secret and len(secret) >= _MIN_SECRET_BYTES:
        return secret
    # First-run generation — 32 random bytes, hex-encoded (64 chars)
    secret = _secrets.token_hex(32)
    data[_SECRET_KEY] = secret
    try:
        _save_settings(data)
    except Exception as exc:
        # Non-fatal: we'll just regenerate next call. Better than crashing
        # the whole API boot. Logged loudly so it's noticed.
        logger.error(
            "jarvisx_auth: failed to persist generated secret to %s: %s. "
            "Tokens issued in this process will not survive restart.",
            _SETTINGS_FILE, exc,
        )
    else:
        logger.warning(
            "jarvisx_auth: generated new auth secret in %s. "
            "Back this up — rotating it invalidates every issued token.",
            _SETTINGS_FILE,
        )
    return secret


def issue_token(
    *,
    user_id: str,
    role: str = "member",
    ttl_days: int = _DEFAULT_TTL_DAYS,
    extra_claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Mint a signed bearer token for a user.

    Returns dict with the token string + metadata so callers can
    show the user when the token expires and what role it grants.
    """
    user_id = (user_id or "").strip()
    if not user_id:
        raise ValueError("user_id required")
    role = (role or "member").strip().lower()
    if role not in {"owner", "member", "guest"}:
        raise ValueError(f"invalid role: {role!r}")
    ttl_days = max(1, min(int(ttl_days), 365))  # clamp [1, 365]

    now = datetime.now(UTC)
    exp = now + timedelta(days=ttl_days)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "iss": _ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if extra_claims:
        # Merge but don't let extras overwrite reserved claims
        for k, v in extra_claims.items():
            if k not in payload:
                payload[k] = v

    token = jwt.encode(payload, _read_secret(), algorithm=_ALGO)
    return {
        "token": token,
        "user_id": user_id,
        "role": role,
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": exp.isoformat().replace("+00:00", "Z"),
        "ttl_days": ttl_days,
    }


def verify_token(token: str) -> dict[str, Any]:
    """Verify signature + expiry, return the parsed claims.

    Raises AuthError on any failure. Caller should treat any exception
    as "no identity" and fall back to whatever degraded mode applies.
    """
    if not token:
        raise AuthError("missing token")
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    try:
        claims = jwt.decode(
            token,
            _read_secret(),
            algorithms=[_ALGO],
            issuer=_ISSUER,
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("token expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise AuthError("token issuer mismatch") from exc
    except jwt.InvalidTokenError as exc:
        # Catches signature mismatch, malformed payload, missing claims
        raise AuthError(f"invalid token: {exc}") from exc

    # Defensive — make sure required fields are usable
    if not claims.get("sub"):
        raise AuthError("token missing subject")
    role = str(claims.get("role") or "member").lower()
    if role not in {"owner", "member", "guest"}:
        raise AuthError(f"invalid role in token: {role!r}")
    claims["role"] = role
    return claims


def auth_required() -> bool:
    """Should the API reject requests without a valid bearer token?

    Default: false — single-user localhost dev mode is the common case
    and forcing tokens there is friction. Set JARVISX_AUTH_REQUIRED=1
    in the environment (or in runtime.json under "jarvisx_auth_required")
    to flip on full enforcement. Recommended whenever the API is bound
    to anything other than 127.0.0.1.
    """
    env = os.environ.get("JARVISX_AUTH_REQUIRED")
    if env is not None:
        return env.strip() not in {"", "0", "false", "False", "no"}
    data = _load_settings()
    flag = data.get("jarvisx_auth_required")
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, str):
        return flag.strip().lower() in {"1", "true", "yes"}
    return False
