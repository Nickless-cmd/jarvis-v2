"""Native tools til notifikations-præferencer (notif-routing spec §4).

Lader Jarvis (og via app-UI'et) sætte HVOR proaktive notifikationer lander —
globalt eller per-type — + quiet hours. Tynde exec-wrappers oven på
core.services.notification_router.
"""
from __future__ import annotations

from typing import Any


def _uid(args: dict[str, Any]) -> str:
    uid = str(args.get("_user_id") or args.get("_runtime_user_id") or "").strip()
    if uid:
        return uid
    try:
        from core.identity.workspace_context import current_user_id
        return current_user_id() or ""
    except Exception:
        return ""


def exec_get_notification_preferences(args: dict[str, Any]) -> dict[str, Any]:
    uid = _uid(args)
    if not uid:
        return {"status": "error", "error": "ingen bruger-kontekst"}
    from core.services.notification_router import get_preferences
    p = get_preferences(uid)
    return {"status": "ok", "preferences": p,
            "text": (f"Notifikationer: global={p['global']}, quiet {p['quiet_start']}–{p['quiet_end']}. "
                     f"Overrides: " + ", ".join(f"{k}={p[k]}" for k in
                     ("briefing", "reminder", "reach_out", "team_invite", "wakeup") if p.get(k)) or
                     f"global={p['global']}, ingen per-type-overrides.")}


def exec_set_notification_preferences(args: dict[str, Any]) -> dict[str, Any]:
    """Args (alle valgfri): global, briefing, reminder, reach_out, team_invite,
    wakeup (kanal=auto|mobile|desktop|push|discord|telegram), quiet_start, quiet_end (HH:MM)."""
    uid = _uid(args)
    if not uid:
        return {"status": "error", "error": "ingen bruger-kontekst"}
    from core.services.notification_router import set_preferences
    kwargs = {k: args[k] for k in
              ("global", "briefing", "reminder", "reach_out", "team_invite", "wakeup",
               "quiet_start", "quiet_end") if k in args and args[k] is not None}
    if not kwargs:
        return {"status": "error", "error": "ingen felter at sætte"}
    try:
        p = set_preferences(uid, **kwargs)
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    return {"status": "ok", "preferences": p, "text": "Notifikations-præferencer opdateret."}


NOTIFICATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_notification_preferences",
            "description": "Read where your proactive notifications currently land (per-type + quiet hours).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_notification_preferences",
            "description": ("Choose where proactive notifications land — globally or per type "
                            "(briefing, reminder, reach_out, team_invite, wakeup). Channels: "
                            "auto, mobile, desktop, push, discord, telegram. Also set quiet hours."),
            "parameters": {
                "type": "object",
                "properties": {
                    "global": {"type": "string", "enum": ["auto", "mobile", "desktop", "push", "discord", "telegram"]},
                    "briefing": {"type": "string", "enum": ["auto", "mobile", "desktop", "push", "discord", "telegram"]},
                    "reminder": {"type": "string", "enum": ["auto", "mobile", "desktop", "push", "discord", "telegram"]},
                    "reach_out": {"type": "string", "enum": ["auto", "mobile", "desktop", "push", "discord", "telegram"]},
                    "team_invite": {"type": "string", "enum": ["auto", "mobile", "desktop", "push", "discord", "telegram"]},
                    "wakeup": {"type": "string", "enum": ["auto", "mobile", "desktop", "push", "discord", "telegram"]},
                    "quiet_start": {"type": "string", "description": "HH:MM"},
                    "quiet_end": {"type": "string", "description": "HH:MM"},
                },
            },
        },
    },
]
