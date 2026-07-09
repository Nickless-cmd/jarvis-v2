"""Central 'proactivity' route — proaktivitets-broens beslutninger (owner, read-only, self-safe).

Overflader hvad broen ville/har sendt til Bjørn: switch-status + ventende urgent/normal kandidater."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-proactivity"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/proactivity")
async def get_proactivity() -> dict:
    """Proaktivitets-broen: switch-status + ventende urgent/normal kandidater. Owner-only."""
    _require_owner()
    try:
        from core.services.proactivity_bridge import build_proactivity_bridge_surface
        surf = build_proactivity_bridge_surface()
        if not isinstance(surf, dict):
            surf = {"status": "unavailable"}
    except Exception:
        surf = {"status": "unavailable"}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
