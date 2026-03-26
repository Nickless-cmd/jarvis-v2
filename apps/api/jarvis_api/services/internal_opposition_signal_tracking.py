from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_internal_opposition_signals,
    list_runtime_reflective_critics,
    list_runtime_reflection_signals,
    list_runtime_self_model_signals,
    list_runtime_temporal_recurrence_signals,
    list_runtime_world_model_signals,
    supersede_runtime_internal_opposition_signals_for_domain,
    update_runtime_internal_opposition_signal_status,
    upsert_runtime_internal_opposition_signal,
)

_STALE_AFTER_DAYS = 14


def track_runtime_internal_opposition_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_internal_opposition_signals(
        signals=_extract_internal_opposition_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded internal opposition signals."
            if items
            else "No bounded internal opposition signal warranted tracking."
        ),
    }


def refresh_runtime_internal_opposition_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_internal_opposition_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_internal_opposition_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded internal-opposition inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "internal_opposition_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_internal_opposition_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_internal_opposition_signal_statuses()
    items = list_runtime_internal_opposition_signals(limit=max(limit, 1))
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
            "current_signal": str((latest or {}).get("title") or "No active internal opposition signal"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
    }


def _extract_internal_opposition_candidates() -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=18):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["active_focus"] = focus

    for goal in list_runtime_goal_signals(limit=18):
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
            bucket["active_goal"] = goal

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

    for signal in list_runtime_self_model_signals(limit=18):
        status = str(signal.get("status") or "")
        if status not in {"active", "uncertain"}:
            continue
        domain_key = _self_model_domain_key(str(signal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_self_model"] = signal
        else:
            bucket["uncertain_self_model"] = signal

    for signal in list_runtime_reflection_signals(limit=18):
        status = str(signal.get("status") or "")
        if status not in {"active", "integrating", "settled"}:
            continue
        domain_key = _reflection_domain_key(str(signal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "settled":
            bucket["settled_reflection"] = signal
        else:
            bucket["live_reflection"] = signal

    for signal in list_runtime_temporal_recurrence_signals(limit=18):
        status = str(signal.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _temporal_domain_key(str(signal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_recurrence"] = signal
        else:
            bucket["softening_recurrence"] = signal

    for item in build_runtime_open_loop_signal_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"open", "softening"}:
            continue
        domain_key = _open_loop_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "open":
            bucket["open_loop"] = item
        else:
            bucket["softening_loop"] = item

    world_uncertain_signals = [
        item
        for item in list_runtime_world_model_signals(limit=12)
        if str(item.get("status") or "") == "uncertain"
    ]
    active_goal_count = len([item for item in list_runtime_goal_signals(limit=18) if str(item.get("status") or "") in {"active", "blocked"}])
    open_loop_surface = build_runtime_open_loop_signal_surface(limit=12)

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        active_focus = snapshot.get("active_focus")
        active_goal = snapshot.get("active_goal")
        blocked_goal = snapshot.get("blocked_goal")
        active_critic = snapshot.get("active_critic")
        resolved_critic = snapshot.get("resolved_critic")
        active_self_model = snapshot.get("active_self_model")
        uncertain_self_model = snapshot.get("uncertain_self_model")
        live_reflection = snapshot.get("live_reflection")
        settled_reflection = snapshot.get("settled_reflection")
        active_recurrence = snapshot.get("active_recurrence")
        softening_recurrence = snapshot.get("softening_recurrence")
        open_loop = snapshot.get("open_loop")
        softening_loop = snapshot.get("softening_loop")
        title_suffix = _domain_title(domain_key)

        if (open_loop and str(open_loop.get("signal_type") or "") == "persistent-open-loop" and active_critic and (active_focus or active_goal or blocked_goal)) or (
            active_critic and active_recurrence and (active_focus or active_goal or blocked_goal)
        ):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="challenge-direction",
                    status="active",
                    title=f"Challenge direction: {title_suffix}",
                    summary=f"This bounded direction around {title_suffix.lower()} now looks like it should face internal challenge rather than simple continuation.",
                    rationale="Persistent unresolved pressure is still pushing against an active focus or goal in the same domain.",
                    status_reason="Active critic pressure and recurring/open-loop evidence make this direction a candidate for bounded internal opposition.",
                    source_items=[active_focus, active_goal, blocked_goal, active_critic, active_recurrence, open_loop],
                )
            )
            continue

        if (active_focus or active_goal) and (active_self_model or uncertain_self_model) and (active_critic or open_loop or active_recurrence):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="challenge-calibration",
                    status="active",
                    title=f"Challenge calibration: {title_suffix}",
                    summary=f"This bounded calibration thread around {title_suffix.lower()} now looks like it should be challenged internally.",
                    rationale="Active direction is still being carried while self-model pressure and critic/open-loop recurrence suggest the current calibration should not be accepted too easily.",
                    status_reason="Self-model pressure plus continuing direction keeps this domain in need of bounded internal challenge.",
                    source_items=[active_focus, active_goal, active_self_model, uncertain_self_model, active_critic, open_loop, active_recurrence],
                )
            )
            continue

        if (softening_loop or softening_recurrence or resolved_critic) and (active_self_model or uncertain_self_model or live_reflection) and not active_critic and not blocked_goal:
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="challenge-calibration",
                    status="softening",
                    title=f"Softening challenge: {title_suffix}",
                    summary=f"This bounded calibration thread around {title_suffix.lower()} may still benefit from challenge, but the pressure is easing.",
                    rationale="The domain still carries some calibration uncertainty, but the sharper critic/open-loop pressure has eased into a softer challenge need.",
                    status_reason="Internal challenge still looks relevant, though the thread is now softening rather than sharply opposed.",
                    source_items=[active_focus, active_goal, active_self_model, uncertain_self_model, live_reflection, softening_loop, softening_recurrence, resolved_critic, settled_reflection],
                )
            )

    if world_uncertain_signals and (active_goal_count > 0 or open_loop_surface.get("active")):
        item = world_uncertain_signals[0]
        title_suffix = str(item.get("title") or "Current world view").replace("Current ", "")
        status = "active" if open_loop_surface.get("summary", {}).get("open_count") else "softening"
        candidates.append(
            _build_candidate(
                domain_key=f"world:{_world_domain_key(str(item.get('canonical_key') or ''))}",
                signal_type="challenge-world-view",
                status=status,
                title=f"Challenge world view: {title_suffix}",
                summary="A bounded situational assumption now looks uncertain enough that Jarvis should visibly keep it challengeable.",
                rationale="An uncertain world-model thread is still present while active direction or unresolved loops remain live elsewhere in runtime truth.",
                status_reason="Situational understanding remains bounded and challengeable while work direction is still live.",
                source_items=[item],
            )
        )

    return candidates[:4]


def _persist_internal_opposition_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_internal_opposition_signal(
            signal_id=f"opposition-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "internal-opposition"),
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
        superseded_count = supersede_runtime_internal_opposition_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded internal-opposition reading for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "internal_opposition_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "internal_opposition_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "internal_opposition_signal.updated",
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
        "canonical_key": f"internal-opposition:{signal_type}:{domain_key}",
        "domain_key": domain_key,
        "status": status,
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": "runtime-derived-support",
        "confidence": confidence,
        "evidence_summary": _merge_fragments(*[str(item.get("evidence_summary") or "") for item in items]),
        "support_summary": _merge_fragments(*[str(item.get("support_summary") or "") for item in items]),
        "support_count": support_count,
        "session_count": session_count,
        "status_reason": status_reason,
    }


def _focus_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _goal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 2 else ""


def _critic_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 4 else ""


def _self_model_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _reflection_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _temporal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _open_loop_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _world_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else "world-view"


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("world:", "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Internal challenge"


def _merge_fragments(*parts: str) -> str:
    seen: list[str] = []
    for part in parts:
        text = " ".join(str(part or "").split()).strip()
        if not text or text in seen:
            continue
        seen.append(text)
    return " | ".join(seen[:4])


def _parse_dt(raw: str) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
