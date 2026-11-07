from __future__ import annotations

import logging
import queue
import threading
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import insert_approval_feedback

logger = logging.getLogger(__name__)

_SUBSCRIBER_THREAD: threading.Thread | None = None
_SUBSCRIBER_STOP = threading.Event()
_SUBSCRIBER_QUEUE: queue.Queue[dict[str, Any] | None] | None = None
_SUPPORTED_KIND = "approvals.tool_intent_resolved"


def start_approval_feedback_subscriber() -> None:
    global _SUBSCRIBER_THREAD, _SUBSCRIBER_QUEUE
    if _SUBSCRIBER_THREAD and _SUBSCRIBER_THREAD.is_alive():
        return
    _SUBSCRIBER_STOP.clear()
    subscriber = event_bus.subscribe()
    _SUBSCRIBER_QUEUE = subscriber
    thread = threading.Thread(
        target=_subscriber_loop,
        kwargs={"subscriber": subscriber},
        name="jarvis-approval-feedback-subscriber",
        daemon=True,
    )
    thread.start()
    _SUBSCRIBER_THREAD = thread


def stop_approval_feedback_subscriber() -> None:
    global _SUBSCRIBER_THREAD, _SUBSCRIBER_QUEUE
    _SUBSCRIBER_STOP.set()
    subscriber = _SUBSCRIBER_QUEUE
    if subscriber is not None:
        event_bus.unsubscribe(subscriber)
    thread = _SUBSCRIBER_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=1.0)
    _SUBSCRIBER_THREAD = None
    _SUBSCRIBER_QUEUE = None


def _subscriber_loop(*, subscriber: queue.Queue[dict[str, Any] | None]) -> None:
    while not _SUBSCRIBER_STOP.is_set():
        try:
            item = subscriber.get(timeout=0.5)
        except queue.Empty:
            continue
        if item is None:
            break
        if str(item.get("kind") or "") != _SUPPORTED_KIND:
            continue
        try:
            payload = dict(item.get("payload") or {})
            approval_state = str(payload.get("approval_state") or "")
            intent_key = str(payload.get("intent_key") or "")
            insert_approval_feedback(
                recorded_at=str(
                    payload.get("resolved_at")
                    or item.get("created_at")
                    or ""
                ),
                intent_key=intent_key,
                approval_state=approval_state,
                approval_source=str(payload.get("approval_source") or ""),
                tool_name=str(payload.get("tool_name") or ""),
                resolution_reason=str(payload.get("resolution_reason") or ""),
                resolution_message=str(payload.get("resolution_message") or ""),
                session_id=str(payload.get("session_id") or ""),
            )
            # emotion-trigger: warmth on approved, doubt on rejected
            try:
                from core.services.emotion_concepts import trigger_emotion_concept
                if approval_state == "approved":
                    trigger_emotion_concept(
                        "warmth", intensity=0.3,
                        trigger=f"approval-approved-{intent_key[:24]}",
                        source="approval_feedback",
                    )
                elif approval_state == "rejected":
                    trigger_emotion_concept(
                        "doubt", intensity=0.2,
                        trigger=f"approval-rejected-{intent_key[:24]}",
                        source="approval_feedback",
                    )
            except Exception:
                pass
        except Exception as exc:
            logger.warning("approval_feedback_subscriber: failed to persist event: %s", exc)


def build_approval_feedback_subscriber_surface() -> dict[str, Any]:
    """Mission Control-surface: hvad svarede brugeren, og lytter abonnenten?

    Tallene kommer fra ``approval_feedback_log`` — det abonnenten selv skriver.
    ``subscriber_alive`` gælder KUN den proces surface'en kaldes i.
    """
    base = {"mode": "approval-feedback-subscriber"}
    alive = bool(_SUBSCRIBER_THREAD and _SUBSCRIBER_THREAD.is_alive())
    try:
        from core.runtime.db import connect

        with connect() as conn:
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                            "AND name='approval_feedback_log'").fetchone() is None:
                return {**base, "active": False, "signals": {"subscriber_alive": alive},
                        "reason": "tabellen approval_feedback_log findes ikke endnu",
                        "summary": "intet brugersvar logget"}
            total, last_at, sessions = conn.execute(
                "SELECT COUNT(*), MAX(recorded_at), COUNT(DISTINCT session_id) "
                "FROM approval_feedback_log").fetchone()
            by_state = conn.execute(
                "SELECT approval_state, COUNT(*) FROM approval_feedback_log "
                "GROUP BY approval_state ORDER BY COUNT(*) DESC, approval_state").fetchall()
            by_source = conn.execute(
                "SELECT approval_source, COUNT(*) FROM approval_feedback_log "
                "GROUP BY approval_source ORDER BY COUNT(*) DESC, approval_source").fetchall()
            tools = conn.execute(
                "SELECT tool_name, COUNT(*) FROM approval_feedback_log WHERE tool_name != '' "
                "GROUP BY tool_name ORDER BY COUNT(*) DESC, tool_name LIMIT 5").fetchall()
    except Exception as exc:  # surface skal melde årsagen, ikke kaste ind i MC
        return {**base, "active": False, "signals": {"subscriber_alive": alive},
                "reason": f"approval_feedback_log kunne ikke læses: {type(exc).__name__}: {exc}"[:300],
                "summary": "feedback-log ulæselig"}
    total = int(total or 0)
    if not total:
        return {**base, "active": False, "signals": {"total": 0, "subscriber_alive": alive},
                "reason": "approval_feedback_log er tom", "summary": "intet brugersvar logget"}
    return {
        "active": True, **base,
        "signals": {
            "total": total, "sessions": int(sessions or 0), "last_recorded_at": last_at,
            "by_state": {str(k): int(n) for k, n in by_state},
            "by_source": {str(k): int(n) for k, n in by_source},
            "top_tools": [{"tool": str(t), "count": int(n)} for t, n in tools],
            "subscriber_alive": alive,
        },
        "summary": (f"{total} brugersvar ({', '.join(f'{k} {n}' for k, n in by_state)}); "
                    f"seneste {last_at or 'aldrig'}"),
    }
