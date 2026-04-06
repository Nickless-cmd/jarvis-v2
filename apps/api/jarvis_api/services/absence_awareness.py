"""Absence Awareness — Jarvis notices when you're gone and prepares for your return.

When the user has been idle >4 hours, builds a return brief:
what was last worked on, open loops, sprouted seeds, compass bearing.
Injected into the visible prompt on first message after absence.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.runtime.db import (
    get_latest_cognitive_compass_state,
    get_latest_cognitive_chronicle_entry,
    list_cognitive_seeds,
    recent_visible_runs,
)

logger = logging.getLogger(__name__)

_MIN_ABSENCE_HOURS = 4.0


def build_return_brief(*, idle_hours: float = 0.0) -> str | None:
    """Build a return brief if user has been absent long enough.

    Returns None if idle < threshold or no useful context.
    """
    if idle_hours < _MIN_ABSENCE_HOURS:
        return None

    parts: list[str] = []

    # Time away
    if idle_hours >= 24:
        parts.append(f"Du har været væk i {idle_hours:.0f} timer.")
    elif idle_hours >= 8:
        parts.append(f"Velkommen tilbage ({idle_hours:.0f}t væk).")
    else:
        parts.append(f"Pause på {idle_hours:.1f}t.")

    # Last topic
    try:
        recent = recent_visible_runs(limit=1)
        if recent:
            last_run = recent[0]
            preview = str(last_run.get("text_preview") or last_run.get("user_message_preview") or "")[:80]
            if preview:
                parts.append(f"Sidst: {preview}")
    except Exception:
        pass

    # Compass bearing
    try:
        compass = get_latest_cognitive_compass_state()
        if compass:
            bearing = str(compass.get("bearing") or "")[:80]
            if bearing:
                parts.append(f"Retning: {bearing}")
    except Exception:
        pass

    # Sprouted seeds
    try:
        sprouted = list_cognitive_seeds(status="sprouted", limit=3)
        if sprouted:
            titles = [s.get("title", "?") for s in sprouted[:2]]
            parts.append(f"Klar: {', '.join(titles)}")
    except Exception:
        pass

    if len(parts) <= 1:
        return None

    return " | ".join(parts)[:400]


def build_absence_awareness_surface() -> dict[str, object]:
    """MC surface for absence awareness."""
    try:
        recent = recent_visible_runs(limit=1)
        if recent:
            last_at = str(recent[0].get("finished_at") or recent[0].get("started_at") or "")
            if last_at:
                try:
                    last_dt = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
                    idle = (datetime.now(UTC) - last_dt).total_seconds() / 3600
                except Exception:
                    idle = 0
            else:
                idle = 0
        else:
            idle = 0
    except Exception:
        idle = 0

    brief = build_return_brief(idle_hours=idle)
    return {
        "active": True,
        "idle_hours": round(idle, 1),
        "return_brief": brief,
        "threshold_hours": _MIN_ABSENCE_HOURS,
        "summary": brief or f"Idle {idle:.1f}h (under threshold)" if idle > 0 else "Active",
    }
