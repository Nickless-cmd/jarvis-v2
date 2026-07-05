"""Shared owner-gate for /central/* routes.

Honors the validated bearer-token role FIRST (``current_role()``), then falls
back to a DB user lookup, then allows an unbound context (localhost / single-user
dev). This fixes the bug where a valid owner *token* was rejected with 403 because
the gate only did a DB lookup by user-id — and that id did not resolve to
role="owner" (Jarvis' diagnosis, 2026-07-05).

Security is preserved: the bearer-token role is set by the validated auth
middleware, so trusting ``current_role() == "owner"`` is at least as strong as the
old DB path, and no weaker for any real caller.
"""
from __future__ import annotations

from fastapi import HTTPException


def require_central_owner() -> None:
    """Raise 403 unless the caller is the owner. Self-safe on each probe."""
    # 1) Validated bearer-token role — authoritative (set by auth middleware).
    try:
        from core.identity.workspace_context import current_role
        if current_role() == "owner":
            return
    except Exception:
        pass
    # 2) Unbound context (no token — localhost / single-user dev) = owner.
    try:
        from core.identity.workspace_context import current_user_id
        uid = current_user_id() or None
    except Exception:
        uid = None
    if uid is None:
        return
    # 3) Fallback: DB user role.
    try:
        from core.identity.users import find_user_by_discord_id
        if getattr(find_user_by_discord_id(str(uid)), "role", "") == "owner":
            return
    except Exception:
        pass
    raise HTTPException(status_code=403, detail="Centralen er kun for owner")
