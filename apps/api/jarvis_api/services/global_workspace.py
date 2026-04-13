"""Global Workspace — shared broadcast buffer (Experiment 3: Global Workspace Theory).

Theoretical basis: Baars — consciousness arises when information is broadcast
to the whole system. This module maintains an in-memory sliding buffer of recent
significant signals from all daemons, populated via eventbus subscription.

Public API:
- publish_to_workspace(source, topic, signal_type, payload_summary)
- get_workspace_snapshot() -> list[dict]
- register_event_listeners() / stop_event_listeners()
"""
from __future__ import annotations

import logging
import queue
import threading
from collections import deque
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_MAX_BUFFER = 50
_workspace: deque[dict[str, Any]] = deque(maxlen=_MAX_BUFFER)
_lock = threading.Lock()

_listener_thread: threading.Thread | None = None
_listener_running: bool = False

# Eventbus event → source name mapping
_EVENT_SOURCE_MAP: dict[str, str] = {
    "cognitive_surprise.noted": "surprise_daemon",
    "cognitive_personality.vector_updated": "personality_vector",
    "cognitive_experiential.memory_created": "experiential_memory",
    "tool.error": "tool_pipeline",
    "tool.success": "tool_pipeline",
    "experiment.recurrence_loop.tick": "recurrence_loop",
    "workspace.broadcast": "broadcast_daemon",
}

# inner_voice events use prefix matching
_INNER_VOICE_PREFIXES = ("cognitive_inner_voice.", "inner_voice.")


def publish_to_workspace(
    source: str,
    topic: str,
    signal_type: str,
    payload_summary: str,
) -> None:
    """Add an entry to the shared workspace buffer."""
    entry = {
        "source": source,
        "topic": topic,
        "signal_type": signal_type,
        "payload_summary": payload_summary[:200],
        "timestamp": datetime.now(UTC).isoformat(),
    }
    with _lock:
        _workspace.append(entry)


def get_workspace_snapshot() -> list[dict[str, Any]]:
    """Return current workspace buffer as a list (newest last)."""
    with _lock:
        return list(_workspace)


def _extract_topic(event_kind: str, payload: dict[str, Any]) -> str:
    """Extract a short topic string from an event payload."""
    for field in ("phrase", "topic", "narrative", "summary", "text", "detail"):
        val = str(payload.get(field) or "")
        if val:
            words = [w.strip(".,!?;:()") for w in val.split() if len(w) > 3][:4]
            if words:
                return " ".join(words)[:60]
    return event_kind.split(".")[-1].replace("_", " ")


def _topic_jaccard(topic_a: str, topic_b: str) -> float:
    """Jaccard similarity between two topic strings (word-level)."""
    words_a = set(w.lower() for w in topic_a.split() if len(w) > 3)
    words_b = set(w.lower() for w in topic_b.split() if len(w) > 3)
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _handle_event(kind: str, payload: dict[str, Any]) -> None:
    """Map eventbus event to workspace entry."""
    source = _EVENT_SOURCE_MAP.get(kind, "")
    if not source:
        if any(kind.startswith(p) for p in _INNER_VOICE_PREFIXES):
            source = "inner_voice_daemon"
        else:
            return  # unknown event, skip
    topic = _extract_topic(kind, payload)
    payload_summary = str(payload)[:150]
    publish_to_workspace(source, topic, kind, payload_summary)


def _listener_loop(q: "queue.Queue[dict[str, Any] | None]") -> None:
    global _listener_running
    while _listener_running:
        try:
            item = q.get(timeout=2.0)
            if item is None:
                break
            kind = str(item.get("kind") or "")
            payload = dict(item.get("payload") or {})
            _handle_event(kind, payload)
        except queue.Empty:
            continue
        except Exception as exc:
            logger.debug("global_workspace: listener error: %s", exc)


def register_event_listeners() -> None:
    """Start background eventbus listener thread."""
    global _listener_thread, _listener_running
    if _listener_thread and _listener_thread.is_alive():
        return
    try:
        from core.eventbus.bus import event_bus
        q = event_bus.subscribe()
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop,
            args=(q,),
            daemon=True,
            name="global-workspace-listener",
        )
        _listener_thread.start()
        logger.info("global_workspace: event listener started")
    except Exception as exc:
        logger.warning("global_workspace: failed to start listener: %s", exc)


def stop_event_listeners() -> None:
    """Stop the background listener thread."""
    global _listener_running
    _listener_running = False
