"""Long-horizon goals tools — Jarvis-facing CRUD for persistent goals.

goal_create: open a new long-horizon goal
goal_update: log progress on an existing goal (note, progress delta, status)
goal_list: see active (or filtered) goals
goal_get: fetch a single goal with recent history
"""
from __future__ import annotations

from typing import Any

from core.services import long_horizon_goals

_VALID_STATUS_FILTERS = ("active", "paused", "completed", "abandoned", "all")
_VALID_NEW_STATUS = ("active", "paused", "completed", "abandoned")


def _normalize_tags(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        items = [t.strip() for t in raw.split(",") if t.strip()]
        return items or None
    if isinstance(raw, list):
        items = [str(t).strip() for t in raw if str(t).strip()]
        return items or None
    return None


def _exec_goal_create(args: dict[str, Any]) -> dict[str, Any]:
    title = str(args.get("title") or "").strip()
    if not title:
        return {"status": "error", "error": "title is required"}
    description = args.get("description")
    try:
        priority = int(args.get("priority") or 50)
    except (TypeError, ValueError):
        priority = 50
    priority = max(0, min(100, priority))
    target_date = args.get("target_date") or None
    tags = _normalize_tags(args.get("tags"))
    created_by = str(args.get("created_by") or "jarvis").strip() or "jarvis"

    goal = long_horizon_goals.create_goal(
        title=title,
        description=str(description).strip() if description else None,
        priority=priority,
        target_date=str(target_date) if target_date else None,
        tags=tags,
        created_by=created_by,
    )
    return {"status": "ok", "goal": goal}


def _exec_goal_update(args: dict[str, Any]) -> dict[str, Any]:
    goal_id = str(args.get("goal_id") or "").strip()
    note = str(args.get("note") or "").strip()
    if not goal_id or not note:
        return {"status": "error", "error": "goal_id and note are required"}
    progress_delta = args.get("progress_delta")
    if progress_delta is not None:
        try:
            progress_delta = int(progress_delta)
        except (TypeError, ValueError):
            progress_delta = None
    new_status = args.get("new_status")
    if new_status and str(new_status).strip() not in _VALID_NEW_STATUS:
        return {
            "status": "error",
            "error": f"new_status must be one of {_VALID_NEW_STATUS}",
        }
    source = str(args.get("source") or "jarvis").strip() or "jarvis"

    goal = long_horizon_goals.update_goal(
        goal_id=goal_id,
        note=note,
        progress_delta=progress_delta,
        new_status=str(new_status).strip() if new_status else None,
        source=source,
    )
    if goal is None:
        return {"status": "error", "error": "goal_id not found"}
    return {"status": "ok", "goal": goal}


def _exec_goal_list(args: dict[str, Any]) -> dict[str, Any]:
    status = str(args.get("status") or "active").strip().lower()
    if status not in _VALID_STATUS_FILTERS:
        status = "active"
    try:
        limit = int(args.get("limit") or 20)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(100, limit))
    if status == "all":
        goals = long_horizon_goals.list_all_goals(limit=limit)
    else:
        from core.runtime.db_goals import list_goals
        goals = list_goals(status=status, limit=limit)
    return {
        "status": "ok",
        "count": len(goals),
        "goals": goals,
        "stats": long_horizon_goals.get_stats(),
    }


def _exec_goal_get(args: dict[str, Any]) -> dict[str, Any]:
    goal_id = str(args.get("goal_id") or "").strip()
    if not goal_id:
        return {"status": "error", "error": "goal_id is required"}
    try:
        history_limit = int(args.get("history_limit") or 10)
    except (TypeError, ValueError):
        history_limit = 10
    history_limit = max(1, min(50, history_limit))
    goal = long_horizon_goals.get_goal_with_history(
        goal_id, history_limit=history_limit
    )
    if goal is None:
        return {"status": "error", "error": "goal_id not found"}
    return {"status": "ok", "goal": goal}


GOAL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "goal_create",
            "description": (
                "Open a new long-horizon goal that Jarvis carries across "
                "sessions. Goals persist in the DB and surface in the "
                "heartbeat every cycle. Use when the user commits to a "
                "multi-day outcome, or when Jarvis himself decides to "
                "work toward something longer than the current conversation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short imperative goal (e.g. 'Help Morten finish his dissertation').",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional longer context — why this matters, success criteria.",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "0-100, higher = more weight in heartbeat. Default 50.",
                    },
                    "target_date": {
                        "type": "string",
                        "description": "Optional ISO date (YYYY-MM-DD) if the goal has a deadline.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional topical tags.",
                    },
                    "created_by": {
                        "type": "string",
                        "description": "Who opened this goal ('jarvis' or user id). Defaults to 'jarvis'.",
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "goal_update",
            "description": (
                "Log progress on an existing goal. Always include a note "
                "describing what happened. Optionally bump progress_pct "
                "(+/- delta), or flip status to paused/completed/abandoned. "
                "Reaching 100% progress auto-completes the goal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "string"},
                    "note": {
                        "type": "string",
                        "description": "What progress (or blocker) happened.",
                    },
                    "progress_delta": {
                        "type": "integer",
                        "description": "Change in progress_pct (e.g. +10, -5). Optional.",
                    },
                    "new_status": {
                        "type": "string",
                        "enum": list(_VALID_NEW_STATUS),
                        "description": "Optional explicit status change.",
                    },
                    "source": {
                        "type": "string",
                        "description": "Where this update came from (inner-voice, user, reflection, etc.).",
                    },
                },
                "required": ["goal_id", "note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "goal_list",
            "description": (
                "List goals by status. Default returns active goals — "
                "pass status='all' or 'completed' etc. to see others."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": list(_VALID_STATUS_FILTERS),
                    },
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "goal_get",
            "description": (
                "Fetch a single goal with its recent progress-update history."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "string"},
                    "history_limit": {"type": "integer"},
                },
                "required": ["goal_id"],
            },
        },
    },
]


GOAL_TOOL_HANDLERS: dict[str, Any] = {
    "goal_create": _exec_goal_create,
    "goal_update": _exec_goal_update,
    "goal_list": _exec_goal_list,
    "goal_get": _exec_goal_get,
}
