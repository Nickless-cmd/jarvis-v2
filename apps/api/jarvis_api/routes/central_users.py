"""Central 'users' route — hvornår var hver bruger sidst aktiv, og hvordan (owner-view).

Bjørn (6. jul): "Kan centralen se hvornår Mikkel sidst har været aktiv?" Fletter alle kilder
(chat/api/run/device) → sidst aktiv · via · aktiv nu · beskeder · token-estimat. Metadata-only
(ingen samtaleindhold). Owner-gated, read-only, self-safe.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-users"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/users")
async def get_user_activity() -> dict:
    """Bruger-aktivitet: sidst aktiv pr. bruger flettet fra alle kilder. Owner-only."""
    _require_owner()
    try:
        from core.services.user_activity import build_user_activity_surface
        surf = build_user_activity_surface()
        if not isinstance(surf, dict):
            surf = {}
    except Exception:
        surf = {}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
