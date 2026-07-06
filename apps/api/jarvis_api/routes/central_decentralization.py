"""Central 'decentralization' route — chokepoint-skat + sikre decentraliserings-kandidater (owner)."""
from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter
router = APIRouter(prefix="/central", tags=["central-decentralization"])
def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()
@router.get("/decentralization")
async def get_decentralization() -> dict:
    """Hvor meget af Centralen er unødvendig flaskehals + hvad kunne resolve lokalt. Owner-only."""
    _require_owner()
    try:
        from core.services.central_decentralization import analyze_chokepoint
        surf = analyze_chokepoint()
    except Exception:
        surf = {}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
