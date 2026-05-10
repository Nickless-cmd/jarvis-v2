"""Nudge-brønd tools — Jarvis inspicerer, sender og afviser nudges.

Disse værktøjer giver Jarvis (den synlige instans) kontrol over hvad der
sendes proaktivt. I stedet for at daemons fyrer beskeder af automatisk,
afleverer de nudges i brønden — og Jarvis vælger selv.
"""
from __future__ import annotations

from typing import Any


def _exec_nudge_inspect(args: dict[str, Any]) -> dict[str, Any]:
    """Vis pending nudges."""
    try:
        from core.services.nudge_broend import list_pending, count_pending
    except Exception as exc:
        return {"status": "error", "error": f"nudge_broend not available: {exc}"}

    limit = int(args.get("limit") or 10)
    pending = list_pending(limit=limit)
    total = count_pending()

    return {
        "status": "ok",
        "pending_count": total,
        "nudges": pending,
        "text": f"{len(pending)} vist (ud af {total} pending)" if pending else "Brønden er tom — ingen ventende nudges.",
    }


def _exec_nudge_send(args: dict[str, Any]) -> dict[str, Any]:
    """Send en nudge via notify_user (webchat/Discord)."""
    nudge_id = str(args.get("nudge_id") or "").strip()
    if not nudge_id:
        return {"status": "error", "error": "nudge_id er påkrævet"}

    try:
        from core.services.nudge_broend import get, mark_sent
    except Exception as exc:
        return {"status": "error", "error": f"nudge_broend not available: {exc}"}

    nudge = get(nudge_id)
    if nudge is None:
        return {"status": "error", "error": f"Nudge '{nudge_id}' ikke fundet"}
    if nudge.get("status") != "pending":
        return {"status": "error", "error": f"Nudge er allerede {nudge.get('status')}"}

    message = str(nudge.get("message", ""))
    importance = str(nudge.get("importance", "normal"))

    # Send via notify_user tool
    try:
        from core.tools.simple_tools import _exec_notify_user
        channel = "discord"  # Default to Discord for nudge-send
        result = _exec_notify_user({
            "content": message,
            "channel": channel,
        })
    except Exception as exc:
        return {"status": "error", "error": f"send failed: {exc}"}

    if result.get("status") == "ok":
        mark_sent(nudge_id)
        return {
            "status": "ok",
            "nudge_id": nudge_id,
            "channel": channel,
            "text": f"Nudge sendt: {message[:120]}",
        }
    else:
        return {
            "status": "error",
            "error": result.get("error", "send failed"),
            "nudge_id": nudge_id,
            "text": f"Kunne ikke sende nudge: {result.get('error')}",
        }


def _exec_nudge_dismiss(args: dict[str, Any]) -> dict[str, Any]:
    """Afvis ét eller alle nudges."""
    try:
        from core.services.nudge_broend import mark_dismissed, dismiss_all
    except Exception as exc:
        return {"status": "error", "error": f"nudge_broend not available: {exc}"}

    nudge_id = str(args.get("nudge_id") or "").strip()
    reason = str(args.get("reason") or "").strip()

    if nudge_id == "all":
        count = dismiss_all(reason=reason or "dismissed-all")
        return {"status": "ok", "dismissed": count, "text": f"Alle {count} nudges afvist."}

    if not nudge_id:
        return {"status": "error", "error": "nudge_id er påkrævet (eller 'all' for alle)"}

    ok = mark_dismissed(nudge_id, reason=reason)
    if ok:
        return {"status": "ok", "dismissed": nudge_id, "text": f"Nudge {nudge_id} afvist."}
    else:
        return {"status": "error", "error": f"Nudge '{nudge_id}' ikke fundet eller allerede håndteret"}


NUDGE_BROEND_TOOL_HANDLERS: dict[str, Any] = {
    "nudge_inspect": _exec_nudge_inspect,
    "nudge_send": _exec_nudge_send,
    "nudge_dismiss": _exec_nudge_dismiss,
}


NUDGE_BROEND_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "nudge_inspect",
            "description": (
                "Inspicer nudge-brønden — se pending beskeder fra daemons og "
                "systemhændelser der venter på din dømmekraft. Brug denne til at "
                "se hvad der er sket i baggrunden og beslut hvad der er værd at dele."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Antal nudges at vise (default 10)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nudge_send",
            "description": (
                "Send en pending nudge til brugeren. Efter inspektion af brønden, "
                "brug denne til at sende de nudges du vurderer er værd at dele. "
                "Sender via notify_user til webchat/Discord."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nudge_id": {
                        "type": "string",
                        "description": "ID på nudgen der skal sendes (fra nudge_inspect)",
                    },
                },
                "required": ["nudge_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nudge_dismiss",
            "description": (
                "Afvis en pending nudge (eller alle med 'all'). Brug når en nudge "
                "ikke er relevant eller vigtig nok til at dele."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nudge_id": {
                        "type": "string",
                        "description": "ID på nudgen der skal afvises, eller 'all' for alle",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Valgfri begrundelse for afvisning",
                    },
                },
                "required": ["nudge_id"],
            },
        },
    },
]
