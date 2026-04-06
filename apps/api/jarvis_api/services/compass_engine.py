"""Compass Engine — weekly strategic bearing based on open loops and priorities.

Determines Jarvis' current direction: what to focus on, what to defer.
Updated weekly via heartbeat. Injected into visible prompt.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_latest_cognitive_compass_state,
    upsert_cognitive_compass_state,
)

logger = logging.getLogger(__name__)


def maybe_update_compass(
    *,
    open_loops: list[dict] | None = None,
    recent_decisions: list[dict] | None = None,
) -> dict[str, object] | None:
    """Update compass if >3 days since last update."""
    current = get_latest_cognitive_compass_state()
    now = datetime.now(UTC)

    if current:
        updated_at = _parse_iso(current.get("updated_at"))
        if updated_at and (now - updated_at) < timedelta(days=3):
            return None

    loops = open_loops or []
    loop_count = len(loops)

    if loop_count == 0:
        bearing = "Ingen åbne loops — klar til nye initiativer."
        rationale = "clean_slate"
    elif loop_count <= 2:
        top = str(loops[0].get("title") or loops[0].get("summary") or "")[:80]
        bearing = f"Fokusér på at afslutte: {top}" if top else "Afslut åbne loops før nye opgaver."
        rationale = "focused_completion"
    elif loop_count <= 5:
        bearing = f"{loop_count} åbne loops — prioritér de vigtigste, parkér resten."
        rationale = "selective_focus"
    else:
        bearing = f"{loop_count} åbne loops — reducer belastningen, afslut eller aflys."
        rationale = "overload_reduction"

    result = upsert_cognitive_compass_state(
        bearing=bearing,
        rationale=rationale,
        open_loop_count=loop_count,
    )

    event_bus.publish(
        "cognitive_compass.bearing_updated",
        {"bearing": bearing, "rationale": rationale, "open_loop_count": loop_count},
    )
    return result


def build_compass_surface() -> dict[str, object]:
    current = get_latest_cognitive_compass_state()
    return {
        "active": current is not None,
        "current": current,
        "summary": current.get("bearing", "No bearing set")[:80] if current else "No compass state",
    }


def _parse_iso(value) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except Exception:
        return None
