"""Central-ejet unified router (spec §5.5). ÉT beslutnings-punkt for alle lanes.

Invariant: route() returnerer ALTID et target eller den garanterede bund — rejser
ALDRIG. Kandidat-rangering samles her; lanes' lokale hot-path-failover bevares.
Bygges shadow→live via central_switches ('central_route_live')."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _rank_candidates(lane: str, task: Any, exclude: frozenset[str]) -> list[tuple[str, str]]:
    """Rangerede (provider, model) for en lane. Genbruger den eksisterende
    selection-kandidat-bygger + proaktiv headroom-de-vægtning (Task 8)."""
    from core.services.cheap_provider_runtime_selection import _configured_cheap_candidates
    from core.services.central_route_headroom import headroom_ok, headroom_weight
    cands = _configured_cheap_candidates(include_public_proxy=True)
    out: list[tuple[float, str, str]] = []
    for c in cands:
        p, m = str(c.get("provider") or ""), str(c.get("model") or "")
        if not p or not m or p in exclude or not c.get("credentials_ready"):
            continue
        if not headroom_ok(p):            # >=95% kvote → skip proaktivt
            continue
        prio = float(c.get("priority") or 9999)
        out.append((prio / max(headroom_weight(p), 1e-3), p, m))  # de-vægt ved >=80%
    out.sort(key=lambda x: x[0])
    return [(p, m) for _, p, m in out]


def route(*, lane: str, task: Any = None,
          exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Vælg (provider, model) for en lane. Aldrig tør."""
    try:
        ranked = _rank_candidates(lane, task, exclude)
    except Exception:
        logger.debug("central_route: kandidat-rangering fejlede", exc_info=True)
        ranked = []
    if ranked:
        p, m = ranked[0]
        return {"provider": p, "model": m, "lane": lane,
                "reason": "central-route:ranked", "is_floor": False}
    from core.services.cheap_lane_floor import floor_targets
    ft = floor_targets()
    if ft:
        p, m = ft[0]
        return {"provider": p, "model": m, "lane": lane,
                "reason": "central-route:floor", "is_floor": True}
    return {"provider": "floor", "model": "", "lane": lane,
            "reason": "central-route:degraded", "is_floor": True}
