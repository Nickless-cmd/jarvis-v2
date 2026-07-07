"""JarvisX channels + scheduling state route group.

Aggregated gateway status for the Channels view and scheduled/recurring/
wakeup state for the Scheduling view. Extracted from routes/jarvisx.py.

Behavior-preserving: pure code movement, no logic changes.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from apps.api.jarvis_api.routes.jarvisx_common import logger

router = APIRouter(prefix="/api", tags=["jarvisx"])


@router.get("/channels/state")
def channels_state() -> dict[str, Any]:
    """Aggregate gateway status for the Channels view.

    Pulls live in-memory status from each gateway module (Discord +
    Telegram) plus the runtime KV mirror so we get the same truth even
    when read from a different worker process.
    """
    out: dict[str, Any] = {"channels": []}
    # Discord — read from runtime_state_kv mirror so we get the runtime
    # worker's truth even when the API worker handles the request.
    try:
        from core.runtime.db import get_runtime_state_value
        from core.services.discord_config import is_discord_configured
        kv = get_runtime_state_value("discord_gateway.status") or {}
        if isinstance(kv, str):
            import json as _json
            try:
                kv = _json.loads(kv)
            except Exception:
                kv = {}
        out["channels"].append({
            "id": "discord",
            "label": "Discord",
            "configured": is_discord_configured(),
            "connected": bool(kv.get("connected")),
            "last_message_at": kv.get("last_message_at"),
            "message_count": kv.get("message_count", 0),
            "guild_name": kv.get("guild_name"),
            "error": kv.get("connect_error"),
        })
    except Exception as exc:
        logger.debug("channels_state: discord read failed: %s", exc)
        out["channels"].append({
            "id": "discord", "label": "Discord", "configured": False,
            "connected": False, "error": str(exc),
        })
    # Telegram
    try:
        from core.services.telegram_gateway import get_status as tg_status, is_configured as tg_configured
        s = tg_status()
        out["channels"].append({
            "id": "telegram",
            "label": "Telegram",
            "configured": tg_configured(),
            "connected": bool(s.get("connected")),
            "last_message_at": s.get("last_message_at"),
            "message_count": s.get("message_count", 0),
            "active_sessions": s.get("active_sessions", 0),
            "error": s.get("error"),
        })
    except Exception as exc:
        logger.debug("channels_state: telegram read failed: %s", exc)
        out["channels"].append({
            "id": "telegram", "label": "Telegram", "configured": False,
            "connected": False, "error": str(exc),
        })
    # Webchat (always present — it's the API itself)
    try:
        from core.services.chat_sessions import list_chat_sessions
        sessions = list_chat_sessions() or []
        out["channels"].append({
            "id": "webchat",
            "label": "Webchat",
            "configured": True,
            "connected": True,
            "session_count": len(sessions),
            "last_message_at": (
                sessions[0].get("updated_at") if sessions else None
            ),
        })
    except Exception as exc:
        logger.debug("channels_state: webchat read failed: %s", exc)
    return out


_SCHEDULING_USER_KEYS = (
    "user_id",
    "for_user_id",
    "scheduled_for_user_id",
    "owner_user_id",
)


def _scheduling_visible_to(item: object, user_id: str) -> bool:
    """True if `item` should be shown to a user with this id.

    An item is considered visible when:
      - it isn't a mapping (treat as global, surface it)
      - none of the recognized user-id keys are present (global)
      - any recognized key matches `user_id` exactly
    Owners bypass this filter entirely at the call site.
    """
    if not isinstance(item, dict):
        return True
    matched_any_key = False
    for k in _SCHEDULING_USER_KEYS:
        v = item.get(k)
        if v is None:
            continue
        matched_any_key = True
        if str(v).strip() == user_id:
            return True
    # No user-id key present at all -> treat as global (visible)
    return not matched_any_key


def _filter_scheduling_payload(payload: object, user_id: str) -> object:
    """Recursively filter dicts/lists in a scheduling-state payload."""
    if isinstance(payload, list):
        return [p for p in payload if _scheduling_visible_to(p, user_id)]
    if isinstance(payload, dict):
        return {k: _filter_scheduling_payload(v, user_id) for k, v in payload.items()}
    return payload


@router.get("/scheduling/state")
def scheduling_state() -> dict[str, Any]:
    """Aggregate scheduled tasks + recurring + self-wakeups.

    Members and guests see only entries scoped to their own user_id.
    Owners see everything (debug visibility into all users' scheduling).
    """
    out: dict[str, Any] = {}
    try:
        from core.services.scheduled_tasks import get_scheduled_tasks_state
        out["scheduled"] = get_scheduled_tasks_state()
    except Exception as exc:
        logger.debug("scheduling_state: scheduled failed: %s", exc)
        out["scheduled"] = {"error": str(exc)}
    try:
        from core.services.recurring_tasks import get_recurring_tasks_state
        out["recurring"] = get_recurring_tasks_state()
    except Exception as exc:
        logger.debug("scheduling_state: recurring failed: %s", exc)
        out["recurring"] = {"error": str(exc)}
    try:
        from core.services.self_wakeup import list_wakeups
        out["wakeups"] = {
            "pending": list_wakeups(status="pending", limit=20),
            "fired": list_wakeups(status="fired", limit=10),
            "consumed": list_wakeups(status="consumed", limit=5),
        }
    except Exception as exc:
        logger.debug("scheduling_state: wakeups failed: %s", exc)
        out["wakeups"] = {"error": str(exc)}

    # Per-user filtering. Owners bypass entirely -- they need to see
    # everything for debugging cross-user scheduling. UI gets a flag so
    # it can render an "owner view -- showing all users" badge.
    try:
        from core.identity.workspace_context import current_role, current_user_id
        role = (current_role() or "").lower()
        uid = (current_user_id() or "").strip()
    except Exception:
        role = ""
        uid = ""
    if role == "owner":
        out["scope"] = {"mode": "owner-all", "user_id": uid or None}
    elif uid:
        out = {
            k: (_filter_scheduling_payload(v, uid) if k != "scope" else v)
            for k, v in out.items()
        }
        out["scope"] = {"mode": "per-user", "user_id": uid}
    else:
        # No identity bound (legacy / dev) -- show everything but flag it.
        out["scope"] = {"mode": "unscoped", "user_id": None}
    return out
