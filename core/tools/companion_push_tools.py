"""Tool: send_push_notification — proaktiv push til brugerens companion (mobil/desktop).

Bygger paa device-awareness-routingen (proactive_router): pushen rutes til den
enhed brugeren er ved, med eskalering. Gaar KUN til den bruger Jarvis betjener nu.
"""
from __future__ import annotations

from typing import Any

COMPANION_PUSH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "send_push_notification",
            "description": (
                "Send a push notification to the user's OWN companion app (mobile + "
                "desktop). Device-aware routing picks whichever device they are at and "
                "escalates if unseen. Use to proactively reach the user when they are "
                "away from the chat — a reminder, a heads-up, or 'this is done'. It goes "
                "only to the user you are currently serving, never to anyone else."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The notification text shown on the device (keep it short — ~140 chars).",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional title (default 'Jarvis').",
                    },
                },
                "required": ["message"],
            },
        },
    },
]


def _exec_send_push_notification(args: dict[str, Any]) -> dict[str, Any]:
    message = str(args.get("message") or "").strip()
    if not message:
        return {"status": "error", "error": "message is required"}
    title = str(args.get("title") or "Jarvis").strip()
    try:
        from core.identity.workspace_context import current_user_id
        uid = current_user_id() or ""
    except Exception:
        uid = ""
    if not uid:
        return {"status": "error", "error": "no current user to push to"}
    try:
        from core.services.push_dispatcher import send_companion_push
        ok = send_companion_push(uid, message, title)
    except Exception as e:
        return {"status": "error", "error": f"push failed: {e}"}
    if not ok:
        return {"status": "error", "error": "could not send push"}
    return {"status": "ok", "text": f"Push sendt til din companion: {message[:60]}"}
