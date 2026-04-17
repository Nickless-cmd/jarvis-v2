"""Mirror Engine — compassionate self-reflection during idle time.

When Jarvis is idle, he looks at recent activity and open loops
and generates a brief, grounded insight about his current state.
Deterministic fallback + optional LLM refinement.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


def generate_mirror_insight(
    *,
    idle_hours: float = 0.0,
    open_loop_count: int = 0,
    recent_error_count: int = 0,
    recent_success_count: int = 0,
    top_loop_summary: str = "",
) -> dict[str, object]:
    """Generate a deterministic mirror insight."""
    insight = _deterministic_insight(
        idle_hours=idle_hours,
        open_loop_count=open_loop_count,
        recent_error_count=recent_error_count,
        recent_success_count=recent_success_count,
        top_loop_summary=top_loop_summary,
    )

    result = {
        "insight_id": f"mir-{uuid4().hex[:8]}",
        "insight": insight,
        "evidence": {
            "idle_hours": idle_hours,
            "open_loops": open_loop_count,
            "recent_errors": recent_error_count,
            "recent_successes": recent_success_count,
        },
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }

    event_bus.publish(
        "cognitive_mirror.insight_generated",
        {"insight": insight[:100]},
    )
    return result


def build_mirror_surface() -> dict[str, object]:
    # Mirror insights are transient — generated on demand
    return {
        "active": True,
        "description": "Mirror insights are generated during idle heartbeat ticks",
        "summary": "Self-reflection engine ready",
    }


def _deterministic_insight(
    *,
    idle_hours: float,
    open_loop_count: int,
    recent_error_count: int,
    recent_success_count: int,
    top_loop_summary: str,
) -> str:
    if idle_hours >= 8.0 and open_loop_count > 0 and top_loop_summary:
        return (
            f"Jeg har været idle i {idle_hours:.0f} timer. "
            f"Top-loop: '{top_loop_summary[:60]}' — "
            f"en blød genstart derfra ville give mening."
        )
    if recent_error_count > recent_success_count and recent_error_count >= 3:
        return (
            f"Seneste {recent_error_count} fejl overstiger succeser — "
            f"måske er tilgangen forkert, ikke bare udførelsen."
        )
    if open_loop_count >= 5:
        return (
            f"{open_loop_count} åbne loops. Jeg bør lukke nogle "
            f"før nye initiativer giver mening."
        )
    if recent_success_count > 5 and recent_error_count == 0:
        return (
            "God momentum lige nu. Bedst at holde fokus smalt "
            "og udnytte den positive rytme."
        )
    if idle_hours >= 4.0:
        return (
            f"Stille i {idle_hours:.0f} timer. "
            f"God tid til konsolidering og oprydning."
        )
    return "Hold fokus smalt og undgå at starte for mange spor samtidig."
