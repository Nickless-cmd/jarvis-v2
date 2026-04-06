"""Decision Log — records high-stakes decisions with context, options, and rationale.

Provides the basis for regret analysis and counterfactual reasoning.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    insert_cognitive_decision,
    list_cognitive_decisions,
)

logger = logging.getLogger(__name__)


def record_decision(
    *,
    title: str,
    context: str = "",
    options: list[str] | None = None,
    decision: str = "",
    why: str = "",
    refs: list[str] | None = None,
) -> dict[str, object]:
    """Record a decision in the log."""
    import json

    decision_id = f"dec-{uuid4().hex[:10]}"
    result = insert_cognitive_decision(
        decision_id=decision_id,
        title=title,
        context=context,
        options=json.dumps(options or [], ensure_ascii=False),
        decision=decision,
        why=why,
        refs=json.dumps(refs or [], ensure_ascii=False),
    )

    event_bus.publish(
        "cognitive_decision.recorded",
        {"decision_id": decision_id, "title": title},
    )
    return result


def build_decision_log_surface() -> dict[str, object]:
    decisions = list_cognitive_decisions(limit=15)
    return {
        "active": bool(decisions),
        "decisions": decisions,
        "total_count": len(decisions),
        "summary": (
            f"{len(decisions)} decisions recorded"
            if decisions else "No decisions logged yet"
        ),
    }
