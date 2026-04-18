from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services.initiative_queue import (
    abandon_long_term_intention,
    list_active_long_term_intentions,
    seed_long_term_intention,
)


def create_life_project(
    *,
    title: str,
    why: str,
    source: str = "life-project",
    source_id: str = "",
    priority: str = "medium",
) -> dict[str, object]:
    initiative_id = seed_long_term_intention(
        title=title,
        why=why,
        source=source,
        source_id=source_id,
        priority=priority,
    )
    items = list_active_long_term_intentions(limit=3)
    item = next((entry for entry in items if str(entry.get("initiative_id") or "") == initiative_id), None)
    return {
        "status": "ok",
        "initiative_id": initiative_id,
        "life_project": item or {},
    }


def build_life_projects_surface() -> dict[str, object]:
    items = list_active_long_term_intentions(limit=3)
    return {
        "active": bool(items),
        "count": len(items),
        "items": items,
        "summary": (
            f"{len(items)} active life projects"
            if items
            else "No active life projects"
        ),
    }


def abandon_life_project(initiative_id: str, *, note: str = "") -> dict[str, object]:
    item = abandon_long_term_intention(initiative_id, note=note)
    if item is None:
        return {"status": "error", "error": f"life project {initiative_id!r} not found"}
    return {"status": "ok", "life_project": item}


def tick_life_projects_reassessment(
    *, trigger: str = "heartbeat", last_visible_at: str = ""
) -> dict[str, object]:
    """Periodisk re-vurdering af aktive life projects.

    Cadence: 1440 min (24t).
    Kill-switch: layer_life_projects_enabled i runtime.json.
    Gennemgår aktive long_term_intentions og markerer dem der er due for re-assessment
    (last_reviewed_at ældre end layer_life_projects_decay_days dage, default 14).
    """
    from core.runtime.secrets import read_runtime_key

    try:
        enabled = read_runtime_key("layer_life_projects_enabled")
    except Exception:
        enabled = True
    if not enabled:
        return {"status": "disabled", "reason": "layer_life_projects_enabled=false"}

    try:
        decay_days = int(read_runtime_key("layer_life_projects_decay_days"))
    except Exception:
        decay_days = 14
    threshold = timedelta(days=decay_days)
    now = datetime.now(UTC)

    items = list_active_long_term_intentions(limit=20)
    reviewed = 0
    skipped = 0

    for item in items:
        last_reviewed_raw = str(item.get("updated_at") or item.get("detected_at") or "")
        if not last_reviewed_raw:
            skipped += 1
            continue
        try:
            last_reviewed = datetime.fromisoformat(last_reviewed_raw.replace("Z", "+00:00"))
            if last_reviewed.tzinfo is None:
                last_reviewed = last_reviewed.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            skipped += 1
            continue

        if (now - last_reviewed) >= threshold:
            # Markér som due for re-assessment via event
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "life_projects.reassessment_due",
                {
                    "initiative_id": str(item.get("initiative_id") or ""),
                    "title": str(item.get("focus") or ""),
                    "last_reviewed_at": last_reviewed_raw,
                    "decay_days": decay_days,
                    "trigger": trigger,
                },
            )
            reviewed += 1
        else:
            skipped += 1

    return {"status": "ok", "reviewed": reviewed, "skipped": skipped, "trigger": trigger}
