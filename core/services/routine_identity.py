"""Canonical, fail-closed identity resolution for Routine entry points."""
from __future__ import annotations

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

    from core.runtime import db
    from core.services.routine_migration import resolve_canonical_identity

    # Preserve ambiguity detection from the public identity adapter.  The
    # canonical resolver below remains the source of truth for the selected ID.
    from core.identity import user_db
    external = user_db.find_user_by_discord_id(token)
    external_id = str((external or {}).get("user_id") or "").strip()
    canonical = external_id if external_id and db.get_user_row(external_id) else resolve_canonical_identity(token)
    user = db.get_user_row(canonical) if canonical else None
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
