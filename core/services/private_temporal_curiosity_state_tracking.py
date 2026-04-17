from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_private_initiative_tension_signals,
    list_runtime_private_state_snapshots,
    list_runtime_private_temporal_curiosity_states,
    supersede_runtime_private_temporal_curiosity_states_for_focus,
    update_runtime_private_temporal_curiosity_state_status,
    upsert_runtime_private_temporal_curiosity_state,
)

_STALE_AFTER_DAYS = 7


def track_runtime_private_temporal_curiosity_states_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    candidate = _extract_candidate_for_run(run_id=run_id)
    if candidate is None:
        return {
            "created": 0,
            "updated": 0,
            "items": [],
            "summary": "No bounded temporal-curiosity grounding was available for this visible turn.",
        }

    persisted = _persist_private_temporal_curiosity_states(
        states=[candidate],
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in persisted if item.get("was_created")]),
        "updated": len([item for item in persisted if item.get("was_updated")]),
        "items": persisted,
        "summary": (
            "Tracked 1 bounded temporal-curiosity runtime support state."
            if persisted
            else "No bounded temporal-curiosity runtime support state warranted tracking."
        ),
    }


def refresh_runtime_private_temporal_curiosity_state_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_private_temporal_curiosity_states(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_private_temporal_curiosity_state_status(
            str(item.get("state_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded temporal-curiosity inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "private_temporal_curiosity_state.stale",
            {
                "state_id": refreshed_item.get("state_id"),
                "state_type": refreshed_item.get("state_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_private_temporal_curiosity_state_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_private_temporal_curiosity_state_statuses()
    items = list_runtime_private_temporal_curiosity_states(limit=max(limit, 1))
    enriched_items = [_with_surface_view(item) for item in items]
    active = [item for item in enriched_items if str(item.get("status") or "") == "active"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
    ordered = [*active, *stale, *superseded]
    latest = next(iter(active or stale or superseded), None)
    return {
        "active": bool(active),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_state": str((latest or {}).get("title") or "No active temporal-curiosity support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_curiosity_type": str((latest or {}).get("curiosity_type") or "none"),
            "current_pull": str((latest or {}).get("curiosity_pull") or "low"),
            "current_confidence": str((latest or {}).get("curiosity_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    private_state = _latest_private_state_snapshot(run_id=run_id)
    tension = _latest_initiative_tension_support(run_id=run_id)
    if private_state is None or tension is None:
        return None

    tension_type = _value(
        tension.get("tension_type"),
        _canonical_segment(str(tension.get("canonical_key") or ""), index=1),
        default="retention-pull",
    )
    state_pressure = _value(private_state.get("state_pressure"), default="low")
    if tension_type not in {"curiosity-pull", "unresolved"} and state_pressure != "medium":
        return None

    focus = _focus_key(private_state, tension)
    curiosity_type = (
        "active-observation"
        if tension_type == "curiosity-pull"
        else "watchful-followup"
    )
    curiosity_pull = "medium" if state_pressure == "medium" or tension_type == "curiosity-pull" else "low"
    curiosity_target = str(
        tension.get("tension_target")
        or tension.get("title")
        or focus.replace("-", " ")
    ).strip()[:96]
    curiosity_summary = _merge_fragments(
        str(private_state.get("state_summary") or ""),
        str(tension.get("tension_summary") or tension.get("summary") or ""),
    )[:220]
    curiosity_confidence = _stronger_confidence(
        str(private_state.get("state_confidence") or private_state.get("confidence") or "low"),
        str(tension.get("tension_confidence") or tension.get("confidence") or "low"),
    )
    source_anchor = _merge_fragments(
        _support_anchor(private_state),
        _support_anchor(tension),
    )

    return {
        "state_type": "private-temporal-curiosity",
        "canonical_key": f"private-temporal-curiosity:{curiosity_type}:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Private temporal curiosity support: {curiosity_target}",
        "summary": (
            f"Bounded runtime temporal curiosity is keeping a small forward-looking pull around {curiosity_target.lower()}."
        ),
        "rationale": (
            "A bounded temporal-curiosity support state may return only when current private-state support and initiative-tension support already indicate a live pull, without becoming a planner, executor, or broad curiosity engine."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": curiosity_confidence,
        "evidence_summary": _merge_fragments(
            str(private_state.get("evidence_summary") or ""),
            str(tension.get("evidence_summary") or ""),
        ),
        "support_summary": _merge_fragments(
            "Derived only from active bounded private-state and initiative-tension runtime support.",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "Bounded temporal curiosity remains subordinate to visible/runtime truth and carries no planner, execution, prompt, or canonical-self authority."
        ),
        "curiosity_type": curiosity_type,
        "curiosity_target": curiosity_target,
        "curiosity_pull": curiosity_pull,
        "curiosity_summary": curiosity_summary,
        "curiosity_confidence": curiosity_confidence,
        "source_anchor": source_anchor,
        "state_snapshot_id": str(private_state.get("snapshot_id") or ""),
        "tension_signal_id": str(tension.get("signal_id") or ""),
        "grounding_mode": "private-state+initiative-tension",
    }


def _persist_private_temporal_curiosity_states(
    *,
    states: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for state in states:
        persisted_item = upsert_runtime_private_temporal_curiosity_state(
            state_id=f"private-temporal-curiosity-state-{uuid4().hex}",
            state_type=str(state.get("state_type") or "private-temporal-curiosity"),
            canonical_key=str(state.get("canonical_key") or ""),
            status=str(state.get("status") or "active"),
            title=str(state.get("title") or ""),
            summary=str(state.get("summary") or ""),
            rationale=str(state.get("rationale") or ""),
            source_kind=str(state.get("source_kind") or "runtime-derived-support"),
            confidence=str(state.get("confidence") or "low"),
            evidence_summary=str(state.get("evidence_summary") or ""),
            support_summary=str(state.get("support_summary") or ""),
            status_reason=str(state.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
            support_count=int(state.get("support_count") or 1),
            session_count=int(state.get("session_count") or 1),
            created_at=now,
            updated_at=now,
        )
        superseded_count = supersede_runtime_private_temporal_curiosity_states_for_focus(
            focus_key=str(state.get("focus_key") or ""),
            exclude_state_id=str(persisted_item.get("state_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded temporal-curiosity runtime support state for the same visible-work focus.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "private_temporal_curiosity_state.superseded",
                {
                    "state_id": persisted_item.get("state_id"),
                    "state_type": persisted_item.get("state_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "private_temporal_curiosity_state.created",
                {
                    "state_id": persisted_item.get("state_id"),
                    "state_type": persisted_item.get("state_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "private_temporal_curiosity_state.updated",
                {
                    "state_id": persisted_item.get("state_id"),
                    "state_type": persisted_item.get("state_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, state))
    return persisted


def _latest_private_state_snapshot(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_state_snapshots(limit=12):
        if str(item.get("run_id") or "") != str(run_id or ""):
            continue
        if str(item.get("status") or "") != "active":
            continue
        return item
    return None


def _latest_initiative_tension_support(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_initiative_tension_signals(limit=12):
        if str(item.get("run_id") or "") != str(run_id or ""):
            continue
        if str(item.get("status") or "") != "active":
            continue
        return item
    return None


def _with_runtime_view(item: dict[str, object], state: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["curiosity_type"] = str(state.get("curiosity_type") or "watchful-followup")
    enriched["curiosity_target"] = str(state.get("curiosity_target") or "")
    enriched["curiosity_pull"] = str(state.get("curiosity_pull") or "low")
    enriched["curiosity_summary"] = str(state.get("curiosity_summary") or "")
    enriched["curiosity_confidence"] = str(
        state.get("curiosity_confidence") or state.get("confidence") or "low"
    )
    enriched["source_anchor"] = str(state.get("source_anchor") or "")
    enriched["state_snapshot_id"] = str(state.get("state_snapshot_id") or "")
    enriched["tension_signal_id"] = str(state.get("tension_signal_id") or "")
    enriched["grounding_mode"] = str(state.get("grounding_mode") or "private-state+initiative-tension")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    canonical_key = str(item.get("canonical_key") or "")
    inferred_type = _canonical_segment(canonical_key, index=1) or "watchful-followup"
    enriched["curiosity_type"] = str(item.get("curiosity_type") or inferred_type)
    enriched["curiosity_target"] = str(item.get("curiosity_target") or _title_target(str(item.get("title") or "")))
    enriched["curiosity_pull"] = str(item.get("curiosity_pull") or _pull_from_type(inferred_type))
    enriched["curiosity_summary"] = str(item.get("curiosity_summary") or item.get("summary") or "")
    enriched["curiosity_confidence"] = str(
        item.get("curiosity_confidence") or item.get("confidence") or "low"
    )
    enriched["source_anchor"] = str(item.get("source_anchor") or item.get("support_summary") or item.get("state_id") or "")
    enriched["state_snapshot_id"] = str(item.get("state_snapshot_id") or "")
    enriched["tension_signal_id"] = str(item.get("tension_signal_id") or "")
    enriched["grounding_mode"] = str(item.get("grounding_mode") or "private-state+initiative-tension")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["source"] = "/mc/runtime.private_temporal_curiosity_state"
    return enriched


def _support_anchor(item: dict[str, object]) -> str:
    item_id = str(item.get("state_id") or item.get("snapshot_id") or item.get("signal_id") or "").strip()
    title = str(item.get("title") or "").strip()
    if item_id and title:
        return f"{item_id}:{title}"[:140]
    return (item_id or title)[:140]


def _focus_key(*items: dict[str, object]) -> str:
    for item in items:
        canonical_key = str(item.get("canonical_key") or "").strip()
        parts = [part.strip() for part in canonical_key.split(":") if part.strip()]
        if parts:
            tail = parts[-1]
            if tail:
                return tail[:96]
    return "visible-work"


def _stronger_confidence(*values: str) -> str:
    ordered = {"low": 0, "medium": 1, "high": 2}
    best = "low"
    best_score = -1
    for value in values:
        normalized = str(value or "").strip().lower()
        if normalized not in ordered:
            continue
        score = ordered[normalized]
        if score > best_score:
            best = normalized
            best_score = score
    return best


def _canonical_segment(value: str, *, index: int) -> str:
    parts = [part.strip() for part in str(value or "").split(":") if part.strip()]
    if len(parts) <= index:
        return ""
    return parts[index][:96]


def _value(*candidates: object, default: str) -> str:
    for candidate in candidates:
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized[:96]
    return default


def _pull_from_type(curiosity_type: str) -> str:
    if str(curiosity_type or "").strip() == "active-observation":
        return "medium"
    return "low"


def _title_target(title: str) -> str:
    normalized = str(title or "").strip()
    prefix = "Private temporal curiosity support:"
    if normalized.startswith(prefix):
        return normalized[len(prefix) :].strip()
    return normalized[:96]


def _merge_fragments(*parts: str) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return " | ".join(merged[:4])


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
