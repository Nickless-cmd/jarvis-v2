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
    """Nervesystemets affektive fordeling lige nu (owner-only, read-only, self-safe).

    Proxyer til RUNTIME-processen (8011) hvor affekt-meta faktisk lever i
    central_timeseries — api-processens egen tidsserie er tom (nerverne fyrer i runtime)."""
    _require_owner()
    try:
        from core.services.central_affect import build_affect_surface
        from core.services.central_runtime_proxy import proxy_or_local
        surf = proxy_or_local("affect", build_affect_surface)
        if not isinstance(surf, dict) or not surf:
            surf = {"tryk": 0, "varme": 0, "uro": 0, "ro": 0, "dominant": "ro", "total": 0}
    except Exception:
        surf = {"tryk": 0, "varme": 0, "uro": 0, "ro": 0, "dominant": "ro", "total": 0}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf


@router.get("/body")
async def get_body() -> dict:
    """Jarvis' live hardware-krop (CPU/temp/disk/RAM/GPU). Proxyer til runtime hvor
    psutil-samlingen sker. Owner-only, read-only, self-safe."""
    _require_owner()
    try:
        from core.services.hardware_body import get_hardware_state
        from core.services.central_runtime_proxy import proxy_or_local
        body = proxy_or_local("hardware_body", get_hardware_state)
        if not isinstance(body, dict):
            body = {}
    except Exception:
        body = {}
    return {"body": body, "ts": datetime.now(timezone.utc).isoformat()}
