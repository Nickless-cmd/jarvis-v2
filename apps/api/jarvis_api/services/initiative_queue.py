"""Persistent initiative queue — bridges inner voice thoughts to heartbeat actions.

When inner voice detects an initiative ("I should check on X", "worth revisiting Y"),
it pushes to this queue. Heartbeat can then see pending initiatives and decide to act.

Design constraints:
- SQLite-backed, bounded
- Observable in Mission Control
- Thread-safe
"""
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime import db as runtime_db
from core.runtime.db import approve_runtime_initiative, reject_runtime_initiative

_MAX_QUEUE_SIZE = 8
_EXPIRE_MINUTES = 90
_RETRY_DELAY_MINUTES = 10
_QUEUE_LOCK = threading.Lock()


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
    if not normalized_focus:
        normalized_focus = "Follow up on unspecified initiative"
    normalized_priority = (
        priority.strip().lower() if priority.strip().lower() in {"low", "medium", "high"} else "medium"
    )

    with _QUEUE_LOCK:
        _expire_stale(now)
        existing = runtime_db.find_pending_runtime_initiative_by_focus(normalized_focus)
        if existing:
            existing_id = str(existing.get("initiative_id") or "")
            existing_priority = str(existing.get("priority") or "medium")
            runtime_db.update_runtime_initiative(
                existing_id,
                detected_at=now.isoformat(),
                next_attempt_at=now.isoformat(),
                priority=(
                    normalized_priority
                    if normalized_priority == "high" or existing_priority != "high"
                    else existing_priority
                ),
                blocked_reason="",
                updated_at=now.isoformat(),
            )
            return existing_id
        runtime_db.create_runtime_initiative(
            initiative_id=initiative_id,
            focus=normalized_focus,
            source=source,
            source_id=source_id,
            status="pending",
            priority=normalized_priority,
            detected_at=now.isoformat(),
            next_attempt_at=now.isoformat(),
            updated_at=now.isoformat(),
        )
        _trim_pending(now)
        queue_size = len(
            runtime_db.list_runtime_initiatives(
                status="pending",
                limit=_MAX_QUEUE_SIZE + 20,
            )
        )

    event_bus.publish(
        "heartbeat.initiative_pushed",
        {
            "initiative_id": initiative_id,
            "focus": normalized_focus[:100],
            "source": source,
            "priority": normalized_priority,
            "queue_size": queue_size,
        },
    )

    return initiative_id


def get_pending_initiatives() -> list[dict[str, object]]:
    """Return all pending (non-expired, non-acted) initiatives."""
    now = datetime.now(UTC)
    with _QUEUE_LOCK:
        _expire_stale(now)
        due_items = [
            item
            for item in runtime_db.list_runtime_initiatives(
                status="pending",
                limit=_MAX_QUEUE_SIZE + 20,
            )
            if _initiative_due(item, now)
        ]
        due_items.sort(key=_initiative_sort_key)
        return due_items[:_MAX_QUEUE_SIZE]


def mark_acted(
    initiative_id: str,
    *,
    action_summary: str = "",
) -> bool:
    """Mark an initiative as acted upon. Returns True if found."""
    now = datetime.now(UTC).isoformat()
    with _QUEUE_LOCK:
        existing = runtime_db.get_runtime_initiative(initiative_id)
        if not existing or str(existing.get("status") or "") != "pending":
            return False
        runtime_db.update_runtime_initiative(
            initiative_id,
            status="acted",
            acted_at=now,
            next_attempt_at="",
            blocked_reason="",
            action_summary=action_summary[:200],
            updated_at=now,
        )
        event_bus.publish(
            "heartbeat.initiative_acted",
            {
                "initiative_id": initiative_id,
                "focus": str(existing.get("focus") or "")[:100],
                "action_summary": action_summary[:100],
            },
        )
        return True


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
        existing = runtime_db.get_runtime_initiative(initiative_id)
        if not existing or str(existing.get("status") or "") != "pending":
            return False
        attempt_count = int(existing.get("attempt_count") or 0) + 1
        runtime_db.update_runtime_initiative(
            initiative_id,
            attempt_count=attempt_count,
            last_attempt_at=now.isoformat(),
            next_attempt_at=retry_at.isoformat(),
            blocked_reason=blocked_reason[:120],
            action_summary=(
                action_summary[:200]
                if action_summary
                else str(existing.get("action_summary") or "")[:200]
            ),
            updated_at=now.isoformat(),
        )
        event_bus.publish(
            "heartbeat.initiative_attempted",
            {
                "initiative_id": initiative_id,
                "focus": str(existing.get("focus") or "")[:100],
                "attempt_count": attempt_count,
                "blocked_reason": blocked_reason[:120],
                "next_attempt_at": retry_at.isoformat(),
            },
        )
        return True


