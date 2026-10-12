"""Canonical, fail-closed identity resolution for Routine entry points."""
from __future__ import annotations

from core.identity import user_db
from core.identity.user_db import AmbiguousRoutineIdentity
from core.services.routine_types import RoutinePrincipal


class UnresolvedRoutinePrincipal(RuntimeError):
    """No active canonical account owns the supplied identity token."""


def resolve_principal(raw_user_id: str, role_hint: str = "") -> RoutinePrincipal:
    """Resolve a canonical user ID first, then an encrypted Discord mapping.

    ``role_hint`` is intentionally non-authoritative.  Authentication adapters
    may provide it for diagnostics, but persisted account truth always wins.
    """
    token = str(raw_user_id or "").strip()
    if not token:
        raise UnresolvedRoutinePrincipal("routine principal is unresolved")

    user = user_db.get_user(token)
    if user is None:
        user = user_db.find_user_by_discord_id(token)
    if user is None or user.get("deleted_at"):
        raise UnresolvedRoutinePrincipal("routine principal is unresolved")

    canonical = str(user.get("user_id") or "").strip()
    if not canonical:
        raise UnresolvedRoutinePrincipal("routine principal is unresolved")
    return RoutinePrincipal(
        canonical_user_id=canonical,
        role=str(user.get("role") or "member"),
        actor_kind="user",
    )


__all__ = [
    "AmbiguousRoutineIdentity",
    "UnresolvedRoutinePrincipal",
    "resolve_principal",
]
