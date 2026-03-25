from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflective_critics,
    list_runtime_reflection_signals,
    list_runtime_self_model_signals,
    supersede_runtime_reflection_signals_for_domain,
    update_runtime_reflection_signal_status,
    upsert_runtime_reflection_signal,
)

_STALE_AFTER_DAYS = 14


def track_runtime_reflection_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
    user_message: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    normalized_message = " ".join(str(user_message or "").split()).strip()

    candidates = _extract_reflection_candidates()
    items = _persist_reflection_signals(
        signals=candidates,
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded reflection signals."
            if items
            else f"No bounded reflection signal warranted tracking for '{normalized_message[:80]}'."
            if normalized_message
            else "No bounded reflection signal warranted tracking."
        ),
    }


def refresh_runtime_reflection_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_reflection_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "integrating", "settled"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_reflection_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded reflection inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "reflection_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_reflection_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_reflection_signal_statuses()
    items = list_runtime_reflection_signals(limit=max(limit, 1))
    active = [item for item in items if str(item.get("status") or "") == "active"]
    integrating = [item for item in items if str(item.get("status") or "") == "integrating"]
    settled = [item for item in items if str(item.get("status") or "") == "settled"]
    stale = [item for item in items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered = [*active, *integrating, *settled, *stale, *superseded]
    latest = next(iter(active or integrating or settled or stale or superseded), None)
    return {
        "active": bool(active or integrating or settled),
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "integrating_count": len(integrating),
            "settled_count": len(settled),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active reflection signal"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
    }


def _extract_reflection_candidates() -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=12):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _domain_key_from_focus(str(focus.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["focus"] = focus

    for critic in list_runtime_reflective_critics(limit=12):
        if str(critic.get("status") or "") != "active":
            continue
        domain_key = _domain_key_from_critic(str(critic.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["critic"] = critic

    for signal in list_runtime_self_model_signals(limit=16):
        status = str(signal.get("status") or "")
        if status not in {"active", "uncertain"}:
            continue
        domain_key = _domain_key_from_self_model(str(signal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        signal_type = str(signal.get("signal_type") or "")
        if signal_type == "current-limitation" and status == "active":
            bucket["self_limitation"] = signal
        if signal_type == "improvement-edge":
            bucket["improvement_edge"] = signal

    for goal in list_runtime_goal_signals(limit=16):
        status = str(goal.get("status") or "")
        if status not in {"active", "blocked"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "blocked":
            bucket["blocked_goal"] = goal
        else:
            bucket["goal"] = goal

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        focus = snapshot.get("focus")
        critic = snapshot.get("critic")
        self_limitation = snapshot.get("self_limitation")
        improvement_edge = snapshot.get("improvement_edge")
        blocked_goal = snapshot.get("blocked_goal")
        goal = snapshot.get("goal")
        title_suffix = _domain_title(domain_key)

        if focus and critic and self_limitation:
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="persistent-tension",
                    status="active",
                    title=f"Persistent reflection tension: {title_suffix}",
                    summary=f"Jarvis is still carrying unresolved reflective pressure around {title_suffix.lower()}.",
                    rationale="Development focus, reflective critic, and self-model limitation all still point at the same bounded problem domain.",
                    status_reason="Multiple bounded layers still agree that this tension is live.",
                    source_items=[focus, critic, self_limitation, blocked_goal],
                )
            )
            continue

        if focus and improvement_edge and not critic and not blocked_goal:
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="settled-thread",
                    status="settled",
                    title=f"Settled reflection thread: {title_suffix}",
                    summary=f"A previously tense reflective thread around {title_suffix.lower()} now appears calmer.",
                    rationale="A prior weak area now has explicit better-now style feedback without matching active critic pressure or blocked-goal pressure.",
                    status_reason="The bounded thread appears meaningfully calmer and is now being retained as settled rather than live tension.",
                    source_items=[focus, goal, improvement_edge],
                )
            )
            continue

        if focus and (goal or blocked_goal) and (self_limitation or improvement_edge) and not critic:
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="slow-integration",
                    status="integrating",
                    title=f"Slow integration thread: {title_suffix}",
                    summary=f"Jarvis is carrying a slow integration thread around {title_suffix.lower()}.",
                    rationale="Multiple bounded layers still point at the same improvement domain, but active reflective mismatch pressure has eased enough that the thread should be treated as integration rather than raw tension.",
                    status_reason="Cross-layer support remains live, but the domain is moving from pressure into integration.",
                    source_items=[focus, goal, blocked_goal, self_limitation, improvement_edge],
                )
            )

    return candidates[:4]


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
        "canonical_key": f"reflection-signal:{signal_type}:{domain_key}",
        "domain_key": domain_key,
        "status": status,
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": "multi-signal-runtime-derivation",
        "confidence": confidence,
        "evidence_summary": _merge_fragments(*[str(item.get("evidence_summary") or "") for item in items]),
        "support_summary": _merge_fragments(*[str(item.get("support_summary") or "") for item in items]),
        "support_count": support_count,
        "session_count": session_count,
        "status_reason": status_reason,
    }


def _persist_reflection_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_reflection_signal(
            signal_id=f"reflection-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "reflection-signal"),
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
        domain_key = str(signal.get("domain_key") or "")
        superseded_count = 0
        if domain_key:
            superseded_count = supersede_runtime_reflection_signals_for_domain(
                domain_key=domain_key,
                exclude_signal_id=str(persisted_item.get("signal_id") or ""),
                updated_at=now,
                status_reason=f"Superseded by newer bounded reflection signal {persisted_item.get('signal_id')}.",
            )
        if superseded_count > 0:
            event_bus.publish(
                "reflection_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "canonical_key": persisted_item.get("canonical_key"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "reflection_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "reflection_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created") or persisted_item.get("was_updated"):
            if str(persisted_item.get("status") or "") == "settled":
                event_bus.publish(
                    "reflection_signal.settled",
                    {
                        "signal_id": persisted_item.get("signal_id"),
                        "signal_type": persisted_item.get("signal_type"),
                        "status": persisted_item.get("status"),
                        "summary": persisted_item.get("summary"),
                    },
                )
        persisted.append(persisted_item)
    return persisted


def _domain_key_from_focus(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if "danish-concise-calibration" in text:
        return "danish-concise-calibration"
    if "avoid-repetitive-openers" in text:
        return "avoid-repetitive-openers"
    if text.startswith("development-focus:"):
        return text.removeprefix("development-focus:").replace(":", "-")
    return ""


def _domain_key_from_critic(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if "danish-concise-calibration" in text:
        return "danish-concise-calibration"
    if "avoid-repetitive-openers" in text:
        return "avoid-repetitive-openers"
    prefix = "reflective-critic:mismatch:development-focus:"
    if text.startswith(prefix):
        return text.removeprefix(prefix).replace(":", "-")
    return ""


def _domain_key_from_self_model(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if text.startswith("self-model:limitation:"):
        return text.removeprefix("self-model:limitation:")
    if text.startswith("self-model:improving:"):
        return text.removeprefix("self-model:improving:")
    return ""


def _goal_domain_key(canonical_key: str) -> str:
    return str(canonical_key or "").removeprefix("goal-signal:")


def _domain_title(domain_key: str) -> str:
    if domain_key == "danish-concise-calibration":
        return "Danish concise calibration"
    if domain_key == "avoid-repetitive-openers":
        return "opener calibration"
    return domain_key.replace("-", " ") or "current bounded thread"


def _merge_fragments(*parts: str) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
        if len(merged) >= 4:
            break
    return " | ".join(merged)


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
