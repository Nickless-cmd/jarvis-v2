"""Long-horizon goals — persistent objectives across sessions.

Goals are first-class state: they live in the DB, show up in Jarvis's
heartbeat every cycle, and publish events so Mission Control (and any
other subscribers) can follow progress.

Surface:
- create_goal, update_goal, complete_goal, abandon_goal
- list_active_goals / get_goal_with_history
- format_active_goals_for_heartbeat() — compact prompt line
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db_goals import (
    append_goal_update,
    count_goals,
    create_goal as _db_create_goal,
    delete_goal as _db_delete_goal,
    get_goal as _db_get_goal,
    last_progress_map as _db_last_progress_map,
    list_goal_updates,
    list_goals as _db_list_goals,
    update_goal_fields,
)

logger = logging.getLogger(__name__)


def create_goal(
    *,
    title: str,
    description: str | None = None,
    priority: int = 50,
    target_date: str | None = None,
    tags: list[str] | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    goal = _db_create_goal(
        title=title,
        description=description,
        priority=priority,
        target_date=target_date,
        tags=tags,
        created_by=created_by,
    )
    try:
        event_bus.publish(
            "goal.created",
            {
                "goal_id": goal.get("goal_id"),
                "title": goal.get("title"),
                "priority": goal.get("priority"),
                "created_by": goal.get("created_by"),
            },
        )
    except Exception as exc:
        logger.debug("long_horizon_goals: publish goal.created failed: %s", exc)
    return goal


def update_goal(
    *,
    goal_id: str,
    note: str,
    progress_delta: int | None = None,
    new_status: str | None = None,
    source: str | None = None,
) -> dict[str, Any] | None:
    goal = append_goal_update(
        goal_id=goal_id,
        note=note,
        progress_delta=progress_delta,
        source=source,
        new_status=new_status,
    )
    if not goal:
        return None
    try:
        event_bus.publish(
            "goal.updated",
            {
                "goal_id": goal.get("goal_id"),
                "title": goal.get("title"),
                "status": goal.get("status"),
                "progress_pct": goal.get("progress_pct"),
                "latest_note": goal.get("latest_note"),
                "source": source,
            },
        )
        if goal.get("status") == "completed":
            event_bus.publish(
                "goal.completed",
                {
                    "goal_id": goal.get("goal_id"),
                    "title": goal.get("title"),
                    "completed_at": goal.get("completed_at"),
                },
            )
    except Exception as exc:
        logger.debug("long_horizon_goals: publish goal.updated failed: %s", exc)
    return goal


def edit_goal(
    goal_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    priority: int | None = None,
    target_date: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any] | None:
    return update_goal_fields(
        goal_id,
        title=title,
        description=description,
        priority=priority,
        target_date=target_date,
        tags=tags,
    )


def delete_goal(goal_id: str) -> bool:
    ok = _db_delete_goal(goal_id)
    if ok:
        try:
            event_bus.publish("goal.deleted", {"goal_id": goal_id})
        except Exception:  # bevidst: en publish-fejl maa ikke rulle en gennemfoert sletning tilbage
            pass
    return ok


def get_goal(goal_id: str) -> dict[str, Any] | None:
    return _db_get_goal(goal_id)


def get_goal_with_history(goal_id: str, *, history_limit: int = 10) -> dict[str, Any] | None:
    goal = _db_get_goal(goal_id)
    if not goal:
        return None
    goal = dict(goal)
    goal["recent_updates"] = list_goal_updates(goal_id, limit=history_limit)
    return goal


def list_active_goals(*, limit: int = 20) -> list[dict[str, Any]]:
    return _db_list_goals(status="active", limit=limit)


def last_progress_map(goal_ids: list[str]) -> dict[str, str]:
    """Sidste REELLE fremskridt pr. mål — ikke sidste rørelse.

    28/10-2026: ``updated_at`` flytter sig også når nogen blot SKRIVER en note
    («dette mål er forladt»). Måler man den, kan vagten gøres blind ved at
    skrive til den. Her tæller kun opdateringer med ``progress_delta``.
    """
    return _db_last_progress_map(goal_ids)


def list_all_goals(*, limit: int = 100) -> list[dict[str, Any]]:
    return _db_list_goals(status="all", limit=limit)


def format_active_goals_for_heartbeat(*, max_goals: int = 5) -> str:
    """Compact single-paragraph summary for heartbeat prompt injection.

    Returns empty string if no active goals, so callers can join safely.
    """
    goals = _db_list_goals(status="active", limit=max_goals)
    if not goals:
        return ""
    parts: list[str] = []
    for g in goals:
        pct = int(g.get("progress_pct") or 0)
        title = str(g.get("title") or "").strip()
        note = str(g.get("latest_note") or "").strip()
        # ALDER (28/10-2026). Maalt samme dag: 4 af 5 aktive maal var uroert i
        # 29-170 dage, og jeg kunne ikke se det. Linjen viste titel + procent,
        # saa et maal paa 70% der ikke havde roert sig siden 11. maj laeste som
        # «naesten i maal» i stedet for «forladt». Procenten er et LOEFTE om
        # fremskridt; alderen er beviset paa om der skete noget.
        chunk = f"{title} ({pct}%)"
        alder = _alder_dage(g.get("updated_at"))
        if alder is not None:
            chunk += f" · {alder}d"
        if note:
            chunk += f" — {note[:120]}"
        parts.append(chunk)
    return " | ".join(parts)


def _alder_dage(tid: object) -> int | None:
    """Dage siden et ISO-tidsstempel. None hvis det mangler eller ikke kan læses.

    Bevidst None og ikke 0: et ukendt tidsstempel maa ikke se ud som «frisk».
    """
    raw = str(tid or "").strip()
    if not raw:
        return None
    try:
        return max(0, (datetime.now(UTC) - datetime.fromisoformat(raw)).days)
    except Exception:  # bevidst: et ulaeseligt tidsstempel skal give None (ukendt), ikke 0 (friskt)
        return None


def get_stats() -> dict[str, Any]:
    return {
        "active": count_goals(status="active"),
        "paused": count_goals(status="paused"),
        "completed": count_goals(status="completed"),
        "abandoned": count_goals(status="abandoned"),
        "total": count_goals(),
    }
