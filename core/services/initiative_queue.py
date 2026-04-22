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
_LONG_TERM_REASSESS_DAYS = 14
_MAX_ACTIVE_LONG_TERM_INTENTIONS = 3
_QUEUE_LOCK = threading.Lock()


def push_initiative(
    *,
    focus: str,
    source: str = "inner-voice",
    source_id: str = "",
    priority: str = "medium",
) -> str:
    """Push a new initiative to the queue. Returns the initiative_id.

    Mood dialer gating:
    - level 0 (distressed): afviser nye initiativer — retur tom streng
    - level 1 (melancholic): downgrader priority til low
    - level 2 (neutral): passerer uændret
    - level 3-4 (content/euphoric): kan upgradere low→medium
    """
    now = datetime.now(UTC)
    initiative_id = f"init-{uuid4().hex[:10]}"
    normalized_focus = focus[:200].strip()
    if not normalized_focus:
        normalized_focus = "Follow up on unspecified initiative"
    normalized_priority = (
        priority.strip().lower() if priority.strip().lower() in {"low", "medium", "high"} else "medium"
    )

    # Mood dialer gate — kun hvis initiative ikke er explicitly "high"
    if normalized_priority != "high":
        try:
            from core.services.mood_dialer import derive_from_v2_mood
            params = derive_from_v2_mood()
            if params.mood_level == 0:
                # Distressed: refuse new initiatives entirely
                event_bus.publish("heartbeat.initiative_gated", {
                    "focus": normalized_focus[:100], "reason": "mood_distressed",
                    "mood_level": 0,
                })
                return ""
            elif params.mood_level == 1 and normalized_priority == "medium":
                normalized_priority = "low"
            elif params.mood_level >= 3 and normalized_priority == "low":
                normalized_priority = "medium"
        except Exception:
            pass

    with _QUEUE_LOCK:
        _expire_stale(now)
        existing = runtime_db.find_pending_runtime_initiative_by_focus(
            normalized_focus,
            initiative_type="initiative",
        )
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
            initiative_type="initiative",
            focus=normalized_focus,
            why_text="",
            source=source,
            source_id=source_id,
            status="pending",
            priority=normalized_priority,
            detected_at=now.isoformat(),
            first_seeded_at=now.isoformat(),
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


def seed_long_term_intention(
    *,
    title: str,
    why: str,
    source: str = "life-project",
    source_id: str = "",
    priority: str = "medium",
) -> str:
    """Create or refresh a long-term intention owned by Jarvis."""
    now = datetime.now(UTC)
    normalized_title = str(title or "").strip()[:200]
    if not normalized_title:
        raise ValueError("title is required")
    normalized_why = str(why or "").strip()[:400]
    if not normalized_why:
        raise ValueError("why is required")
    normalized_priority = (
        priority.strip().lower() if priority.strip().lower() in {"low", "medium", "high"} else "medium"
    )
    initiative_id = f"life-{uuid4().hex[:10]}"

    with _QUEUE_LOCK:
        _expire_stale(now)
        existing = _find_active_long_term_intention_by_title(normalized_title)
        if existing:
            existing_id = str(existing.get("initiative_id") or "")
            runtime_db.update_runtime_initiative(
                existing_id,
                why_text=normalized_why,
                detected_at=now.isoformat(),
                next_attempt_at=now.isoformat(),
                blocked_reason="",
                updated_at=now.isoformat(),
            )
            return existing_id
        active = list_active_long_term_intentions(limit=_MAX_ACTIVE_LONG_TERM_INTENTIONS + 2)
        if len(active) >= _MAX_ACTIVE_LONG_TERM_INTENTIONS:
            raise RuntimeError("max active life projects reached")
        runtime_db.create_runtime_initiative(
            initiative_id=initiative_id,
            initiative_type="long_term_intention",
            focus=normalized_title,
            why_text=normalized_why,
            source=source,
            source_id=source_id,
            status="pending",
            priority=normalized_priority,
            detected_at=now.isoformat(),
            first_seeded_at=now.isoformat(),
            next_attempt_at=now.isoformat(),
            updated_at=now.isoformat(),
        )

    event_bus.publish(
        "heartbeat.initiative_pushed",
        {
            "initiative_id": initiative_id,
            "focus": normalized_title[:100],
            "source": source,
            "priority": normalized_priority,
            "initiative_type": "long_term_intention",
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
        if str(existing.get("initiative_type") or "initiative") == "long_term_intention":
            reassess_at = (
                datetime.fromisoformat(now) + timedelta(days=_LONG_TERM_REASSESS_DAYS)
            ).isoformat()
            runtime_db.update_runtime_initiative(
                initiative_id,
                status="pending",
                last_action_at=now,
                acted_at=now,
                next_attempt_at=reassess_at,
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
                    "initiative_type": "long_term_intention",
                    "reassess_at": reassess_at,
                },
            )
            return True
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
        if str(existing.get("initiative_type") or "initiative") == "long_term_intention":
            retry_at = now + timedelta(days=_LONG_TERM_REASSESS_DAYS)
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
        long_term = [
            i for i in all_items
            if str(i.get("initiative_type") or "") == "long_term_intention"
            and not str(i.get("abandoned_at") or "").strip()
        ]

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
        "life_projects": long_term[:_MAX_ACTIVE_LONG_TERM_INTENTIONS],
        "life_project_count": len(long_term),
        "long_term_reassess_days": _LONG_TERM_REASSESS_DAYS,
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
        if str(item.get("initiative_type") or "initiative") == "long_term_intention":
            continue
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
    pending = [
        item
        for item in pending
        if str(item.get("initiative_type") or "initiative") != "long_term_intention"
    ]
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


def list_active_long_term_intentions(*, limit: int = 3) -> list[dict[str, object]]:
    items = runtime_db.list_runtime_initiatives(
        initiative_type="long_term_intention",
        limit=max(limit, 1) + 20,
    )
    active = [
        item
        for item in items
        if str(item.get("status") or "") == "pending"
        and not str(item.get("abandoned_at") or "").strip()
    ]
    active.sort(key=lambda item: str(item.get("first_seeded_at") or item.get("detected_at") or ""))
    return active[: max(limit, 1)]


def abandon_long_term_intention(initiative_id: str, *, note: str = "") -> dict[str, object] | None:
    now = datetime.now(UTC).isoformat()
    with _QUEUE_LOCK:
        existing = runtime_db.get_runtime_initiative(initiative_id)
        if not existing or str(existing.get("initiative_type") or "") != "long_term_intention":
            return None
        updated = runtime_db.update_runtime_initiative(
            initiative_id,
            status="expired",
            abandoned_at=now,
            blocked_reason=note[:120],
            updated_at=now,
        )
    if updated:
        event_bus.publish(
            "heartbeat.initiative_rejected",
            {
                "initiative_id": initiative_id,
                "focus": str(updated.get("focus") or "")[:100],
                "initiative_type": "long_term_intention",
                "note": note[:120],
            },
        )
    return updated


def _find_active_long_term_intention_by_title(title: str) -> dict[str, object] | None:
    normalized = str(title or "").strip().lower()
    if not normalized:
        return None
    for item in runtime_db.list_runtime_initiatives(
        initiative_type="long_term_intention",
        limit=_MAX_ACTIVE_LONG_TERM_INTENTIONS + 20,
    ):
        if str(item.get("status") or "") != "pending":
            continue
        if str(item.get("abandoned_at") or "").strip():
            continue
        if str(item.get("focus") or "").strip().lower() == normalized:
            return item
    return None
