"""Central 'self' route — surfaces Jarvis' SELF to the OWNER, reduced + absorbed.

``GET /central/self`` projects the three self-producer surfaces —
``living_executive`` (impulse→choice→action motor), ``runtime_self_model``
(self-understanding) and ``world_model_signal_tracking`` (world model) — into a
REDUCED owner-safe snapshot (§24.4: only liveness/counts/governance-consequence,
NEVER raw content like current_focus/recent_traces/items) and ABSORBS each into
the Central as a living nerve (full treatment via ``central_absorb.absorb``).

Owner-gated + read-only. This exposes the private self-layer to the owner's own
eyes over his authenticated tunnel — NOT egress to any external service.

SELF-SAFE end to end: each surface builder is wrapped; a missing/empty/raising
surface → ``{}`` for that key, and the route always returns a 200-shape dict.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from apps.api.jarvis_api.routes.central_auth import require_central_owner
from core.services.central_absorb import absorb
from core.services.central_private_reducer import reduce_for_owner
from core.services.central_runtime_proxy import proxy_or_local

router = APIRouter(prefix="/central", tags=["central-self"])


def _live_executive() -> dict:
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


def _derive_liveness(raw: dict) -> bool:
    """Owner-safe liveness: prefer an explicit ``active`` flag, else non-empty."""
    if "active" in raw:
        return bool(raw.get("active"))
    return bool(raw)


# Each entry: (nerve-name, zero-arg builder, kept owner-safe meta keys).
# ``summary`` is pure counts (owner-safe); ``mode``/``built_at`` are meta;
# ``liveness`` is derived in-route (works for both local + 8011-proxy paths).
# Raw content keys (current_focus/recent_traces/items/...) are NEVER kept and
# are additionally blocklisted by reduce_for_owner.
_SURFACES = (
    ("living_executive", _live_executive, ("liveness", "mode", "summary")),
    ("self_model", _self_model, ("liveness", "summary", "built_at")),
    ("world_model", _world_model, ("liveness", "summary")),
)


@router.get("/self")
async def get_self() -> dict:
    """Jarvis' reduced self-snapshot (owner-only, read-only, self-safe)."""
    require_central_owner()
    out: dict = {}
    for name, builder, keep in _SURFACES:
        try:
            raw = proxy_or_local(name, builder)
            if not isinstance(raw, dict) or not raw:
                red: dict = {}
            else:
                # Derive owner-safe liveness AFTER proxy (covers local + HTTP paths).
                raw = {**raw, "liveness": _derive_liveness(raw)}
                red = reduce_for_owner(raw, keep=keep)
        except Exception:
            red = {}
        out[name] = red
        try:
            absorb("self", name, red)  # living nerve — full treatment
        except Exception:
            pass
    return {"self": out, "ts": datetime.now(timezone.utc).isoformat()}
