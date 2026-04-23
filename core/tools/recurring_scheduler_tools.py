"""Recurring scheduler tools — Jarvis can schedule repeating tasks."""
from __future__ import annotations

from typing import Any

_UNIT_TO_MINUTES = {
    "minutes": 1, "minute": 1, "min": 1,
    "hours": 60, "hour": 60, "h": 60,
    "days": 1440, "day": 1440, "d": 1440,
}


def _parse_interval(interval: Any, unit: str) -> int | None:
    """Return interval in minutes, or None on bad input."""
    try:
        n = int(interval)
        if n < 1:
            return None
        factor = _UNIT_TO_MINUTES.get(str(unit).lower().strip())
        if not factor:
            return None
        return n * factor
    except (TypeError, ValueError):
        return None


def _exec_schedule_recurring(args: dict[str, Any]) -> dict[str, Any]:
    focus = str(args.get("focus") or "").strip()
    interval = args.get("interval")
    unit = str(args.get("unit") or "minutes").strip().lower()
    delay_minutes = int(args.get("delay_minutes") or 0)

    if not focus:
        return {"status": "error", "error": "focus is required"}

    interval_minutes = _parse_interval(interval, unit)
    if interval_minutes is None:
        valid = ", ".join(_UNIT_TO_MINUTES.keys())
        return {"status": "error", "error": f"interval must be a positive integer and unit must be one of: {valid}"}

    if interval_minutes < 5:
        return {"status": "error", "error": "Minimum interval is 5 minutes to avoid spamming."}

    try:
        from core.services.recurring_tasks import create_recurring_task
        task = create_recurring_task(
            focus=focus,
            interval_minutes=interval_minutes,
            delay_minutes=delay_minutes,
        )
        unit_display = f"{interval} {unit}"
        return {
            "status": "ok",
            "task_id": task["task_id"],
            "focus": task["focus"],
            "interval": unit_display,
            "interval_minutes": interval_minutes,
            "next_fire_at": task["next_fire_at"],
            "text": f"Recurring task scheduled: '{focus}' every {unit_display}. First fire: {task['next_fire_at'][:16]}Z",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _exec_list_recurring(args: dict[str, Any]) -> dict[str, Any]:
    include_cancelled = bool(args.get("include_cancelled", False))
    try:
        from core.services.recurring_tasks import list_recurring_tasks
        tasks = list_recurring_tasks()
        if not include_cancelled:
            tasks = [t for t in tasks if t["status"] != "cancelled"]
        return {
            "status": "ok",
            "tasks": tasks,
            "count": len(tasks),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _exec_cancel_recurring(args: dict[str, Any]) -> dict[str, Any]:
    task_id = str(args.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "error": "task_id is required"}
    try:
        from core.services.recurring_tasks import cancel_recurring_task
        ok = cancel_recurring_task(task_id)
        if not ok:
            return {"status": "error", "error": f"Task {task_id!r} not found or already cancelled"}
        return {"status": "ok", "cancelled": task_id, "text": f"Recurring task {task_id} cancelled."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


RECURRING_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "schedule_recurring",
            "description": (
                "Schedule a repeating reminder or action at a fixed interval. "
                "Each time it fires, Jarvis receives a notification and it is pushed to the initiative queue. "
                "Examples: every night at 02:00, every 6 hours for system health checks."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "What Jarvis should do or think about when this fires. Max 300 chars.",
                    },
                    "interval": {
                        "type": "integer",
                        "description": "How often to repeat (numeric value, e.g. 6 for every 6 hours).",
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit for interval: 'minutes', 'hours', or 'days'. Default 'minutes'.",
                        "enum": ["minutes", "hours", "days"],
                    },
                    "delay_minutes": {
                        "type": "integer",
                        "description": "Optional: extra delay before the FIRST fire (in minutes). Default 0.",
                    },
                },
                "required": ["focus", "interval"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_recurring",
            "description": "List all recurring scheduled tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_cancelled": {
                        "type": "boolean",
                        "description": "Include cancelled tasks in the list (default false).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_recurring",
            "description": "Cancel an active recurring task by its task_id (from list_recurring).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task_id of the recurring task to cancel.",
                    },
                },
                "required": ["task_id"],
            },
        },
    },
]