def approve_initiative(initiative_id: str, *, note: str = "") -> dict[str, object] | None:
    """Mark an initiative as user-approved. Returns the updated record or None if not found."""
    now = datetime.now(UTC).isoformat()
    result = approve_runtime_initiative(initiative_id, outcome_note=note, updated_at=now)
    if result:
        event_bus.publish(
            "heartbeat.initiative_approved",
            {
                "initiative_id": initiative_id,
                "focus": str(result.get("focus") or "")[:100],
                "note": note[:120],
            },
        )
    return result


def reject_initiative(initiative_id: str, *, note: str = "") -> dict[str, object] | None:
    """Mark an initiative as user-rejected and expire it. Returns updated record or None."""
    now = datetime.now(UTC).isoformat()
    result = reject_runtime_initiative(initiative_id, outcome_note=note, updated_at=now)
    if result:
        event_bus.publish(
            "heartbeat.initiative_rejected",
            {
                "initiative_id": initiative_id,
                "focus": str(result.get("focus") or "")[:100],
                "note": note[:120],
            },
        )
    return result


def get_initiative_queue_state() -> dict[str, object]:
    """Return full queue state for MC observability."""
    now = datetime.now(UTC)
    with _QUEUE_LOCK:
        _expire_stale(now)
        all_items = runtime_db.list_runtime_initiatives(limit=_MAX_QUEUE_SIZE + 40)
        pending = [i for i in all_items if i["status"] == "pending"]
        acted = [i for i in all_items if i["status"] == "acted"]
        expired = [i for i in all_items if i["status"] == "expired"]

    approved = [i for i in all_items if str(i.get("outcome") or "") == "approved"]
    rejected = [i for i in all_items if str(i.get("outcome") or "") == "rejected"]

    return {
        "queue_size": len(all_items),
        "pending_count": len(pending),
        "acted_count": len(acted),
        "expired_count": len(expired),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "pending": pending,
        "recent_acted": acted[:3],
        "recent_approved": approved[:3],
        "recent_rejected": rejected[:3],
        "max_queue_size": _MAX_QUEUE_SIZE,
        "expire_minutes": _EXPIRE_MINUTES,
        "retry_delay_minutes": _RETRY_DELAY_MINUTES,
    }


def _expire_stale(now: datetime) -> None:
    """Expire initiatives older than _EXPIRE_MINUTES. Must hold _QUEUE_LOCK."""
    cutoff = now - timedelta(minutes=_EXPIRE_MINUTES)
    for item in runtime_db.list_runtime_initiatives(
        status="pending",
        limit=_MAX_QUEUE_SIZE + 100,
    ):
        detected = _parse_iso(str(item.get("detected_at") or ""))
        if detected is not None and detected < cutoff:
            runtime_db.update_runtime_initiative(
                str(item.get("initiative_id") or ""),
                status="expired",
                updated_at=now.isoformat(),
            )


def _trim_pending(now: datetime) -> None:
    pending = runtime_db.list_runtime_initiatives(
        status="pending",
        limit=_MAX_QUEUE_SIZE + 100,
    )
    pending.sort(key=_initiative_sort_key)
    for item in pending[_MAX_QUEUE_SIZE:]:
        runtime_db.update_runtime_initiative(
            str(item.get("initiative_id") or ""),
            status="expired",
            blocked_reason="queue-trimmed",
            updated_at=now.isoformat(),
        )


def _parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _initiative_due(initiative: dict[str, object], now: datetime) -> bool:
    next_attempt = str(initiative.get("next_attempt_at") or "").strip()
    if not next_attempt:
        return True
    due_at = _parse_iso(next_attempt)
    if due_at is None:
        return True
    return due_at <= now


def _initiative_sort_key(initiative: dict[str, object]) -> tuple[int, int, str]:
    priority_rank = {"high": 0, "medium": 1, "low": 2}.get(
        str(initiative.get("priority") or "medium"),
        1,
    )
    return (
        priority_rank,
        int(initiative.get("attempt_count") or 0),
        str(initiative.get("detected_at") or ""),
    )
