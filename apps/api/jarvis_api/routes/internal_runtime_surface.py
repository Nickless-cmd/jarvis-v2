"""Internal runtime-surface endpoint — proxy-mål for Centralens self/mind-flader.

`core/services/central_runtime_proxy.proxy_or_local` kalder dette endpoint på
jarvis-runtime (port 8011) når api kører api-only, så runtime-proces-tilstand
(living_executive, self_model, world_model, …) kan læses fra api-processen.

Ligger under `/api/internal/` (auth-fri prefix jf. middleware `_PUBLIC_PATHS`) og
håndhæver **loopback-only** på rute-niveau (samme mønster som internal_discord.py):
kun 127.0.0.1/::1 uden X-Forwarded-For. 8011 er ikke eksternt eksponeret, så den
rå builder-output kan ikke tilgås udefra; §24.4-reduktionen sker på api-siden via
`central_private_reducer.reduce_for_owner`. Self-safe: ukendt navn/fejl → {}.
"""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/internal", tags=["internal-runtime-surface"])


def _require_loopback(request: Request) -> None:
    client_host = request.client.host if request.client else ""
    if client_host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="loopback-only")
    if request.headers.get("x-forwarded-for"):
        raise HTTPException(status_code=403, detail="loopback-only (proxy-forwarded)")


def _living_executive() -> dict:
    from core.services.living_executive import build_living_executive_surface
    return build_living_executive_surface()


def _self_model() -> dict:
    """LIGHT self-model: kun top-level tællere, ikke den 255KB nestede payload
    (undgå at hamre 255KB pr. self-view). Bygger fuld surface men returnerer småt."""
    from core.services.runtime_self_model import build_runtime_self_model
    full = build_runtime_self_model()
    if not isinstance(full, dict):
        return {}
    layers = full.get("layers") or []
    return {
        "liveness": True,
        "summary": {
            "layer_count": len(layers) if hasattr(layers, "__len__") else 0,
            "sections": len([k for k in full.keys() if k != "layers"]),
            "built_at": str(full.get("built_at") or full.get("generated_at") or ""),
        },
    }


def _world_model() -> dict:
    from core.services.world_model_signal_tracking import (
        build_runtime_world_model_signal_surface,
    )
    return build_runtime_world_model_signal_surface()


def _inner_life() -> dict:
    from core.services.central_inner_life_digest import build_inner_life_digest
    return build_inner_life_digest()


# Navn → builder. Udvides efterhånden som flere runtime-flader absorberes (mind-sektioner).
_BUILDERS: dict[str, Callable[[], dict]] = {
    "living_executive": _living_executive,
    "self_model": _self_model,
    "world_model": _world_model,
    "inner_life": _inner_life,
}


@router.get("/runtime-surface/{name}")
async def get_runtime_surface(name: str, request: Request) -> dict:
    """Return the named runtime-surface builder's output (raw). Loopback-only, self-safe."""
    _require_loopback(request)
    builder = _BUILDERS.get(name)
    if builder is None:
        return {}
    try:
        out = builder()
        if not isinstance(out, dict):
            out = {"value": out}
        # JSON-safe: nogle self/world-flader indeholder ikke-serialiserbare værdier
        # (datetimes, objekter) → FastAPI ville 500'e og proxyen få tomt. Round-trip
        # med default=str gør ALT serialiserbart uden at tabe struktur.
        import json
        return json.loads(json.dumps(out, default=str))
    except Exception:
        logger.debug("runtime-surface builder failed: %s", name, exc_info=True)
        return {}
