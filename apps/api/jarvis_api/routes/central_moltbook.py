"""Central 'moltbook' route — Jarvis' Moltbook-tilstedeværelse (owner, read-only, self-safe).

Overflader observe-nervens status: sidste scan, ny aktivitet, seneste tråde, credential-/switch-status."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-moltbook"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/moltbook")
async def get_moltbook() -> dict:
    """Moltbook observe-nerve: sidste scan + ny aktivitet + seneste tråde + status. Owner-only."""
    _require_owner()
    try:
        from core.services.central_moltbook import build_moltbook_surface
        surf = build_moltbook_surface()
        if not isinstance(surf, dict):
            surf = {"status": "unavailable"}
    except Exception:
        surf = {"status": "unavailable"}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
