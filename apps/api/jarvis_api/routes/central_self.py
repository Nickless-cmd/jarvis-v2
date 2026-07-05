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


# -- Fase C: de PRIVATE lag hvor emergent agentur bor (§24.4). Hver builder
# kører producenten og reducerer STRAKS til light (liveness + tællere) via den
# samme _light-helper som internal-ruten. Så både proxy-stien (api-only, henter
# allerede-light fra 8011) OG den lokale sti (runtime-proces) giver en `summary`,
# og reduce_for_owner(keep=("liveness","summary")) kan aldrig slippe råt indhold
# igennem. Rå selv-indhold (uløste mål, forudsigelses-tekst, selv-forståelse)
# forlader ALDRIG processen.
def _open_loops() -> dict:
    from apps.api.jarvis_api.routes.internal_runtime_surface import _light
    from core.services.open_loop_signal_tracking import (
        build_runtime_open_loop_signal_surface,
    )
    return _light(build_runtime_open_loop_signal_surface())


def _runtime_awareness() -> dict:
    from apps.api.jarvis_api.routes.internal_runtime_surface import _light
    from core.services.runtime_awareness_signal_tracking import (
        build_runtime_awareness_signal_surface,
    )
    return _light(build_runtime_awareness_signal_surface())


def _runtime_self_knowledge() -> dict:
    from apps.api.jarvis_api.routes.internal_runtime_surface import _light
    from core.services.runtime_self_knowledge import (
        build_runtime_self_knowledge_surface,
    )
    return _light(build_runtime_self_knowledge_surface())


def _counterfactual() -> dict:
    from apps.api.jarvis_api.routes.internal_runtime_surface import _light
    from core.services.counterfactual_predictions import (
        build_counterfactual_predictions_surface,
    )
    return _light(build_counterfactual_predictions_surface())


def _derive_liveness(raw: dict) -> bool:
    """Owner-safe liveness: prefer a builder-provided ``liveness`` flag (the
    light Fase C-builders already compute it), then an explicit ``active`` flag,
    else non-empty."""
    if "liveness" in raw:
        return bool(raw.get("liveness"))
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
    ("self_model", _self_model, ("liveness", "summary")),
    ("world_model", _world_model, ("liveness", "summary")),
    # Fase C — de private agentur-lag (allerede light fra builderen):
    ("open_loops", _open_loops, ("liveness", "summary")),
    ("runtime_awareness", _runtime_awareness, ("liveness", "summary")),
    ("runtime_self_knowledge", _runtime_self_knowledge, ("liveness", "summary")),
    ("counterfactual", _counterfactual, ("liveness", "summary")),
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


@router.get("/inner-life")
async def get_inner_life() -> dict:
    """Jarvis' reducerede inner-life-digest (owner-only, liveness+count, self-safe)."""
    require_central_owner()
    from core.services.central_runtime_proxy import proxy_or_local
    from core.services.central_inner_life_digest import build_inner_life_digest
    try:
        digest = proxy_or_local("inner_life", build_inner_life_digest)
    except Exception:
        digest = {}
    if not isinstance(digest, dict):
        digest = {}
    inner = digest.get("inner_life") or {}
    exp = digest.get("experiment") or {}
    live_count = digest.get("live_count") or 0
    total = digest.get("total") or 0

    # Absorbér HVER sektion som sin egen levende nerve (trace+flag+læring), så
    # Centralen sporer + lærer af hver enkelt. cluster="mind" for living-mind,
    # cluster="experiment" for AGI/experiment-laget. Self-safe pr. sektion.
    for name, sec in inner.items():
        try:
            absorb("mind", name, sec, learn_key=f"mind:{name}")
        except Exception:
            pass
    for name, sec in exp.items():
        try:
            absorb("experiment", name, sec, learn_key=f"experiment:{name}")
        except Exception:
            pass

    # Behold aggregat-absorb self:inner_life (live_count/total) + flag ved dødt sind.
    try:
        absorb("self", "inner_life", {"live_count": live_count, "total": total},
               flag_if=lambda v: v["total"] > 0 and v["live_count"] == 0,
               flag_reason="intet indre liv aktivt")
    except Exception:
        pass
    return {"inner_life": {"inner_life": inner, "experiment": exp,
                           "live_count": live_count, "total": total},
            "ts": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
