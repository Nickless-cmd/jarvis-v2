"""Owner-identity resolution for autonomous dispatch.

Threat model: Jarvis runs autonomous side-effects (wakeups, scheduled
reminders, heartbeat pings, proactive outreach) that can route through
chat sessions or Discord DMs. If those dispatches land in a non-owner's
session — typically a member like Mikkel who had a recent DM — the
member sees Jarvis spontaneously asking *Bjørn's* questions. That's a
privacy leak and a UX bug.

Root cause was bigger than any single dispatcher: the `pin_session`
helper in notification_bridge tracks "the most recently active session"
globally without distinguishing whose. So when Mikkel sends a DM,
his session gets pinned; the next autonomous wakeup or reminder fired
for Bjørn picks up the pin and dumps the message into Mikkel's chat.

This module centralises:
  * get_owner_discord_id()       — resolve the owner's Discord ID via
                                   discord_config and users.json
  * resolve_owner_target_session() — pick the right session for an
                                   autonomous Bjørn-event, never
                                   matching a non-owner session

Use this at every autonomous-dispatch site instead of calling
list_chat_sessions() / get_pinned_session_id() directly.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_owner_discord_id() -> str:
    """Return the owner's Discord user ID, or empty string if unknown.

    Tries discord_config first (the operational source of truth, set
    when the gateway was configured), then users.json as fallback
    (where role='owner' is the canonical record).
    """
    # Source 1: discord_config.owner_discord_id
    try:
        from core.services.discord_config import load_discord_config
        cfg = load_discord_config()
        if cfg:
            owner = str(cfg.get("owner_discord_id") or "").strip()
            if owner:
                return owner
    except Exception as exc:
        logger.debug("owner_resolver: discord_config read failed: %s", exc)

    # Source 2: users.json
    try:
        from core.identity.users import load_users
        for u in load_users():
            if getattr(u, "role", "") == "owner":
                return str(u.discord_id or "").strip()
    except Exception as exc:
        logger.debug("owner_resolver: users.json read failed: %s", exc)
    return ""


def is_owner_session(session: dict[str, Any] | None) -> bool:
    """Decide whether a session record belongs to the owner.

    Heuristics, ordered most-specific to most-permissive:
      1. session.user_id matches owner's discord_id (preferred — the
         multi-user routing layer stamps this)
      2. session.title matches the legacy "Discord DM" with no user
         suffix (pre-multi-user world; that one was always Bjørn's)
      3. session.title is "Discord DM — {owner_id}"
      4. session has any messages with the owner's user_id

    A session with no user_id and no Discord-related title falls
    through as "ambiguous" → False (refuse rather than risk leaking).
    """
    if not isinstance(session, dict):
        return False
    owner_id = get_owner_discord_id()
    if not owner_id:
        # Without a known owner we can't gate anything; refuse all
        # autonomous routing.
        return False
    # 1. session.user_id (if the schema carries it)
    sess_user_id = str(session.get("user_id") or "").strip()
    if sess_user_id and sess_user_id == owner_id:
        return True
    # 2/3. Title patterns
    title = str(session.get("title") or "").strip()
    if title == "Discord DM":
        return True  # legacy single-user title
    if title == f"Discord DM — {owner_id}":
        return True
    # 4. Inspect messages for owner-stamped user_id
    messages = session.get("messages")
    if isinstance(messages, list):
        for m in messages:
            if isinstance(m, dict):
                if str(m.get("user_id") or "").strip() == owner_id:
                    return True
    return False


def resolve_owner_target_session() -> str:
    """Find the session that an autonomous Bjørn-event should target.

    Order:
      1. Pinned session — but only if it's owner-owned
      2. Most recent owner-owned session from list_chat_sessions
      3. Empty string (caller should create a fresh session or skip)

    Never returns a member's session id. Returning empty is a
    deliberate "I refuse to dispatch into ambiguity" signal.
    """
    try:
        from core.services.notification_bridge import get_pinned_session_id
        from core.services.chat_sessions import get_chat_session, list_chat_sessions
    except Exception as exc:
        logger.warning("owner_resolver: chat-session imports failed: %s", exc)
        return ""

    owner_id = get_owner_discord_id()

    # Step 1: pinned, if owner-owned
    pinned = (get_pinned_session_id() or "").strip()
    if pinned:
        full = get_chat_session(pinned)
        if full and is_owner_session(full):
            return pinned
        # Pinned exists but isn't owner's — fall through, do NOT use it
        logger.info(
            "owner_resolver: pinned session %s is not owner-owned, "
            "ignoring for autonomous dispatch",
            pinned,
        )

    # Step 2: most recent owner-owned session.
    # list_chat_sessions accepts user_id filter (added when middleware
    # was wired). Try the filtered call first; if the implementation
    # doesn't honor the kwarg for some reason, fall back to manual
    # filtering.
    try:
        if owner_id:
            scoped = list_chat_sessions(user_id=owner_id)
        else:
            scoped = list_chat_sessions()
    except TypeError:
        scoped = list_chat_sessions()

    for s in scoped:
        sid = str((s or {}).get("id") or "").strip()
        if not sid:
            continue
        full = get_chat_session(sid)
        if not full:
            continue
        if not is_owner_session(full):
            # If the user_id filter didn't actually scope, double-check
            continue
        if any(m.get("role") == "user" for m in (full.get("messages") or [])):
            return sid

    return ""
