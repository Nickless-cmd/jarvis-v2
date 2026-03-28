from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.chronicle_consolidation_signal_tracking import (
    build_runtime_chronicle_consolidation_signal_surface,
)
from apps.api.jarvis_api.services.executive_contradiction_signal_tracking import (
    build_runtime_executive_contradiction_signal_surface,
)
from apps.api.jarvis_api.services.private_temporal_promotion_signal_tracking import (
    build_runtime_private_temporal_promotion_signal_surface,
)
from apps.api.jarvis_api.services.remembered_fact_signal_tracking import (
    build_runtime_remembered_fact_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_chronicle_consolidation_briefs,
    supersede_runtime_chronicle_consolidation_briefs_for_domain,
    update_runtime_chronicle_consolidation_brief_status,
    upsert_runtime_chronicle_consolidation_brief,
)

_STALE_AFTER_DAYS = 14
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_chronicle_consolidation_briefs_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_chronicle_consolidation_briefs(
        briefs=_extract_chronicle_consolidation_brief_candidates(run_id=run_id),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded chronicle/consolidation briefs."
            if items
            else "No bounded chronicle/consolidation brief warranted tracking."
        ),
    }


def refresh_runtime_chronicle_consolidation_brief_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_chronicle_consolidation_briefs(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_chronicle_consolidation_brief_status(
            str(item.get("brief_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded chronicle/consolidation brief inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "chronicle_consolidation_brief.stale",
            {
                "brief_id": refreshed_item.get("brief_id"),
                "brief_type": refreshed_item.get("brief_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_chronicle_consolidation_brief_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_chronicle_consolidation_brief_statuses()
    items = list_runtime_chronicle_consolidation_briefs(limit=max(limit, 1))
    enriched_items = [_with_surface_view(item) for item in items]
    active = [item for item in enriched_items if str(item.get("status") or "") == "active"]
    softening = [item for item in enriched_items if str(item.get("status") or "") == "softening"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
    ordered = [*active, *softening, *stale, *superseded]
    latest = next(iter(active or softening or stale or superseded), None)
    return {
        "active": bool(active or softening),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "writeback_state": "not-writing-to-canonical-files",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_brief": str((latest or {}).get("title") or "No active chronicle/consolidation brief"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_brief_type": str((latest or {}).get("brief_type") or "none"),
            "current_weight": str((latest or {}).get("brief_weight") or "low"),
            "current_confidence": str((latest or {}).get("brief_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "writeback_state": "not-writing-to-canonical-files",
        },
    }


def _extract_chronicle_consolidation_brief_candidates(*, run_id: str) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for item in build_runtime_chronicle_consolidation_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("chronicle_confidence") or item.get("confidence") or "low") not in {"medium", "high"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["chronicle_signal"] = item

    for item in build_runtime_private_temporal_promotion_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["temporal_promotion"] = item

    for item in build_runtime_remembered_fact_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["remembered_fact"] = item

    for item in build_runtime_executive_contradiction_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["executive_contradiction"] = item

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        chronicle_signal = snapshot.get("chronicle_signal")
        if chronicle_signal is None:
            continue
        temporal_promotion = snapshot.get("temporal_promotion")
        remembered_fact = snapshot.get("remembered_fact")
        executive_contradiction = snapshot.get("executive_contradiction")

        brief_type = _brief_type(
            chronicle_type=str(chronicle_signal.get("chronicle_type") or ""),
            has_remembered_fact=remembered_fact is not None,
            has_temporal_promotion=temporal_promotion is not None,
        )
        brief_focus = str(chronicle_signal.get("chronicle_focus") or _focus_title(domain_key)).strip()[:96]
        brief_weight = _brief_weight(
            chronicle_weight=str(chronicle_signal.get("chronicle_weight") or "low"),
            contradiction_pressure=str((executive_contradiction or {}).get("control_pressure") or ""),
            has_temporal_promotion=temporal_promotion is not None,
        )
        brief_reason = _merge_fragments(
            str(chronicle_signal.get("chronicle_summary") or chronicle_signal.get("summary") or ""),
            str((temporal_promotion or {}).get("promotion_summary") or ""),
            str((remembered_fact or {}).get("signal_summary") or (remembered_fact or {}).get("summary") or ""),
            str((executive_contradiction or {}).get("control_summary") or (executive_contradiction or {}).get("summary") or ""),
        )[:220]
        brief_confidence = _stronger_confidence(
            str(chronicle_signal.get("chronicle_confidence") or chronicle_signal.get("confidence") or "low"),
            str((temporal_promotion or {}).get("promotion_confidence") or (temporal_promotion or {}).get("confidence") or ""),
            str((remembered_fact or {}).get("signal_confidence") or (remembered_fact or {}).get("confidence") or ""),
            str((executive_contradiction or {}).get("control_confidence") or (executive_contradiction or {}).get("confidence") or ""),
        )
        source_anchor = _merge_fragments(
            str(chronicle_signal.get("source_anchor") or ""),
            _anchor(temporal_promotion),
            _anchor(remembered_fact),
            _anchor(executive_contradiction),
        )
        status = str(chronicle_signal.get("status") or "active")

        candidates.append(
            {
                "brief_type": brief_type,
                "canonical_key": f"chronicle-consolidation-brief:{brief_type}:{domain_key}",
                "domain_key": domain_key,
                "status": status,
                "title": f"Chronicle brief: {brief_focus}",
                "summary": f"Bounded chronicle brief is holding {brief_focus.lower()} as a small longer-horizon continuity candidate.",
                "rationale": (
                    "A bounded chronicle brief may return only when an existing chronicle/consolidation signal already marks a thread as worth carrying, without becoming a diary engine, file writeback path, or hidden authority."
                ),
                "source_kind": "runtime-derived-support",
                "confidence": brief_confidence,
                "evidence_summary": _merge_fragments(
                    str(chronicle_signal.get("evidence_summary") or ""),
                    str((temporal_promotion or {}).get("evidence_summary") or ""),
                    str((remembered_fact or {}).get("evidence_summary") or ""),
                    str((executive_contradiction or {}).get("evidence_summary") or ""),
                ),
                "support_summary": _merge_fragments(
                    "Derived primarily from an existing bounded chronicle/consolidation signal, with only optional promotion/fact/contradiction sharpening.",
                    source_anchor,
                ),
                "support_count": 1,
                "session_count": 1,
                "status_reason": (
                    "Bounded chronicle brief remains non-authoritative runtime support and is not yet writing to chronicle or memory files."
                ),
                "brief_focus": brief_focus,
                "brief_weight": brief_weight,
                "brief_summary": str(chronicle_signal.get("summary") or ""),
                "brief_reason": brief_reason,
                "brief_confidence": brief_confidence,
                "source_anchor": source_anchor,
                "grounding_mode": _grounding_mode(
                    has_temporal_promotion=temporal_promotion is not None,
                    has_remembered_fact=remembered_fact is not None,
                    has_executive_contradiction=executive_contradiction is not None,
                ),
                "writeback_state": "not-writing-to-canonical-files",
                "chronicle_signal_id": str(chronicle_signal.get("signal_id") or ""),
            }
        )

    return candidates[:4]


def _persist_chronicle_consolidation_briefs(
    *,
    briefs: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for brief in briefs:
        persisted_item = upsert_runtime_chronicle_consolidation_brief(
            brief_id=f"chronicle-consolidation-brief-{uuid4().hex}",
            brief_type=str(brief.get("brief_type") or "chronicle-brief"),
            canonical_key=str(brief.get("canonical_key") or ""),
            status=str(brief.get("status") or "active"),
            title=str(brief.get("title") or ""),
            summary=str(brief.get("summary") or ""),
            rationale=str(brief.get("rationale") or ""),
            source_kind=str(brief.get("source_kind") or "runtime-derived-support"),
            confidence=str(brief.get("confidence") or "low"),
            evidence_summary=str(brief.get("evidence_summary") or ""),
            support_summary=str(brief.get("support_summary") or ""),
            status_reason=str(brief.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
            support_count=int(brief.get("support_count") or 1),
            session_count=int(brief.get("session_count") or 1),
            created_at=now,
            updated_at=now,
        )
        superseded_count = supersede_runtime_chronicle_consolidation_briefs_for_domain(
            domain_key=str(brief.get("domain_key") or ""),
            exclude_brief_id=str(persisted_item.get("brief_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded chronicle/consolidation brief for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "chronicle_consolidation_brief.superseded",
                {
                    "brief_id": persisted_item.get("brief_id"),
                    "brief_type": persisted_item.get("brief_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "chronicle_consolidation_brief.created",
                {
                    "brief_id": persisted_item.get("brief_id"),
                    "brief_type": persisted_item.get("brief_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "chronicle_consolidation_brief.updated",
                {
                    "brief_id": persisted_item.get("brief_id"),
                    "brief_type": persisted_item.get("brief_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, brief))
    return persisted


def _with_runtime_view(item: dict[str, object], brief: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["brief_focus"] = str(brief.get("brief_focus") or "")
    enriched["brief_weight"] = str(brief.get("brief_weight") or "low")
    enriched["brief_summary"] = str(brief.get("brief_summary") or item.get("summary") or "")
    enriched["brief_reason"] = str(brief.get("brief_reason") or "")
    enriched["brief_confidence"] = str(brief.get("brief_confidence") or item.get("confidence") or "low")
    enriched["source_anchor"] = str(brief.get("source_anchor") or "")
    enriched["grounding_mode"] = str(brief.get("grounding_mode") or "chronicle-consolidation-signal")
    enriched["writeback_state"] = str(brief.get("writeback_state") or "not-writing-to-canonical-files")
    enriched["chronicle_signal_id"] = str(brief.get("chronicle_signal_id") or "")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    brief_type = str(item.get("brief_type") or _canonical_segment(str(item.get("canonical_key") or ""), index=1) or "chronicle-brief")
    enriched["brief_focus"] = _value(
        item.get("brief_focus"),
        _focus_title(_domain_key(str(item.get("canonical_key") or ""))),
        default="visible continuity",
    )
    enriched["brief_type"] = brief_type
    enriched["brief_weight"] = _value(
        item.get("brief_weight"),
        _weight_from_brief_type(brief_type),
        default="low",
    )
    enriched["brief_summary"] = str(item.get("brief_summary") or item.get("summary") or "")
    enriched["brief_reason"] = str(item.get("brief_reason") or item.get("summary") or "")
    enriched["brief_confidence"] = str(item.get("brief_confidence") or item.get("confidence") or "low")
    enriched["source_anchor"] = _value(
        item.get("source_anchor"),
        item.get("support_summary"),
        item.get("title"),
        default="",
    )
    enriched["grounding_mode"] = str(item.get("grounding_mode") or "chronicle-consolidation-signal")
    enriched["writeback_state"] = str(item.get("writeback_state") or "not-writing-to-canonical-files")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _brief_type(*, chronicle_type: str, has_remembered_fact: bool, has_temporal_promotion: bool) -> str:
    if has_remembered_fact:
        return "anchored-brief"
    if has_temporal_promotion or chronicle_type == "consolidation-worthy":
        return "consolidation-brief"
    if chronicle_type == "carry-forward-thread":
        return "carry-forward-brief"
    return "chronicle-brief"


def _brief_weight(*, chronicle_weight: str, contradiction_pressure: str, has_temporal_promotion: bool) -> str:
    if contradiction_pressure == "high":
        return "high"
    if chronicle_weight == "high" or has_temporal_promotion:
        return "high"
    if chronicle_weight == "medium":
        return "medium"
    return "low"


def _grounding_mode(
    *,
    has_temporal_promotion: bool,
    has_remembered_fact: bool,
    has_executive_contradiction: bool,
) -> str:
    parts = ["chronicle-consolidation-signal"]
    if has_temporal_promotion:
        parts.append("temporal-promotion")
    if has_remembered_fact:
        parts.append("remembered-fact")
    if has_executive_contradiction:
        parts.append("executive-contradiction")
    return "+".join(parts)


def _domain_key(canonical_key: str) -> str:
    parts = [segment.strip() for segment in str(canonical_key or "").split(":") if segment.strip()]
    if len(parts) >= 3:
        return parts[-1]
    return ""


def _focus_title(domain_key: str) -> str:
    return str(domain_key or "visible continuity").replace("-", " ").strip()


def _canonical_segment(canonical_key: str, *, index: int) -> str:
    parts = [segment.strip() for segment in str(canonical_key or "").split(":") if segment.strip()]
    if 0 <= index < len(parts):
        return parts[index]
    return ""


def _weight_from_brief_type(brief_type: str) -> str:
    normalized = str(brief_type or "").strip()
    if normalized == "consolidation-brief":
        return "high"
    if normalized in {"anchored-brief", "carry-forward-brief", "chronicle-brief"}:
        return "medium"
    return "low"


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    return _merge_fragments(
        str(item.get("title") or ""),
        str(item.get("summary") or ""),
    )[:160]


def _merge_fragments(*parts: str) -> str:
    seen: list[str] = []
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if normalized and normalized not in seen:
            seen.append(normalized)
    return " ".join(seen)


def _stronger_confidence(*values: str) -> str:
    best = "low"
    for value in values:
        candidate = str(value or "").strip().lower()
        if _CONFIDENCE_RANKS.get(candidate, -1) > _CONFIDENCE_RANKS.get(best, -1):
            best = candidate
    return best


def _value(*values: object, default: str) -> str:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return default


def _parse_dt(raw: str) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
