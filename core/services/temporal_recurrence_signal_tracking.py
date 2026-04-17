from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflective_critics,
    list_runtime_reflection_signals,
    list_runtime_temporal_recurrence_signals,
    supersede_runtime_temporal_recurrence_signals_for_domain,
    update_runtime_temporal_recurrence_signal_status,
    upsert_runtime_temporal_recurrence_signal,
)

_STALE_AFTER_DAYS = 14


def track_runtime_temporal_recurrence_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_recurrence_signals(
        signals=_extract_recurrence_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded temporal recurrence signals."
            if items
            else "No bounded temporal recurrence signal warranted tracking."
        ),
    }


def refresh_runtime_temporal_recurrence_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_temporal_recurrence_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_temporal_recurrence_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded recurrence inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "temporal_recurrence_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_temporal_recurrence_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_temporal_recurrence_signal_statuses()
    items = list_runtime_temporal_recurrence_signals(limit=max(limit, 1))
    active = [item for item in items if str(item.get("status") or "") == "active"]
    softening = [item for item in items if str(item.get("status") or "") == "softening"]
    stale = [item for item in items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered = [*active, *softening, *stale, *superseded]
    latest = next(iter(active or softening or stale or superseded), None)
    return {
        "active": bool(active or softening),
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active temporal recurrence signal"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
    }


def _extract_recurrence_candidates() -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=18):
        status = str(focus.get("status") or "")
        if status not in {"active", "stale", "completed"}:
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, _empty_snapshot())
        bucket["focus_records"].append(focus)
        if status == "active":
            bucket["active_focus"] = focus

    for critic in list_runtime_reflective_critics(limit=18):
        status = str(critic.get("status") or "")
        if status not in {"active", "stale", "resolved"}:
            continue
        domain_key = _critic_domain_key(str(critic.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, _empty_snapshot())
        bucket["critic_records"].append(critic)
        if status == "active":
            bucket["active_critic"] = critic

    for goal in list_runtime_goal_signals(limit=18):
        status = str(goal.get("status") or "")
        if status not in {"active", "blocked", "completed", "stale"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, _empty_snapshot())
        bucket["goal_records"].append(goal)
        if status == "blocked":
            bucket["blocked_goal"] = goal
        if status == "active":
            bucket["active_goal"] = goal
        if status == "completed":
            bucket["completed_goal"] = goal

    for reflection in list_runtime_reflection_signals(limit=18):
        status = str(reflection.get("status") or "")
        if status not in {"active", "integrating", "settled", "stale"}:
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, _empty_snapshot())
        bucket["reflection_records"].append(reflection)
        if status in {"active", "integrating"}:
            bucket["integrating_reflection"] = reflection
        if status == "settled":
            bucket["settled_reflection"] = reflection

    candidates: list[dict[str, object]] = []
    for domain_key, bucket in snapshots.items():
        record_count = sum(
            len(bucket[name])
            for name in ("focus_records", "critic_records", "goal_records", "reflection_records")
        )
        if record_count < 3:
            continue

        active_focus = bucket["active_focus"]
        active_critic = bucket["active_critic"]
        blocked_goal = bucket["blocked_goal"]
        active_goal = bucket["active_goal"]
        integrating_reflection = bucket["integrating_reflection"]
        settled_reflection = bucket["settled_reflection"]
        completed_goal = bucket["completed_goal"]
        title_suffix = _domain_title(domain_key)

        if active_focus and (active_critic or blocked_goal or integrating_reflection):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="recurring-tension",
                    status="active",
                    title=f"Recurring tension: {title_suffix}",
                    summary=f"The same bounded tension around {title_suffix.lower()} keeps returning over time.",
                    rationale="The same domain keeps reappearing across existing development, critic, goal, or reflection truth rather than showing up as a one-off signal.",
                    status_reason="Repeated domain recurrence still carries live pressure.",
                    source_items=[
                        active_focus,
                        active_critic,
                        blocked_goal,
                        integrating_reflection,
                    ],
                    record_count=record_count,
                )
            )
            continue

        if (active_focus or active_goal) and (settled_reflection or completed_goal):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="recurring-direction",
                    status="softening",
                    title=f"Recurring direction: {title_suffix}",
                    summary=f"The same bounded development direction around {title_suffix.lower()} keeps returning, but the thread looks calmer now.",
                    rationale="The domain is recurring across existing tracked layers, but active pressure has eased enough that the pattern now looks more like a carried direction than live friction.",
                    status_reason="The repeated thread is still present, but it is softening into calmer continuity.",
                    source_items=[
                        active_focus,
                        active_goal,
                        settled_reflection,
                        completed_goal,
                    ],
                    record_count=record_count,
                )
            )

    return candidates[:4]


