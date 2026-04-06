"""Lightweight initiative queue — bridges inner voice thoughts to heartbeat actions.

When inner voice detects an initiative ("I should check on X", "worth revisiting Y"),
it pushes to this queue. Heartbeat can then see pending initiatives and decide to act.

Design constraints:
- In-memory, bounded (max 5 initiatives)
- Auto-expire after 30 minutes
- Observable in Mission Control
- No LLM, no persistence beyond process lifetime
- Thread-safe
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus

_MAX_QUEUE_SIZE = 5
_EXPIRE_MINUTES = 30
_QUEUE_LOCK = threading.Lock()


@dataclass
class Initiative:
    """A detected initiative from inner voice or other source."""
    initiative_id: str
    focus: str
    source: str          # "inner-voice", "witness", "dream", etc.
    source_id: str       # ID of the source record
    detected_at: str
    status: str          # "pending" | "acted" | "expired"
    acted_at: str = ""
    action_summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "initiative_id": self.initiative_id,
            "focus": self.focus,
            "source": self.source,
            "source_id": self.source_id,
            "detected_at": self.detected_at,
            "status": self.status,
            "acted_at": self.acted_at,
            "action_summary": self.action_summary,
        }


# Module-level queue
_initiatives: list[Initiative] = []


def push_initiative(
    *,
    focus: str,
    source: str = "inner-voice",
    source_id: str = "",
) -> str:
    """Push a new initiative to the queue. Returns the initiative_id."""
    now = datetime.now(UTC)
    initiative_id = f"init-{uuid4().hex[:10]}"

    initiative = Initiative(
        initiative_id=initiative_id,
        focus=focus[:200],
        source=source,
        source_id=source_id,
        detected_at=now.isoformat(),
        status="pending",
    )

    with _QUEUE_LOCK:
        _expire_stale(now)
        _initiatives.append(initiative)
        # Trim to max size (drop oldest pending)
        while len(_initiatives) > _MAX_QUEUE_SIZE:
            # Remove oldest pending, or oldest overall
            oldest_pending = next(
                (i for i in _initiatives if i.status == "pending"),
                _initiatives[0],
            )
            _initiatives.remove(oldest_pending)

    event_bus.publish(
        "heartbeat.initiative_pushed",
        {
            "initiative_id": initiative_id,
            "focus": focus[:100],
            "source": source,
            "queue_size": len(_initiatives),
        },
    )

    return initiative_id


def get_pending_initiatives() -> list[dict[str, object]]:
    """Return all pending (non-expired, non-acted) initiatives."""
    now = datetime.now(UTC)
    with _QUEUE_LOCK:
        _expire_stale(now)
        return [
            i.to_dict() for i in _initiatives
            if i.status == "pending"
        ]


def mark_acted(
    initiative_id: str,
    *,
    action_summary: str = "",
) -> bool:
    """Mark an initiative as acted upon. Returns True if found."""
    now = datetime.now(UTC).isoformat()
    with _QUEUE_LOCK:
        for i in _initiatives:
            if i.initiative_id == initiative_id and i.status == "pending":
                i.status = "acted"
                i.acted_at = now
                i.action_summary = action_summary[:200]
                event_bus.publish(
                    "heartbeat.initiative_acted",
                    {
                        "initiative_id": initiative_id,
                        "focus": i.focus[:100],
                        "action_summary": action_summary[:100],
                    },
                )
                return True
    return False


def get_initiative_queue_state() -> dict[str, object]:
    """Return full queue state for MC observability."""
    now = datetime.now(UTC)
    with _QUEUE_LOCK:
        _expire_stale(now)
        all_items = [i.to_dict() for i in _initiatives]
        pending = [i for i in all_items if i["status"] == "pending"]
        acted = [i for i in all_items if i["status"] == "acted"]
        expired = [i for i in all_items if i["status"] == "expired"]

    return {
        "queue_size": len(all_items),
        "pending_count": len(pending),
        "acted_count": len(acted),
        "expired_count": len(expired),
        "pending": pending,
        "recent_acted": acted[-3:],
        "max_queue_size": _MAX_QUEUE_SIZE,
        "expire_minutes": _EXPIRE_MINUTES,
    }


def _expire_stale(now: datetime) -> None:
    """Expire initiatives older than _EXPIRE_MINUTES. Must hold _QUEUE_LOCK."""
    cutoff = now - timedelta(minutes=_EXPIRE_MINUTES)
    for i in _initiatives:
        if i.status == "pending":
            try:
                detected = datetime.fromisoformat(i.detected_at)
                if detected < cutoff:
                    i.status = "expired"
            except (ValueError, TypeError):
                pass
