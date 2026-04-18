from __future__ import annotations

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