def _persist_recurrence_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_temporal_recurrence_signal(
            signal_id=f"recurrence-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "temporal-recurrence"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "runtime-derived-support"),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=str(signal.get("support_summary") or ""),
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(signal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        superseded_count = supersede_runtime_temporal_recurrence_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer temporal recurrence reading for the same bounded domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "temporal_recurrence_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "temporal_recurrence_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "temporal_recurrence_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _build_candidate(
    *,
    domain_key: str,
    signal_type: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    status_reason: str,
    source_items: list[dict[str, object] | None],
    record_count: int,
) -> dict[str, object]:
    items = [item for item in source_items if item]
    support_count = max([int(item.get("support_count") or 1) for item in items], default=1)
    session_count = max([int(item.get("session_count") or 1) for item in items], default=1)
    confidence = "high" if len(items) >= 3 or record_count >= 5 else "medium"
    return {
        "signal_type": signal_type,
        "canonical_key": f"temporal-recurrence:{signal_type}:{domain_key}",
        "domain_key": domain_key,
        "status": status,
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": "multi-signal-runtime-derivation",
        "confidence": confidence,
        "evidence_summary": _merge_fragments(*[str(item.get("evidence_summary") or "") for item in items]),
        "support_summary": _merge_fragments(
            f"{record_count} bounded signal records across existing runtime layers.",
            *[str(item.get("support_summary") or "") for item in items],
        ),
        "support_count": max(support_count, record_count),
        "session_count": session_count,
        "status_reason": status_reason,
    }


def _empty_snapshot() -> dict[str, object]:
    return {
        "focus_records": [],
        "critic_records": [],
        "goal_records": [],
        "reflection_records": [],
        "active_focus": None,
        "active_critic": None,
        "blocked_goal": None,
        "active_goal": None,
        "completed_goal": None,
        "integrating_reflection": None,
        "settled_reflection": None,
    }


def _focus_domain_key(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if text.startswith("development-focus:communication:"):
        return text.removeprefix("development-focus:communication:")
    if text.startswith("development-focus:user-directed:"):
        return text.removeprefix("development-focus:user-directed:")
    if text.startswith("development-focus:runtime:"):
        parts = text.removeprefix("development-focus:runtime:").split(":")
        return parts[0] if parts else ""
    return ""


def _critic_domain_key(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if text.startswith("reflective-critic:mismatch:development-focus:communication:"):
        return text.removeprefix("reflective-critic:mismatch:development-focus:communication:")
    if text.startswith("reflective-critic:mismatch:development-focus:user-directed:"):
        return text.removeprefix("reflective-critic:mismatch:development-focus:user-directed:")
    if text.startswith("reflective-critic:mismatch:development-focus:runtime:"):
        parts = text.removeprefix("reflective-critic:mismatch:development-focus:runtime:").split(":")
        return parts[0] if parts else ""
    return ""


def _goal_domain_key(canonical_key: str) -> str:
    return str(canonical_key or "").removeprefix("goal-signal:")


def _reflection_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Recurring thread"


def _merge_fragments(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        normalized = " ".join(str(value or "").split()).strip()
        if normalized and normalized not in parts:
            parts.append(normalized)
    return " | ".join(parts[:4])


def _parse_dt(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
