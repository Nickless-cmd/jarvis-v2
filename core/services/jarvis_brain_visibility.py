"""Privacy-gate for Jarvis Brain recall.

Princip: mindst privilegerede deltager vinder. Default deny.
Skrivning påvirkes ikke — kun læsning gates her.

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md sektion 6.
"""
from __future__ import annotations
from typing import Any

LEVEL = {"public_safe": 0, "personal": 1, "intimate": 2}


def _resolve_owner_id() -> str | None:
    """Hentet via owner_resolver. Wrapped så tests kan monkeypatche."""
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        oid = get_owner_discord_id()
        if oid:
            return str(oid)
    except Exception:
        pass
    try:
        from core.identity.owner_resolver import get_owner_user_id  # type: ignore
        return get_owner_user_id()
    except Exception:
        return None


def can_recall(entry_visibility: str, ceiling: str) -> bool:
    """True if entry's visibility is permitted at the given ceiling."""
    return LEVEL[entry_visibility] <= LEVEL[ceiling]


def session_visibility_ceiling(session: Any) -> str:
    """Beregn visibility-ceiling for en session.

    Beslutningstræ (spec sektion 6.2):
      1. autonomous/inner_voice → personal
      2. ingen kendt deltager → public_safe (default deny)
      3. ≥1 ikke-owner deltager → public_safe (mindst-privilegeret-vinder)
      4. 1:1 DM med owner → intimate
      5. owner-only kanal → personal
      6. ellers → public_safe (default deny)
    """
    if getattr(session, "is_autonomous", False) or getattr(session, "is_inner_voice", False):
        return "personal"

    participants = getattr(session, "participants", None)
    if not participants:
        return "public_safe"

    owner_id = _resolve_owner_id()
    non_owner_count = sum(1 for p in participants if p != owner_id)
    if non_owner_count >= 1:
        return "public_safe"

    channel_kind = getattr(session, "channel_kind", "")
    if channel_kind in {"dm", "jarvisx_native"}:
        return "intimate"
    if channel_kind in {"owner_private_channel", "owner_only_workspace"}:
        return "personal"
    return "public_safe"
