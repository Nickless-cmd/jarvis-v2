"""Internal runtime-surface endpoint — proxy-mål for Centralens self/mind-flader.

`core/services/central_runtime_proxy.proxy_or_local` kalder dette endpoint på
jarvis-runtime (port 8011) når api kører api-only, så runtime-proces-tilstand
(living_executive, self_model, world_model, …) kan læses fra api-processen.

Localhost-only proxy-mål: returnerer den RÅ builder-output; reduktionen (§24.4)
sker på api-siden via `central_private_reducer.reduce_for_owner`. 8011 er ikke
eksternt eksponeret. Self-safe: ukendt navn → {}, builder-fejl → {}.
"""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal-runtime-surface"])


def _living_executive() -> dict:
    from core.services.living_executive import build_living_executive_surface
    return build_living_executive_surface()


def _self_model() -> dict:
    from core.services.runtime_self_model import build_runtime_self_model
    return build_runtime_self_model()


def _world_model() -> dict:
    from core.services.world_model_signal_tracking import (
        build_runtime_world_model_signal_surface,
    )
    return build_runtime_world_model_signal_surface()


# Navn → builder. Udvides efterhånden som flere runtime-flader absorberes (mind-sektioner).
_BUILDERS: dict[str, Callable[[], dict]] = {
    "living_executive": _living_executive,
    "self_model": _self_model,
    "world_model": _world_model,
}


@router.get("/runtime-surface/{name}")
async def get_runtime_surface(name: str) -> dict:
    """Return the named runtime-surface builder's output (raw). Self-safe."""
    builder = _BUILDERS.get(name)
    if builder is None:
        return {}
    try:
        out = builder()
        return out if isinstance(out, dict) else {"value": out}
    except Exception:
        logger.debug("runtime-surface builder failed: %s", name, exc_info=True)
        return {}
