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
            insert_approval_feedback(
                recorded_at=str(
                    payload.get("resolved_at")
                    or item.get("created_at")
                    or ""
                ),
                intent_key=str(payload.get("intent_key") or ""),
                approval_state=str(payload.get("approval_state") or ""),
                approval_source=str(payload.get("approval_source") or ""),
                tool_name=str(payload.get("tool_name") or ""),
                resolution_reason=str(payload.get("resolution_reason") or ""),
                resolution_message=str(payload.get("resolution_message") or ""),
                session_id=str(payload.get("session_id") or ""),
            )
        except Exception as exc:
            logger.warning("approval_feedback_subscriber: failed to persist event: %s", exc)
