"""Lightweight initiative queue — bridges inner voice thoughts to heartbeat actions.

When inner voice detects an initiative ("I should check on X", "worth revisiting Y"),
it pushes to this queue. Heartbeat can then see pending initiatives and decide to act.

Design constraints:
- In-memory, bounded
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

_MAX_QUEUE_SIZE = 8
_EXPIRE_MINUTES = 90
_RETRY_DELAY_MINUTES = 10
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
    priority: str = "medium"
    attempt_count: int = 0
    last_attempt_at: str = ""
    next_attempt_at: str = ""
    blocked_reason: str = ""
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
            "priority": self.priority,
            "attempt_count": self.attempt_count,
            "last_attempt_at": self.last_attempt_at,
            "next_attempt_at": self.next_attempt_at,
            "blocked_reason": self.blocked_reason,
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
    priority: str = "medium",
) -> str:
    """Push a new initiative to the queue. Returns the initiative_id."""
    now = datetime.now(UTC)
    initiative_id = f"init-{uuid4().hex[:10]}"
    normalized_focus = focus[:200].strip()
    normalized_priority = (
        priority.strip().lower() if priority.strip().lower() in {"low", "medium", "high"} else "medium"
    )

    initiative = Initiative(
        initiative_id=initiative_id,
        focus=normalized_focus,
        source=source,
        source_id=source_id,
        detected_at=now.isoformat(),
        status="pending",
        priority=normalized_priority,
        next_attempt_at=now.isoformat(),
    )

    with _QUEUE_LOCK:
        _expire_stale(now)
        for existing in reversed(_initiatives):
            if (
                existing.status == "pending"
                and existing.focus.lower() == normalized_focus.lower()
            ):
                existing.detected_at = now.isoformat()
                existing.next_attempt_at = now.isoformat()
                if normalized_priority == "high" or existing.priority != "high":
                    existing.priority = normalized_priority
                return existing.initiative_id
        _initiatives.append(initiative)
        # Trim to max size (drop stalest pending first)
        while len(_initiatives) > _MAX_QUEUE_SIZE:
            pending = [item for item in _initiatives if item.status == "pending"]
            removable = pending[0] if pending else _initiatives[0]
            _initiatives.remove(removable)

    event_bus.publish(
        "heartbeat.initiative_pushed",
        {
            "initiative_id": initiative_id,
            "focus": normalized_focus[:100],
            "source": source,
            "priority": normalized_priority,
            "queue_size": len(_initiatives),
        },
    )

    return initiative_id


def get_pending_initiatives() -> list[dict[str, object]]:
    """Return all pending (non-expired, non-acted) initiatives."""
    now = datetime.now(UTC)
    with _QUEUE_LOCK:
        _expire_stale(now)
        due_items = [
            i for i in _initiatives
            if i.status == "pending" and _initiative_due(i, now)
        ]
        due_items.sort(key=_initiative_sort_key)
        return [i.to_dict() for i in due_items]


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
                i.next_attempt_at = ""
                i.blocked_reason = ""
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


def mark_attempted(
    initiative_id: str,
    *,
    blocked_reason: str = "",
    retry_delay_minutes: int = _RETRY_DELAY_MINUTES,
    action_summary: str = "",
) -> bool:
    """Record a bounded attempt and schedule a retry if still pending."""
    now = datetime.now(UTC)
    retry_at = now + timedelta(minutes=max(retry_delay_minutes, 1))
    with _QUEUE_LOCK:
        for i in _initiatives:
            if i.initiative_id != initiative_id or i.status != "pending":
                continue
            i.attempt_count += 1
            i.last_attempt_at = now.isoformat()
            i.next_attempt_at = retry_at.isoformat()
            i.blocked_reason = blocked_reason[:120]
            if action_summary:
                i.action_summary = action_summary[:200]
            event_bus.publish(
                "heartbeat.initiative_attempted",
                {
                    "initiative_id": initiative_id,
                    "focus": i.focus[:100],
                    "attempt_count": i.attempt_count,
                    "blocked_reason": i.blocked_reason,
                    "next_attempt_at": i.next_attempt_at,
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
        "retry_delay_minutes": _RETRY_DELAY_MINUTES,
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


def _initiative_due(initiative: Initiative, now: datetime) -> bool:
    next_attempt = str(initiative.next_attempt_at or "").strip()
    if not next_attempt:
        return True
    try:
        due_at = datetime.fromisoformat(next_attempt)
    except ValueError:
        return True
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)
    return due_at <= now


def _initiative_sort_key(initiative: Initiative) -> tuple[int, int, str]:
    priority_rank = {"high": 0, "medium": 1, "low": 2}.get(initiative.priority, 1)
    return (
        priority_rank,
        initiative.attempt_count,
        initiative.detected_at,
    )
