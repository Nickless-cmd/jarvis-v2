"""Central 'feel' route — surfaces Jarvis' somatic/inner-life snapshot to the OWNER.

Owner-gated + read-only. This exposes the private layer to the owner's own eyes
(over his own authenticated tunnel) — it is NOT egress to any external service.
The snapshot is the cheap, buffered somatic lines (no LLM), so it is fast enough
to call on demand from the Central HUD's ``feel`` command.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/central", tags=["central-feel"])


def _require_owner() -> None:
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    if uid is None:
        return
    try:
        from core.identity.users import find_user_by_discord_id
        if getattr(find_user_by_discord_id(str(uid)), "role", "") == "owner":
            return
    except Exception:
        pass
    raise HTTPException(status_code=403, detail="Centralen er kun for owner")


@router.get("/feel")
async def get_feel() -> dict:
    """Jarvis' current somatic snapshot (owner-only, read-only, self-safe)."""
    _require_owner()
    try:
        from core.services.visible_inner_life import build_somatic_snapshot
        lines = build_somatic_snapshot()
    except Exception:
        lines = []
    return {
        "lines": lines,
        "count": len(lines),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
