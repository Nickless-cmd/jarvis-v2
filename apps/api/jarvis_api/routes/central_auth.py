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


def _unbound_owner_allowed() -> bool:
    """Må en token-løs (unbound) kontekst behandles som owner på privilege-eskalerende ruter?

    Default FALSE (fail-closed). Med ``--host 0.0.0.0`` + ``auth_required()``=false (dev-default)
    når en token-løs LAN-request `uid is None` — den må IKKE auto-autoriseres til at give Jarvis
    mere autonomi. Sæt runtime.json ``central_unbound_owner_ok=true`` (ren-localhost single-user)
    for at genåbne den bekvemme sti bevidst. Self-safe → False ved enhver fejl."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value("central_unbound_owner_ok", False)
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes"}
    except Exception:
        pass
    return False


def require_central_owner_strict() -> None:
    """Fail-closed owner-gate for privilege-ESKALERENDE ruter (autonomi-nøgle-godkendelse,
    enforcement-toggles). Kræver en POSITIV owner-identitet — bearer-rolle=owner ELLER en uid der
    DB-opslås til owner. Til forskel fra ``require_central_owner`` giver den IKKE owner blot fordi
    konteksten er unbound; den token-løse sti kræver et eksplicit dev-flag. Read-only observabilitet
    bruger stadig den lempelige gate; kun handlinger der udvider Jarvis' magt bruger denne."""
    # 1) Validated bearer-token role — authoritative.
    try:
        from core.identity.workspace_context import current_role
        if current_role() == "owner":
            return
    except Exception:
        pass
    # 2) Positive uid resolving to DB owner role.
    try:
        from core.identity.workspace_context import current_user_id
        uid = current_user_id() or None
    except Exception:
        uid = None
    if uid is not None:
        try:
            from core.identity.users import find_user_by_discord_id
            if getattr(find_user_by_discord_id(str(uid)), "role", "") == "owner":
                return
        except Exception:
            pass
    # 3) Unbound (token-løs) — kun hvis eksplicit dev-flag; ellers fail-closed.
    elif _unbound_owner_allowed():
        return
    raise HTTPException(status_code=403,
                        detail="Denne handling kræver bekræftet owner-identitet (token)")
