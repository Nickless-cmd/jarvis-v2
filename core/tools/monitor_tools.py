"""Tool wrappers for pinned monitor streams (monitor_streams)."""
from __future__ import annotations

from typing import Any

from core.services.monitor_streams import (
    close_monitor,
    list_monitors,
    open_monitor,
)


def _exec_monitor_open(args: dict[str, Any]) -> dict[str, Any]:
    return open_monitor(
        session_id=args.get("session_id"),
        source=str(args.get("source") or ""),
        label=str(args.get("label") or ""),
        pattern=str(args.get("pattern") or ""),
    )


def _exec_monitor_close(args: dict[str, Any]) -> dict[str, Any]:
    mid = str(args.get("monitor_id") or "").strip()
    if not mid:
        return {"status": "error", "error": "monitor_id is required"}
    return close_monitor(mid)


def _exec_monitor_list(args: dict[str, Any]) -> dict[str, Any]:
    items = list_monitors(args.get("session_id"))
    return {"status": "ok", "monitors": items, "count": len(items)}


MONITOR_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "monitor_open",
            "description": (
                "Pin a monitor on a source. Each turn after this, any new "
                "matches will be surfaced at the top of your prompt without "
                "you having to poll. Use for 'wake me when X happens'. "
                "Source format: 'eventbus:<family>' (e.g. 'eventbus:tool') "
                "or 'file:<absolute-path>'. Optional pattern is a Python regex."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "source": {"type": "string", "description": "'eventbus:<family>' or 'file:<absolute-path>'."},
                    "label": {"type": "string", "description": "Short human label shown in the digest."},
                    "pattern": {"type": "string", "description": "Optional regex; only matching lines/events surface."},
                },
                "required": ["source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "monitor_close",
            "description": "Stop and remove a pinned monitor by id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "monitor_id": {"type": "string"},
                },
                "required": ["monitor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "monitor_list",
            "description": "List active pinned monitors for this session.",
            "parameters": {
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": [],
            },
        },
    },
]
