"""Central 'connections' route — hvem/hvad er forbundet til Jarvis' API (owner-view).

Bjørn (6. jul): "sådan du altid kan se hvem og hvad forbinder til din api og vi faktisk kan se
det og fange fejl." Presence for HTTP-API-trafik: IP, user/session, aktiv, last aktiv, tællere, fejl.

GDPR: metadata-only (ingen samtaleindhold). Fuld IP → /24 efter 48t. Owner-gated, read-only, self-safe.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-connections"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/connections")
async def get_api_connections() -> dict:
    """Live API-forbindelser: aktive/seneste klienter pr. (ip, user) + seneste fejl. Owner-only."""
    _require_owner()
    try:
        from core.services.api_connection_nerve import presence_view
        surf = presence_view()
        if not isinstance(surf, dict):
            surf = {}
    except Exception:
        surf = {}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
