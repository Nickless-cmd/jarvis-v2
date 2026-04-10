"""Notification bridge — lets Jarvis push messages to the active session.

Two entry points:
  1. send_session_notification(content, source) — called directly (tool, tick, etc.)
  2. Boredom subscriber — auto-fires when boredom reaches "productive" threshold.
"""
from __future__ import annotations

import logging
import threading

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_boredom_sub: object | None = None
_boredom_thread: threading.Thread | None = None
_boredom_stop = threading.Event()

# Guard: only one boredom notification per productive episode
_last_boredom_notification_level: str = "none"

# The session currently active in the user's browser. When set, proactive
# notifications are delivered here instead of guessing from list_chat_sessions().
_pinned_session_id: str = ""


def pin_session(session_id: str) -> None:
    """Record which session the user is currently viewing. Call on every user message."""
    global _pinned_session_id
    _pinned_session_id = (session_id or "").strip()


def send_session_notification(
    content: str,
    *,
    source: str = "jarvis-notify",
) -> dict[str, object]:
    """Append a proactive message to the most recently active chat session.

    Returns a status dict. Never raises — returns error dict on failure.
    """
    from apps.api.jarvis_api.services.chat_sessions import (
        append_chat_message,
        get_chat_session,
        list_chat_sessions,
    )

    content = content.strip()
    if not content:
        return {"status": "error", "error": "empty content"}

    # Use the pinned session if set (e.g. the session currently active in the user's browser),
    # otherwise fall back to the most recently updated session that has user messages
    # (to avoid sending to autonomous-run-only sessions which the user may not be watching).
    session_id = _pinned_session_id
    if not session_id:
        sessions = list_chat_sessions()
        for s in sessions:
            sid = str((s or {}).get("id") or "").strip()
            if not sid:
                continue
            full = get_chat_session(sid)
            if full and any(m.get("role") == "user" for m in (full.get("messages") or [])):
                session_id = sid
                break
        if not session_id:
            session_id = str((sessions[0] or {}).get("id") or "").strip() if sessions else ""
    if not session_id or get_chat_session(session_id) is None:
        return {"status": "blocked", "error": "no active session"}

    try:
        message = append_chat_message(
            session_id=session_id,
            role="assistant",
            content=content,
        )
        event_bus.publish(
            "channel.chat_message_appended",
            {
                "session_id": session_id,
                "message": message,
                "source": source,
            },
        )
        logger.info("notification_bridge: delivered [%s] to session %s", source, session_id)
        return {"status": "ok", "session_id": session_id, "source": source}
    except Exception as exc:
        logger.error("notification_bridge: delivery failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}


def _boredom_listener_loop() -> None:
    """Background thread that listens for boredom_productive events."""
    global _last_boredom_notification_level
    from core.eventbus.bus import event_bus as bus
    sub = bus.subscribe()
    try:
        while not _boredom_stop.is_set():
            import queue as _q
            try:
                item = sub.get(timeout=1.0)
            except _q.Empty:
                continue
            if item is None:
                break
            kind = item.get("kind", "") if isinstance(item, dict) else ""
            if kind != "cognitive_state.boredom_productive":
                continue
            # Only notify once per productive episode (reset when level drops)
            if _last_boredom_notification_level == "productive":
                continue
            _last_boredom_notification_level = "productive"
            try:
                from apps.api.jarvis_api.services.boredom_engine import get_boredom_state
                state = get_boredom_state()
                restlessness = state.get("restlessness", 0)
                desire = state.get("desire", "")
                msg = f"[boredom] Restlessness {restlessness:.0%} — {desire}" if desire else f"[boredom] Restlessness {restlessness:.0%}"
                send_session_notification(msg, source="boredom-bridge")
            except Exception as exc:
                logger.error("notification_bridge: boredom notify failed: %s", exc)
    finally:
        bus.unsubscribe(sub)


def _reset_boredom_level_listener_loop() -> None:
    """Background thread that resets the boredom notification guard when level drops."""
    global _last_boredom_notification_level
    from core.eventbus.bus import event_bus as bus
    sub = bus.subscribe()
    try:
        while not _boredom_stop.is_set():
            import queue as _q
            try:
                item = sub.get(timeout=1.0)
            except _q.Empty:
                continue
            if item is None:
                break
            if not isinstance(item, dict):
                continue
            kind = item.get("kind", "")
            payload = item.get("payload") or {}
            if kind == "cognitive_state.boredom_productive":
                continue
            # Any heartbeat tick completion resets guard so next productive episode fires again
            if kind in ("heartbeat.tick_completed", "heartbeat.tick_blocked"):
                _last_boredom_notification_level = "none"
    finally:
        bus.unsubscribe(sub)


def start_notification_bridge() -> None:
    """Start the boredom notification listener threads."""
    global _boredom_thread, _boredom_stop
    _boredom_stop.clear()
    t = threading.Thread(target=_boredom_listener_loop, daemon=True, name="boredom-notify")
    t.start()
    _boredom_thread = t
    t2 = threading.Thread(target=_reset_boredom_level_listener_loop, daemon=True, name="boredom-reset")
    t2.start()
    logger.info("notification_bridge: started")


def stop_notification_bridge() -> None:
    """Stop the boredom notification listener."""
    _boredom_stop.set()
    logger.info("notification_bridge: stopped")
