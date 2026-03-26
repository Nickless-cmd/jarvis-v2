from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_open_loop_signals,
    list_runtime_reflective_critics,
    list_runtime_reflection_signals,
    list_runtime_temporal_recurrence_signals,
    supersede_runtime_open_loop_signals_for_domain,
    update_runtime_open_loop_signal_status,
    upsert_runtime_open_loop_signal,
)

_STALE_AFTER_DAYS = 14


def track_runtime_open_loop_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_open_loop_signals(
        signals=_extract_open_loop_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded open-loop signals."
            if items
            else "No bounded open-loop signal warranted tracking."
        ),
    }


def refresh_runtime_open_loop_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_open_loop_signals(limit=40):
        if str(item.get("status") or "") not in {"open", "softening", "closed"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_open_loop_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded open-loop inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "open_loop_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_open_loop_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_open_loop_signal_statuses()
    items = list_runtime_open_loop_signals(limit=max(limit, 1))
    snapshots = _build_governance_snapshots()
    enriched_items = [_with_closure_governance(item, snapshots=snapshots) for item in items]
    open_items = [item for item in enriched_items if str(item.get("status") or "") == "open"]
    softening = [item for item in enriched_items if str(item.get("status") or "") == "softening"]
    closed = [item for item in enriched_items if str(item.get("status") or "") == "closed"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
    ordered = [*open_items, *softening, *closed, *stale, *superseded]
    latest = next(iter(open_items or softening or closed or stale or superseded), None)
    return {
        "active": bool(open_items or softening or closed),
        "items": ordered,
        "summary": {
            "open_count": len(open_items),
            "softening_count": len(softening),
            "closed_count": len(closed),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "ready_count": len([item for item in ordered if str(item.get("closure_confidence") or "") == "high"]),
            "current_signal": str((latest or {}).get("title") or "No active open loop"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_closure_confidence": str((latest or {}).get("closure_confidence") or "low"),
        },
    }


def _extract_open_loop_candidates() -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=18):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["active_focus"] = focus

    for critic in list_runtime_reflective_critics(limit=18):
        status = str(critic.get("status") or "")
        if status not in {"active", "resolved"}:
            continue
        domain_key = _critic_domain_key(str(critic.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if status == "active":
                bucket["active_critic"] = critic
            else:
                bucket["resolved_critic"] = critic

    for goal in list_runtime_goal_signals(limit=18):
        status = str(goal.get("status") or "")
        if status not in {"active", "blocked", "completed"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if status == "blocked":
                bucket["blocked_goal"] = goal
            elif status == "active":
                bucket["active_goal"] = goal
            else:
                bucket["completed_goal"] = goal

    for reflection in list_runtime_reflection_signals(limit=18):
        status = str(reflection.get("status") or "")
        if status not in {"active", "integrating", "settled"}:
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if status == "active":
                bucket["active_reflection"] = reflection
            elif status == "integrating":
                bucket["integrating_reflection"] = reflection
            else:
                bucket["settled_reflection"] = reflection

    for recurrence in list_runtime_temporal_recurrence_signals(limit=18):
        status = str(recurrence.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _temporal_domain_key(str(recurrence.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if status == "active":
                bucket["active_recurrence"] = recurrence
            else:
                bucket["softening_recurrence"] = recurrence

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        active_focus = snapshot.get("active_focus")
        active_critic = snapshot.get("active_critic")
        resolved_critic = snapshot.get("resolved_critic")
        blocked_goal = snapshot.get("blocked_goal")
        active_goal = snapshot.get("active_goal")
        completed_goal = snapshot.get("completed_goal")
        active_reflection = snapshot.get("active_reflection")
        integrating_reflection = snapshot.get("integrating_reflection")
        settled_reflection = snapshot.get("settled_reflection")
        active_recurrence = snapshot.get("active_recurrence")
        softening_recurrence = snapshot.get("softening_recurrence")
        title_suffix = _domain_title(domain_key)

        live_pressure = [item for item in [active_critic, blocked_goal, active_reflection, active_recurrence] if item]
        if active_focus and live_pressure:
            signal_type = "persistent-open-loop" if active_recurrence or (active_critic and blocked_goal) else "open-loop"
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type=signal_type,
                    status="open",
                    title=f"Open loop: {title_suffix}",
                    summary=f"A bounded loop around {title_suffix.lower()} is still unresolved and carrying live pressure.",
                    rationale="Existing development, critic, goal, reflection, or recurrence truth still shows unresolved bounded pressure in the same domain.",
                    status_reason="The bounded thread is still visibly unresolved.",
                    source_items=[
                        active_focus,
                        active_critic,
                        blocked_goal,
                        active_reflection,
                        active_recurrence,
                    ],
                )
            )
            continue

        if active_focus and (integrating_reflection or softening_recurrence) and not active_critic and not blocked_goal:
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="softening-loop",
                    status="softening",
                    title=f"Softening loop: {title_suffix}",
                    summary=f"A bounded loop around {title_suffix.lower()} is still present, but the pressure is easing.",
                    rationale="The thread remains live through existing focus and integration/recurrence truth, but acute critic or blocked-goal pressure is no longer present.",
                    status_reason="The loop is still present, but it is softening rather than pressing.",
                    source_items=[
                        active_focus,
                        active_goal,
                        integrating_reflection,
                        softening_recurrence,
                    ],
                )
            )
            continue

        if (active_focus or active_goal or completed_goal) and settled_reflection and (softening_recurrence or resolved_critic or completed_goal) and not active_critic and not blocked_goal:
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="softening-loop",
                    status="closed",
                    title=f"Closed loop: {title_suffix}",
                    summary=f"A bounded loop around {title_suffix.lower()} now appears closed by visible runtime evidence.",
                    rationale="The same domain now reads as settled or completed across existing layers without matching active critic or blocked-goal pressure.",
                    status_reason="The bounded loop appears closed by calmer reflection and cleared pressure, not by autonomous task execution.",
                    source_items=[
                        active_focus,
                        active_goal,
                        completed_goal,
                        settled_reflection,
                        softening_recurrence,
                        resolved_critic,
                    ],
                )
            )

    return candidates[:4]


def _build_governance_snapshots() -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for critic in list_runtime_reflective_critics(limit=18):
        status = str(critic.get("status") or "")
        if status not in {"active", "resolved"}:
            continue
        domain_key = _critic_domain_key(str(critic.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_critic"] = critic
        else:
            bucket["resolved_critic"] = critic

    for goal in list_runtime_goal_signals(limit=18):
        status = str(goal.get("status") or "")
        if status not in {"blocked", "completed"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "blocked":
            bucket["blocked_goal"] = goal
        else:
            bucket["completed_goal"] = goal

    for reflection in list_runtime_reflection_signals(limit=18):
        status = str(reflection.get("status") or "")
        if status not in {"integrating", "settled"}:
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "integrating":
            bucket["integrating_reflection"] = reflection
        else:
            bucket["settled_reflection"] = reflection

    for recurrence in list_runtime_temporal_recurrence_signals(limit=18):
        status = str(recurrence.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _temporal_domain_key(str(recurrence.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_recurrence"] = recurrence
        else:
            bucket["softening_recurrence"] = recurrence

    return snapshots


def _with_closure_governance(
    item: dict[str, object],
    *,
    snapshots: dict[str, dict[str, object]],
) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _open_loop_domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key, {}) if domain_key else {}
    active_critic = snapshot.get("active_critic")
    blocked_goal = snapshot.get("blocked_goal")
    completed_goal = snapshot.get("completed_goal")
    integrating_reflection = snapshot.get("integrating_reflection")
    settled_reflection = snapshot.get("settled_reflection")
    active_recurrence = snapshot.get("active_recurrence")
    softening_recurrence = snapshot.get("softening_recurrence")
    status = str(item.get("status") or "")

    closure_confidence = "low"
    closure_reason = "No current closure evidence is strong enough to treat this loop as ready."

    if status == "closed":
        closure_confidence = "high"
        closure_reason = "This loop already reads as conservatively closed by existing runtime truth."
    elif active_critic or blocked_goal:
        if settled_reflection or softening_recurrence or completed_goal:
            closure_confidence = "medium"
            closure_reason = "Some calming evidence exists, but active critic or blocked-goal pressure still keeps closure readiness bounded."
        else:
            closure_confidence = "low"
            closure_reason = "Active critic or blocked-goal pressure is still present, so the loop is not close to closure."
    elif settled_reflection and (softening_recurrence or completed_goal):
        closure_confidence = "high"
        closure_reason = "Settled reflection and calmer completion signals now point toward likely closure readiness."
    elif integrating_reflection or softening_recurrence:
        closure_confidence = "medium"
        closure_reason = "The loop is easing through integration or softening, but closure evidence is not yet strong."
    elif active_recurrence:
        closure_confidence = "low"
        closure_reason = "The loop still shows active recurrence, so closure readiness remains low."

    enriched["closure_readiness"] = closure_confidence
    enriched["closure_confidence"] = closure_confidence
    enriched["closure_reason"] = closure_reason
    return enriched


def _persist_open_loop_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_open_loop_signal(
            signal_id=f"open-loop-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "open-loop"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "open"),
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
        superseded_count = supersede_runtime_open_loop_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer open-loop reading for the same bounded domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "open_loop_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "open_loop_signal.created" if persisted_item.get("status") != "closed" else "open_loop_signal.closed",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "open_loop_signal.updated" if persisted_item.get("status") != "closed" else "open_loop_signal.closed",
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
) -> dict[str, object]:
    items = [item for item in source_items if item]
    support_count = max([int(item.get("support_count") or 1) for item in items], default=1)
    session_count = max([int(item.get("session_count") or 1) for item in items], default=1)
    confidence = "high" if len(items) >= 3 else "medium"
    return {
        "signal_type": signal_type,
        "canonical_key": f"open-loop:{signal_type}:{domain_key}",
        "domain_key": domain_key,
        "status": status,
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": "derived-runtime-open-loop",
        "confidence": confidence,
        "evidence_summary": _merge_fragments(*[str(item.get("evidence_summary") or "") for item in items]),
        "support_summary": _merge_fragments(*[str(item.get("support_summary") or "") for item in items]),
        "support_count": support_count,
        "session_count": session_count,
        "status_reason": status_reason,
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


def _temporal_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _open_loop_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Open loop"


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
