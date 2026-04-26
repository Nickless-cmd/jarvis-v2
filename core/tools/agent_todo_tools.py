"""Tool wrappers for the per-session todo tracker (agent_todos)."""
from __future__ import annotations

from typing import Any

from core.services.agent_todos import (
    add_todo,
    list_todos,
    remove_todo,
    set_todos,
    update_todo_status,
)


def _session_id_arg(args: dict[str, Any]) -> str | None:
    raw = args.get("session_id")
    return str(raw).strip() if raw else None


def _exec_todo_list(args: dict[str, Any]) -> dict[str, Any]:
    items = list_todos(_session_id_arg(args))
    return {"status": "ok", "todos": items, "count": len(items)}


def _exec_todo_set(args: dict[str, Any]) -> dict[str, Any]:
    raw_items = args.get("todos")
    if not isinstance(raw_items, list):
        return {"status": "error", "error": "todos must be a list of {content, status?, id?}"}
    return set_todos(_session_id_arg(args), raw_items)


def _exec_todo_add(args: dict[str, Any]) -> dict[str, Any]:
    return add_todo(_session_id_arg(args), str(args.get("content") or ""))


def _exec_todo_update_status(args: dict[str, Any]) -> dict[str, Any]:
    return update_todo_status(
        _session_id_arg(args),
        str(args.get("todo_id") or ""),
        str(args.get("status") or ""),
    )


def _exec_todo_remove(args: dict[str, Any]) -> dict[str, Any]:
    return remove_todo(_session_id_arg(args), str(args.get("todo_id") or ""))


AGENT_TODO_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "todo_list",
            "description": (
                "List your active todos for this session. Use this any time "
                "you want to check what's outstanding before deciding what to "
                "do next. Empty list means nothing tracked."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Defaults to current session."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_set",
            "description": (
                "Replace your todo list for this session. Use this when starting "
                "a multi-step task — write down what needs to happen, then mark "
                "items as you progress. Each todo: {content (required), status "
                "(pending/in_progress/completed, default pending)}. Hard rule: "
                "max ONE in_progress at a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                                "id": {"type": "string", "description": "Optional, auto-generated if omitted."},
                            },
                            "required": ["content"],
                        },
                    },
                },
                "required": ["todos"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_add",
            "description": "Append a single todo to your session list (status pending).",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_update_status",
            "description": (
                "Change a todo's status. Marking a todo in_progress automatically "
                "demotes any other in_progress todo to pending."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "todo_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                },
                "required": ["todo_id", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_remove",
            "description": "Remove a todo from your session list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "todo_id": {"type": "string"},
                },
                "required": ["todo_id"],
            },
        },
    },
]
