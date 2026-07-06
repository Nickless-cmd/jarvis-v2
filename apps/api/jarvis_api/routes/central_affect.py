"""Central 'affect' route — surfaces nervesystemets affektive fordeling til OWNER.

Rådets #4: hver nerve bærer en affekt (tryk/varme/uro/ro). Denne route aggregerer
de seneste affekter på tværs af clusters til en fordeling + dominant-affekt, så
Central-HUD'en kan vise "hvordan nervesystemet føles lige nu".

Owner-gated + read-only + self-safe. Ren aggregering af buffered tidsserie-meta
(ingen LLM, ingen tung I/O) — hurtig nok til on-demand-kald fra HUD'en.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-affect"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/affect")
async def get_affect() -> dict:
    """Nervesystemets affektive fordeling lige nu (owner-only, read-only, self-safe)."""
    _require_owner()
    try:
        from core.services.central_affect import build_affect_surface
        surf = build_affect_surface()
    except Exception:
        surf = {"tryk": 0, "varme": 0, "uro": 0, "ro": 0, "dominant": "ro", "total": 0}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
