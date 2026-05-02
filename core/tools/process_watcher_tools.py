"""Tool wrappers for the process_watcher service.

Exposes three tools to Jarvis:
  add_process_watch     — register a watch on a process or state file
  list_process_watches  — see active watches
  remove_process_watch  — drop a watch

Watches give Jarvis push-notifications: instead of polling via wakeups
("vågn op om 5 min og tjek bot'en"), he says "tell me when the bot
dies / when drawdown crosses 4% / when a new trade fires" and gets
a signal exactly when it happens.

Designed so the LLM can compose conditions without knowing internal
shapes — JSON-shaped condition dicts with explicit `kind` discriminator.
"""
from __future__ import annotations

from typing import Any


def _exec_add_process_watch(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.process_watcher import add_watch
    return add_watch(
        label=str(args.get("label") or ""),
        conditions=list(args.get("conditions") or []),
        on_match=str(args.get("on_match") or "push_initiative"),
        notify_text=str(args.get("notify_text") or ""),
        cooldown_seconds=int(args.get("cooldown_seconds") or 300),
        one_shot=bool(args.get("one_shot") or False),
    )


def _exec_list_process_watches(_args: dict[str, Any]) -> dict[str, Any]:
    from core.services.process_watcher import list_watches
    items = list_watches()
    return {"status": "ok", "count": len(items), "watches": items}


def _exec_remove_process_watch(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.process_watcher import remove_watch
    return remove_watch(str(args.get("watch_id") or ""))


def _exec_set_watch_enabled(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.process_watcher import set_watch_enabled
    return set_watch_enabled(
        watch_id=str(args.get("watch_id") or ""),
        enabled=bool(args.get("enabled", True)),
    )


PROCESS_WATCHER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "add_process_watch",
            "description": (
                "Register a watch that fires an action when a process or state-"
                "file condition matches. Use this for push-notifications instead "
                "of polling via wakeups. Conditions are evaluated every 10s by a "
                "daemon. Cooldown prevents action storms. one_shot=true deletes "
                "the watch after first fire."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "Human-readable name shown in notifications",
                    },
                    "conditions": {
                        "type": "array",
                        "description": (
                            "List of condition dicts. Watch fires if ANY matches. "
                            "Each condition needs a 'kind' field, plus kind-"
                            "specific args. Kinds: "
                            "'process_died' (needs process_name); "
                            "'log_pattern' (needs process_name + regex); "
                            "'state_field_threshold' (needs state_file + field "
                            "+ op[above|below|equals] + value); "
                            "'state_field_change' (needs state_file + field; "
                            "optional 'to' to filter on target value); "
                            "'state_stale' (needs state_file + max_age_seconds); "
                            "'state_list_grew' (needs state_file + field, e.g. "
                            "'recent_trades'). state_file accepts bare filename "
                            "(resolved under STATE_DIR), absolute path, or ~ paths."
                        ),
                        "items": {"type": "object"},
                    },
                    "on_match": {
                        "type": "string",
                        "enum": [
                            "push_initiative",
                            "self_wakeup",
                            "notify_owner",
                            "eventbus_publish",
                        ],
                        "description": (
                            "What to do when matched. push_initiative: surfaces "
                            "in next prompt. self_wakeup: schedules a wakeup "
                            "with the notify_text as prompt. notify_owner: "
                            "Discord DM to owner. eventbus_publish: emits "
                            "process_watcher.match event for subscribers."
                        ),
                    },
                    "notify_text": {
                        "type": "string",
                        "description": (
                            "Message text used by the action. Defaults to label "
                            "if empty. The matched-condition reason is appended "
                            "automatically."
                        ),
                    },
                    "cooldown_seconds": {
                        "type": "integer",
                        "description": "Minimum gap between fires (default 300 = 5 min)",
                    },
                    "one_shot": {
                        "type": "boolean",
                        "description": "If true, delete after first fire",
                    },
                },
                "required": ["label", "conditions", "on_match"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_process_watches",
            "description": "List all registered process watches and their status.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_process_watch",
            "description": "Remove a watch by id (returned by add_process_watch).",
            "parameters": {
                "type": "object",
                "properties": {
                    "watch_id": {"type": "string"},
                },
                "required": ["watch_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_process_watch_enabled",
            "description": (
                "Pause or resume a watch without removing it. Useful for "
                "temporarily quiet periods (maintenance windows etc)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "watch_id": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                "required": ["watch_id", "enabled"],
            },
        },
    },
]


PROCESS_WATCHER_TOOL_HANDLERS: dict[str, Any] = {
    "add_process_watch": _exec_add_process_watch,
    "list_process_watches": _exec_list_process_watches,
    "remove_process_watch": _exec_remove_process_watch,
    "set_process_watch_enabled": _exec_set_watch_enabled,
}
