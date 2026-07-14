"""Agent-pool router (spec §4 + §5.5). Tyndt lag over central_route så agenter
router gennem det Central-ejede beslutnings-punkt — kvote-bevidst allerede på
den PRIMÆRE hop (i dag er kun fallback kvote-aware).

Bærer også kvalitets-lærings-loopet (§4.4): task_scores opdateres fra rigtige
agent-outcomes så poolen lærer hvilke modeller der er gode til hvad."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def route_agent_task(*, kind: str = "default", min_tokens: int = 0,
                     quality_threshold: float = 0.0, allow_paid: bool = False,
                     exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Vælg (provider, model) for en agent-task via central_route. Aldrig tør.

    allow_paid=False (default): kun GRATIS modeller (Jarvis' frie valg). allow_paid=True
    ("rigtig opgave"): betalte Copilot-premium (Claude/GPT-5.6) bliver også kandidater,
    scoret på kvalitet — de vælges først (høj prioritet) fordi de er bedst."""
    from core.services import central_route
    r = central_route.route(
        lane="agent",
        task={"kind": kind, "min_tokens": min_tokens,
              "quality_threshold": quality_threshold, "allow_paid": allow_paid},
        exclude=exclude,
    )
    return r


def _load_task_scores(provider: str, model: str) -> dict[str, float]:
    """Nuværende task_scores for (provider, model) fra runtime-state. {} ved intet."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        key = f"task_scores:{provider}:{model}"
        val = get_runtime_state_value(key, None)
        return dict(val) if isinstance(val, dict) else {}
    except Exception:
        return {}


def _save_task_scores(provider: str, model: str, scores: dict[str, float]) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(f"task_scores:{provider}:{model}", scores)
    except Exception:
        pass


def update_task_score(*, provider: str, model: str, kind: str,
                      outcome_quality: float, lr: float = 0.1) -> None:
    """§4.4 kvalitets-læring: EMA-opdatér task_score for (model, kind) fra et
    outcome-signal ∈ [0,1]. Emitter task_score_updated til Central."""
    scores = _load_task_scores(provider, model)
    prev = float(scores.get(kind, 0.5))
    new = (1.0 - lr) * prev + lr * float(outcome_quality)
    scores[kind] = new
    _save_task_scores(provider, model, scores)
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "task_score_updated",
                           "provider": provider, "model": model, "kind": kind,
                           "prev": prev, "new": new})
    except Exception:
        pass
