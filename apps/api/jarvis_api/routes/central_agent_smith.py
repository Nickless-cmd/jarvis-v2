"""Central 'agent-smith' route — selv-lighed-kritikerens dom (owner, read-only, self-safe).

Overflader Agent Smiths vurdering af om Jarvis gentager sig selv: selv-lighed-score + top-gentagne
fraser/mønstre + modstemme-status."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-agent-smith"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/agent-smith")
async def get_agent_smith() -> dict:
    """Agent Smith: selv-lighed-score + top-gentagne fraser/mønstre + modstemme-status. Owner-only."""
    _require_owner()
    try:
        from core.services.central_agent_smith import build_agent_smith_surface
        surf = build_agent_smith_surface()
        if not isinstance(surf, dict):
            surf = {"status": "unavailable"}
    except Exception:
        surf = {"status": "unavailable"}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
