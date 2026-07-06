"""Central 'excess' route — Centralens gartner-sans (owner-view).

Bjørn+Claude (6. jul): Centralen skal kunne MÆRKE sin egen vægt (bloat/redundans) og FORESLÅ
konkrete snit — modvægten til dagens observatør/guvernør-arbejde. `?propose=1` kører den dybere
(dyre) dead-function-scan. Metadata-only (tal + fil/funktions-navne, ingen kode-indhold).
Owner-gated, read-only, self-safe.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-excess"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/excess")
async def get_excess(propose: int = 0) -> dict:
    """Excess-sans: føles-pres + oversized filer. ?propose=1 → tilføj dead-function-snit-forslag."""
    _require_owner()
    try:
        from core.services.central_excess import build_excess_surface, propose_cuts
        surf = build_excess_surface()
        if propose:
            surf["cuts"] = propose_cuts()
    except Exception:
        surf = {}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
