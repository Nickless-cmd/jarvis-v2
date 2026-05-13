"""Tools Jarvis uses to surface or dismiss pending nudges.

Nudges land in outbound_nudges via push_nudge() from daemons. They appear
in Jarvis' awareness as pending. He uses these tools to:
  - surface_nudge(nudge_id): actually send the daemon's message to the user
    (he can rewrite it with full context in his reply)
  - dismiss_nudge(nudge_id, reason): explicit skip — won't reappear
  - list_pending_nudges(): re-read pending if he wants to inspect deeper

The "send" path is delegated: surfacing means marking sent; Jarvis composes
his own message in the visible chat reply. We don't auto-send the daemon's
text — that's what caused the spejlsal-bug in the first place.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _exec_list_pending_nudges(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from core.services.outbound_nudges import list_pending
        limit = int(args.get("limit") or 10)
        return {"status": "ok", "nudges": list_pending(limit=limit)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_surface_nudge(args: dict[str, Any]) -> dict[str, Any]:
    nudge_id = str(args.get("nudge_id") or "").strip()
    if not nudge_id:
        return {"status": "rejected", "reason": "nudge_id required"}
    try:
        from core.services.outbound_nudges import mark_sent
        ok = mark_sent(nudge_id)
        return {"status": "ok" if ok else "not-found", "nudge_id": nudge_id}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_dismiss_nudge(args: dict[str, Any]) -> dict[str, Any]:
    nudge_id = str(args.get("nudge_id") or "").strip()
    if not nudge_id:
        return {"status": "rejected", "reason": "nudge_id required"}
    try:
        from core.services.outbound_nudges import mark_dismissed
        ok = mark_dismissed(nudge_id)
        return {"status": "ok" if ok else "not-found", "nudge_id": nudge_id}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


NUDGE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_pending_nudges",
            "description": (
                "List pending outbound nudges from daemons (heartbeat, "
                "outreach, inner_voice, boredom). Each has nudge_id, "
                "source, kind, message, importance. Use surface_nudge or "
                "dismiss_nudge based on whether the message belongs in "
                "the current conversation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Default 10."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "surface_nudge",
            "description": (
                "Mark a pending nudge as surfaced — you'll then compose "
                "your own message to the user that incorporates the "
                "nudge's content with full conversational context. "
                "Pattern: read the nudge, then write your visible reply "
                "that brings it up naturally. Don't repeat the nudge text "
                "verbatim — make it yours."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nudge_id": {"type": "string"},
                },
                "required": ["nudge_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dismiss_nudge",
            "description": (
                "Skip a pending nudge — won't reappear in awareness. Use "
                "when the daemon's signal isn't worth surfacing right now."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nudge_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["nudge_id"],
            },
        },
    },
]

NUDGE_TOOL_HANDLERS: dict[str, Any] = {
    "list_pending_nudges": _exec_list_pending_nudges,
    "surface_nudge": _exec_surface_nudge,
    "dismiss_nudge": _exec_dismiss_nudge,
}
