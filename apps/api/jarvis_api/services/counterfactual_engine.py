"""Counterfactual Engine — "What if we had chosen differently?"

Generates alternative scenarios from decisions, regrets, and incidents.
During idle time, can also generate "dream counterfactuals" —
speculative what-if scenarios about recent work.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    insert_cognitive_counterfactual,
    list_cognitive_counterfactuals,
)

logger = logging.getLogger(__name__)

_TRIGGER_TEMPLATES = {
    "regret": "Hvad hvis vi havde valgt en anden tilgang til {anchor}?",
    "incident": "Hvad hvis vi havde opdaget {anchor} tidligere?",
    "decision": "Hvad hvis vi havde valgt anderledes ved {anchor}?",
    "dream": "Hvad hvis {anchor} havde været løst fra starten?",
}


def generate_counterfactual(
    *,
    trigger_type: str,
    anchor: str,
    source: str = "runtime",
    confidence: float = 0.5,
) -> dict[str, object]:
    """Generate a counterfactual question from a trigger event."""
    template = _TRIGGER_TEMPLATES.get(trigger_type, "Hvad hvis {anchor} var gået anderledes?")
    question = template.format(anchor=anchor[:80])

    cf_id = f"cf-{uuid4().hex[:10]}"
    result = insert_cognitive_counterfactual(
        cf_id=cf_id,
        trigger_type=trigger_type,
        anchor=anchor[:200],
        cf_question=question,
        source=source,
        confidence=confidence,
    )

    event_bus.publish(
        "cognitive_counterfactual.generated",
        {"cf_id": cf_id, "trigger_type": trigger_type, "source": source},
    )
    return result


def generate_dream_counterfactual(
    *,
    recent_decisions: list[dict] | None = None,
) -> dict[str, object] | None:
    """Generate a speculative counterfactual during idle time."""
    decisions = recent_decisions or []
    if not decisions:
        return None

    # Pick the most recent decision
    latest = decisions[0]
    title = str(latest.get("title") or "")
    if not title:
        return None

    return generate_counterfactual(
        trigger_type="dream",
        anchor=title,
        source="dream",
        confidence=0.3,
    )


def build_counterfactual_surface() -> dict[str, object]:
    items = list_cognitive_counterfactuals(limit=15)
    dream_count = sum(1 for i in items if i.get("source") == "dream")
    runtime_count = len(items) - dream_count
    return {
        "active": bool(items),
        "items": items,
        "dream_count": dream_count,
        "runtime_count": runtime_count,
        "summary": (
            f"{len(items)} counterfactuals ({runtime_count} runtime, {dream_count} dream)"
            if items else "No counterfactuals yet"
        ),
    }
