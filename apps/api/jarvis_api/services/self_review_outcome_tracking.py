from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.internal_opposition_signal_tracking import (
    build_runtime_internal_opposition_signal_surface,
)
from apps.api.jarvis_api.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from apps.api.jarvis_api.services.self_review_run_tracking import (
    build_runtime_self_review_run_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_self_review_outcomes,
    list_runtime_witness_signals,
    supersede_runtime_self_review_outcomes_for_domain,
    update_runtime_self_review_outcome_status,
    upsert_runtime_self_review_outcome,
)

_STALE_AFTER_DAYS = 14


def track_runtime_self_review_outcomes_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_self_review_outcomes(
        outcomes=_extract_self_review_outcome_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded self-review outcomes."
            if items
            else "No bounded self-review outcome warranted tracking."
        ),
    }


def refresh_runtime_self_review_outcome_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_self_review_outcomes(limit=40):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_self_review_outcome_status(
            str(item.get("outcome_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded self-review outcome inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "self_review_outcome.stale",
            {
                "outcome_id": refreshed_item.get("outcome_id"),
                "outcome_type": refreshed_item.get("outcome_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_self_review_outcome_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_self_review_outcome_statuses()
    items = list_runtime_self_review_outcomes(limit=max(limit, 1))
    snapshots = _build_outcome_snapshots()
    enriched_items = [_with_surface_outcome_view(item, snapshots=snapshots) for item in items]
    fresh = [item for item in enriched_items if str(item.get("status") or "") == "fresh"]
    active = [item for item in enriched_items if str(item.get("status") or "") == "active"]
    fading = [item for item in enriched_items if str(item.get("status") or "") == "fading"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
    ordered = [*fresh, *active, *fading, *stale, *superseded]
    latest = next(iter(fresh or active or fading or stale or superseded), None)
    return {
        "active": bool(fresh or active or fading),
        "items": ordered,
        "summary": {
            "fresh_count": len(fresh),
            "active_count": len(active),
            "fading_count": len(fading),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_outcome": str((latest or {}).get("title") or "No active self-review outcome"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_outcome_type": str((latest or {}).get("outcome_type") or "none"),
            "current_review_focus": str((latest or {}).get("review_focus") or "none"),
        },
    }


def _extract_self_review_outcome_candidates() -> list[dict[str, object]]:
    snapshots = _build_outcome_snapshots()
    candidates: list[dict[str, object]] = []

    for item in build_runtime_self_review_run_surface(limit=12).get("items", []):
        run_status = str(item.get("status") or "")
        if run_status not in {"fresh", "active", "fading"}:
            continue
        domain_key = _self_review_outcome_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        snapshot = snapshots.get(domain_key) or {}
        if not any(
            snapshot.get(key)
            for key in ("open_loop", "softening_loop", "active_opposition", "softening_opposition", "active_focus", "active_goal", "blocked_goal", "witness")
        ):
            continue
        title_suffix = _domain_title(domain_key)
        review_type = str(item.get("review_type") or item.get("run_type") or "self-review-run")
        outcome_type = _build_outcome_type(item=item, snapshot=snapshot)
        short_outcome = _build_short_outcome(outcome_type=outcome_type, snapshot=snapshot)
        source_items = [
            item,
            snapshot.get("open_loop"),
            snapshot.get("softening_loop"),
            snapshot.get("active_opposition"),
            snapshot.get("softening_opposition"),
            snapshot.get("active_focus"),
            snapshot.get("active_goal"),
            snapshot.get("blocked_goal"),
            snapshot.get("witness"),
        ]
        candidates.append(
            {
                "outcome_type": outcome_type,
                "canonical_key": f"self-review-outcome:{review_type}:{domain_key}",
                "domain_key": domain_key,
                "status": run_status,
                "title": f"Self-review outcome: {title_suffix}",
                "summary": short_outcome,
                "rationale": str(item.get("short_review_note") or item.get("summary") or "")
                or "A bounded self-review snapshot now materializes as a small review outcome.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(
                    str(item.get("confidence") or "low"),
                    str(item.get("closure_confidence") or ""),
                ),
                "evidence_summary": _merge_fragments(
                    *[str(source.get("evidence_summary") or "") for source in source_items if source]
                ),
                "support_summary": _merge_fragments(
                    *[str(source.get("support_summary") or "") for source in source_items if source],
                    str(item.get("review_focus") or ""),
                    short_outcome,
                ),
                "support_count": max([int(source.get("support_count") or 1) for source in source_items if source], default=1),
                "session_count": max([int(source.get("session_count") or 1) for source in source_items if source], default=1),
                "status_reason": _build_status_reason(outcome_type=outcome_type),
                "review_focus": str(item.get("review_focus") or "bounded-self-review"),
                "review_type": review_type,
                "closure_confidence": str(item.get("closure_confidence") or "low"),
                "short_outcome": short_outcome,
            }
        )

    return candidates[:4]


def _persist_self_review_outcomes(
    *,
    outcomes: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    existing_by_key = {
        str(item.get("canonical_key") or ""): item for item in list_runtime_self_review_outcomes(limit=40)
    }
    persisted: list[dict[str, object]] = []
    for outcome in outcomes:
        existing = existing_by_key.get(str(outcome.get("canonical_key") or ""))
        persisted_item = upsert_runtime_self_review_outcome(
            outcome_id=f"self-review-outcome-{uuid4().hex}",
            outcome_type=str(outcome.get("outcome_type") or "watch-closely"),
            canonical_key=str(outcome.get("canonical_key") or ""),
            status="active" if existing and str(outcome.get("status") or "") == "fresh" else str(outcome.get("status") or "fresh"),
            title=str(outcome.get("title") or ""),
            summary=str(outcome.get("short_outcome") or outcome.get("summary") or ""),
            rationale=str(outcome.get("rationale") or ""),
            source_kind=str(outcome.get("source_kind") or "runtime-derived-support"),
            confidence=str(outcome.get("confidence") or "low"),
            evidence_summary=str(outcome.get("evidence_summary") or ""),
            support_summary=str(outcome.get("support_summary") or ""),
            support_count=int(outcome.get("support_count") or 1),
            session_count=int(outcome.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(outcome.get("status_reason") or ""),
            review_run_id=run_id,
            session_id=session_id,
        )
        superseded_count = supersede_runtime_self_review_outcomes_for_domain(
            domain_key=str(outcome.get("domain_key") or ""),
            exclude_outcome_id=str(persisted_item.get("outcome_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded self-review outcome for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "self_review_outcome.superseded",
                {
                    "outcome_id": persisted_item.get("outcome_id"),
                    "outcome_type": persisted_item.get("outcome_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "self_review_outcome.created",
                {
                    "outcome_id": persisted_item.get("outcome_id"),
                    "outcome_type": persisted_item.get("outcome_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "self_review_outcome.updated",
                {
                    "outcome_id": persisted_item.get("outcome_id"),
                    "outcome_type": persisted_item.get("outcome_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_outcome_view(persisted_item, outcome))
    return persisted


def _build_outcome_snapshots() -> dict[str, dict[str, object]]:
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

    for witness in list_runtime_witness_signals(limit=18):
        status = str(witness.get("status") or "")
        if status not in {"fresh", "carried"}:
            continue
        domain_key = _witness_domain_key(str(witness.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["witness"] = witness

    for item in build_runtime_open_loop_signal_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"open", "softening", "closed"}:
            continue
        domain_key = _open_loop_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "open":
            bucket["open_loop"] = item
        else:
            bucket["softening_loop"] = item

    for item in build_runtime_internal_opposition_signal_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _internal_opposition_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_opposition"] = item
        else:
            bucket["softening_opposition"] = item

    return snapshots


def _with_outcome_view(item: dict[str, object], outcome: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["domain"] = _self_review_outcome_domain_key(str(item.get("canonical_key") or ""))
    enriched["review_type"] = str(outcome.get("review_type") or "self-review-run")
    enriched["review_focus"] = str(outcome.get("review_focus") or "bounded-self-review")
    enriched["closure_confidence"] = str(outcome.get("closure_confidence") or "low")
    enriched["short_outcome"] = str(outcome.get("short_outcome") or item.get("summary") or "")
    return enriched


def _with_surface_outcome_view(item: dict[str, object], *, snapshots: dict[str, dict[str, object]]) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _self_review_outcome_domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key) or {}
    enriched["domain"] = domain_key
    enriched["review_type"] = _review_type_from_key(str(item.get("canonical_key") or ""))
    enriched["review_focus"] = _build_review_focus(snapshot=snapshot)
    enriched["closure_confidence"] = _closure_confidence_from_snapshot(snapshot=snapshot)
    enriched["short_outcome"] = str(item.get("summary") or _build_short_outcome(outcome_type=str(item.get("outcome_type") or "watch-closely"), snapshot=snapshot))
    return enriched


def _build_outcome_type(*, item: dict[str, object], snapshot: dict[str, object]) -> str:
    if snapshot.get("open_loop") and snapshot.get("active_opposition"):
        return "challenge-further"
    if snapshot.get("open_loop") or snapshot.get("blocked_goal"):
        return "watch-closely"
    if snapshot.get("witness") and (
        snapshot.get("softening_loop")
        or snapshot.get("softening_opposition")
        or str(item.get("status") or "") == "fading"
    ):
        return "carry-forward"
    if snapshot.get("softening_loop") or snapshot.get("softening_opposition") or str(item.get("closure_confidence") or "") == "high":
        return "nearing-closure"
    return "watch-closely"


def _build_short_outcome(*, outcome_type: str, snapshot: dict[str, object]) -> str:
    if outcome_type == "challenge-further":
        return "The review still points toward further challenge before this thread should settle."
    if outcome_type == "carry-forward":
        return "The review points toward carrying the lesson forward without widening the thread."
    if outcome_type == "nearing-closure":
        return "The review points toward a bounded settling path if the current easing holds."
    if snapshot.get("blocked_goal"):
        return "The review points toward keeping this thread visibly open while blocked direction remains live."
    return "The review points toward keeping this thread visibly open and closely watched."


def _build_status_reason(*, outcome_type: str) -> str:
    if outcome_type == "challenge-further":
        return "Bounded self-review still points toward further challenge before settling."
    if outcome_type == "carry-forward":
        return "Bounded self-review points toward carrying this lesson forward without widening the thread."
    if outcome_type == "nearing-closure":
        return "Bounded self-review points toward a narrowing path to settling if the easing holds."
    return "Bounded self-review points toward keeping this thread closely watched for now."


def _build_review_focus(*, snapshot: dict[str, object]) -> str:
    parts: list[str] = []
    if snapshot.get("open_loop"):
        parts.append("open-loop pressure")
    elif snapshot.get("softening_loop"):
        parts.append("softening loop")
    if snapshot.get("active_opposition"):
        parts.append("active opposition")
    elif snapshot.get("softening_opposition"):
        parts.append("softening opposition")
    if snapshot.get("blocked_goal"):
        parts.append("blocked direction")
    elif snapshot.get("active_goal"):
        parts.append("active direction")
    if snapshot.get("witness"):
        parts.append("carried lesson")
    return " + ".join(parts[:3]) or "bounded-self-review"


def _closure_confidence_from_snapshot(*, snapshot: dict[str, object]) -> str:
    open_loop = snapshot.get("open_loop") or snapshot.get("softening_loop") or {}
    return str(open_loop.get("closure_confidence") or "low")


def _stronger_confidence(*values: str) -> str:
    ordered = [str(value or "").strip() for value in values if str(value or "").strip()]
    if "high" in ordered:
        return "high"
    if "medium" in ordered:
        return "medium"
    return ordered[0] if ordered else "low"


def _focus_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _goal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 2 else ""


def _witness_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _open_loop_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _internal_opposition_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _self_review_outcome_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _review_type_from_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[1] if len(parts) >= 3 else "self-review-run"


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Self-review"


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
