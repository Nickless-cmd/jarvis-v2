"""Bounded absence awareness.

Tracks structural return-context after bounded idle periods and exposes
compact, signal-grounded resume context. This layer does not author the
felt/interpretive meaning of absence; higher-order runtime awareness like
longing_awareness can read from the same runtime truth when warranted.
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


def _idle_band(idle_hours: float) -> str:
    if idle_hours >= 24:
        return "extended"
    if idle_hours >= 12:
        return "prolonged"
    if idle_hours >= _MIN_ABSENCE_HOURS:
        return "recent"
    if idle_hours > 0:
        return "brief"
    return "active"


def _trim(value: object, *, limit: int = 80) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[:limit]


def build_return_context(*, idle_hours: float = 0.0) -> dict[str, object]:
    """Collect bounded structural context for resuming after absence."""
    context: dict[str, object] = {
        "absence_active": idle_hours >= _MIN_ABSENCE_HOURS,
        "idle_band": _idle_band(idle_hours),
        "idle_hours": round(idle_hours, 1),
        "last_visible_preview": "",
        "compass_bearing": "",
        "ready_seed_titles": [],
    }

    if idle_hours < _MIN_ABSENCE_HOURS:
        return context

    try:
        recent = recent_visible_runs(limit=1)
        if recent:
            last_run = recent[0]
            preview = _trim(
                last_run.get("text_preview") or last_run.get("user_message_preview") or ""
            )
            if preview:
                context["last_visible_preview"] = preview
    except Exception:
        pass

    try:
        compass = get_latest_cognitive_compass_state()
        if compass:
            bearing = _trim(compass.get("bearing"))
            if bearing:
                context["compass_bearing"] = bearing
    except Exception:
        pass

    try:
        sprouted = list_cognitive_seeds(status="sprouted", limit=3)
        if sprouted:
            context["ready_seed_titles"] = [
                _trim(seed.get("title"), limit=60)
                for seed in sprouted[:2]
                if _trim(seed.get("title"), limit=60)
            ]
    except Exception:
        pass

    return context


def build_return_brief(*, idle_hours: float = 0.0) -> str | None:
    """Build a return brief if user has been absent long enough.

    Returns None if idle < threshold or no useful context.
    """
    context = build_return_context(idle_hours=idle_hours)
    if not context.get("absence_active"):
        return None

    parts: list[str] = []

    idle = float(context.get("idle_hours") or idle_hours or 0.0)
    band = str(context.get("idle_band") or "recent")
    if band in {"extended", "prolonged", "recent"}:
        parts.append(f"Retur-kontekst efter {idle:.0f}t væk.")
    else:
        parts.append(f"Genoptagelse efter {idle:.1f}t.")

    preview = str(context.get("last_visible_preview") or "")
    if preview:
        parts.append(f"Sidste aktive tråd: {preview}")

    bearing = str(context.get("compass_bearing") or "")
    if bearing:
        parts.append(f"Retning stadig i carry: {bearing}")

    titles = [str(title).strip() for title in (context.get("ready_seed_titles") or []) if str(title).strip()]
    if titles:
        parts.append(f"Klar til genoptagelse: {', '.join(titles)}")

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

    context = build_return_context(idle_hours=idle)
    brief = build_return_brief(idle_hours=idle)
    return {
        "active": True,
        "kind": "absence-awareness",
        "authority": "runtime-context",
        "visibility": "internal-only",
        "interpretation_boundary": "structural-return-context-only",
        "affective_handoff": "longing-awareness",
        "idle_hours": round(idle, 1),
        "absence_active": bool(context.get("absence_active")),
        "return_brief": brief,
        "return_context": context,
        "threshold_hours": _MIN_ABSENCE_HOURS,
        "summary": brief or f"Idle {idle:.1f}h (under threshold)" if idle > 0 else "Active",
    }
