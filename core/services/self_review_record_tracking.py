from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.internal_opposition_signal_tracking import (
    build_runtime_internal_opposition_signal_surface,
)
from core.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from core.services.self_review_signal_tracking import (
    build_runtime_self_review_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflection_signals,
    list_runtime_self_review_records,
    list_runtime_witness_signals,
    supersede_runtime_self_review_records_for_domain,
    update_runtime_self_review_record_status,
    upsert_runtime_self_review_record,
)

_STALE_AFTER_DAYS = 14


def track_runtime_self_review_records_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_self_review_records(
        records=_extract_self_review_record_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded self-review records."
            if items
            else "No bounded self-review record warranted tracking."
        ),
    }


def refresh_runtime_self_review_record_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_self_review_records(limit=40):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_self_review_record_status(
            str(item.get("record_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded self-review record inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "self_review_record.stale",
            {
                "record_id": refreshed_item.get("record_id"),
                "record_type": refreshed_item.get("record_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_self_review_record_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_self_review_record_statuses()
    items = list_runtime_self_review_records(limit=max(limit, 1))
    snapshots = _build_review_brief_snapshots()
    enriched_items = [_with_review_brief(item, snapshots=snapshots) for item in items]
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
            "current_record": str((latest or {}).get("title") or "No active self-review record"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_review_type": str((latest or {}).get("review_type") or "none"),
        },
    }


def _extract_self_review_record_candidates() -> list[dict[str, object]]:
    snapshots = _build_review_brief_snapshots()
    candidates: list[dict[str, object]] = []

    for item in build_runtime_self_review_signal_surface(limit=12).get("items", []):
        signal_status = str(item.get("status") or "")
        if signal_status not in {"active", "softening"}:
            continue
        domain_key = _self_review_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        snapshot = snapshots.get(domain_key) or {}
        if not any(
            snapshot.get(key)
            for key in (
                "open_loop",
                "softening_loop",
                "active_opposition",
                "softening_opposition",
                "active_focus",
                "active_goal",
                "blocked_goal",
                "settled_reflection",
                "fresh_witness",
                "carried_witness",
            )
        ):
            continue
        title_suffix = _domain_title(domain_key)
        record_type = str(item.get("signal_type") or "self-review-brief")
        source_items = [
            item,
            snapshot.get("open_loop"),
            snapshot.get("softening_loop"),
            snapshot.get("active_opposition"),
            snapshot.get("softening_opposition"),
            snapshot.get("active_focus"),
            snapshot.get("active_goal"),
            snapshot.get("blocked_goal"),
            snapshot.get("settled_reflection"),
            snapshot.get("fresh_witness"),
            snapshot.get("carried_witness"),
        ]
        candidates.append(
            {
                "record_type": record_type,
                "canonical_key": f"self-review-record:{record_type}:{domain_key}",
                "domain_key": domain_key,
                "status": "fresh" if signal_status == "active" else "fading",
                "title": f"Self-review brief: {title_suffix}",
                "summary": _build_review_summary(title_suffix=title_suffix, snapshot=snapshot),
                "rationale": str(item.get("rationale") or "") or "Bounded self-review signal remains active enough to warrant a small review brief.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(
                    str(item.get("confidence") or "low"),
                    str(((snapshot.get("open_loop") or snapshot.get("softening_loop") or {}).get("closure_confidence") or "")),
                ),
                "evidence_summary": _merge_fragments(
                    *[str(source.get("evidence_summary") or "") for source in source_items if source]
                ),
                "support_summary": _merge_fragments(
                    *[str(source.get("support_summary") or "") for source in source_items if source]
                ),
                "support_count": max([int(source.get("support_count") or 1) for source in source_items if source], default=1),
                "session_count": max([int(source.get("session_count") or 1) for source in source_items if source], default=1),
                "status_reason": _build_short_reason(snapshot=snapshot, fallback=str(item.get("status_reason") or "")),
            }
        )
    return candidates[:4]


def _persist_self_review_records(
    *,
    records: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    existing_by_key = {
        str(item.get("canonical_key") or ""): item for item in list_runtime_self_review_records(limit=40)
    }
    persisted: list[dict[str, object]] = []
    for record in records:
        desired_status = str(record.get("status") or "fresh")
        existing = existing_by_key.get(str(record.get("canonical_key") or ""))
        persisted_item = upsert_runtime_self_review_record(
            record_id=f"self-review-record-{uuid4().hex}",
            record_type=str(record.get("record_type") or "self-review-brief"),
            canonical_key=str(record.get("canonical_key") or ""),
            status="active" if existing and desired_status == "fresh" else desired_status,
            title=str(record.get("title") or ""),
            summary=str(record.get("summary") or ""),
            rationale=str(record.get("rationale") or ""),
            source_kind=str(record.get("source_kind") or "runtime-derived-support"),
            confidence=str(record.get("confidence") or "low"),
            evidence_summary=str(record.get("evidence_summary") or ""),
            support_summary=str(record.get("support_summary") or ""),
            support_count=int(record.get("support_count") or 1),
            session_count=int(record.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(record.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        superseded_count = supersede_runtime_self_review_records_for_domain(
            domain_key=str(record.get("domain_key") or ""),
            exclude_record_id=str(persisted_item.get("record_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded self-review brief for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "self_review_record.superseded",
                {
                    "record_id": persisted_item.get("record_id"),
                    "record_type": persisted_item.get("record_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "self_review_record.created",
                {
                    "record_id": persisted_item.get("record_id"),
                    "record_type": persisted_item.get("record_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "self_review_record.updated",
                {
                    "record_id": persisted_item.get("record_id"),
                    "record_type": persisted_item.get("record_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _build_review_brief_snapshots() -> dict[str, dict[str, object]]:
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

    for reflection in list_runtime_reflection_signals(limit=18):
        if str(reflection.get("status") or "") != "settled":
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["settled_reflection"] = reflection

    for witness in list_runtime_witness_signals(limit=18):
        status = str(witness.get("status") or "")
        if status not in {"fresh", "carried"}:
            continue
        domain_key = _witness_domain_key(str(witness.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "fresh":
            bucket["fresh_witness"] = witness
        else:
            bucket["carried_witness"] = witness

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


def _with_review_brief(item: dict[str, object], *, snapshots: dict[str, dict[str, object]]) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _self_review_record_domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key) or {}
    open_loop = snapshot.get("open_loop") or snapshot.get("softening_loop") or {}
    opposition = snapshot.get("active_opposition") or snapshot.get("softening_opposition") or {}
    enriched["domain"] = domain_key
    enriched["review_type"] = str(item.get("record_type") or "self-review-brief")
    enriched["trigger"] = str(item.get("record_type") or "self-review-brief")
    enriched["open_loop_status"] = str(open_loop.get("status") or "none")
    enriched["opposition_status"] = str(opposition.get("status") or "none")
    enriched["closure_readiness"] = str(open_loop.get("closure_readiness") or "low")
    enriched["closure_confidence"] = str(open_loop.get("closure_confidence") or "low")
    enriched["short_reason"] = _build_short_reason(snapshot=snapshot, fallback=str(item.get("status_reason") or ""))
    return enriched


def _build_review_summary(*, title_suffix: str, snapshot: dict[str, object]) -> str:
    open_loop = snapshot.get("open_loop") or snapshot.get("softening_loop")
    opposition = snapshot.get("active_opposition") or snapshot.get("softening_opposition")
    phrases = [f"Review {title_suffix.lower()}."]
    if open_loop:
        phrases.append(f"Loop is {str(open_loop.get('status') or 'open')}.")
    if opposition:
        phrases.append(f"Opposition is {str(opposition.get('status') or 'active')}.")
    if snapshot.get("settled_reflection"):
        phrases.append("Settled reflection is present.")
    if snapshot.get("fresh_witness") or snapshot.get("carried_witness"):
        phrases.append("A carried lesson is still visible.")
    return " ".join(phrases[:4])


def _build_short_reason(*, snapshot: dict[str, object], fallback: str) -> str:
    open_loop = snapshot.get("open_loop") or snapshot.get("softening_loop") or {}
    if str(open_loop.get("closure_reason") or "").strip():
        return str(open_loop.get("closure_reason") or "")
    opposition = snapshot.get("active_opposition") or snapshot.get("softening_opposition") or {}
    if str(opposition.get("status_reason") or "").strip():
        return str(opposition.get("status_reason") or "")
    return fallback


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


def _reflection_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _witness_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _open_loop_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _internal_opposition_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _self_review_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _self_review_record_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


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
