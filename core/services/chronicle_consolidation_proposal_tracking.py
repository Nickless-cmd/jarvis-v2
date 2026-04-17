from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.chronicle_consolidation_brief_tracking import (
    build_runtime_chronicle_consolidation_brief_surface,
)
from core.services.executive_contradiction_signal_tracking import (
    build_runtime_executive_contradiction_signal_surface,
)
from core.services.private_temporal_promotion_signal_tracking import (
    build_runtime_private_temporal_promotion_signal_surface,
)
from core.services.remembered_fact_signal_tracking import (
    build_runtime_remembered_fact_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_chronicle_consolidation_proposals,
    supersede_runtime_chronicle_consolidation_proposals_for_domain,
    update_runtime_chronicle_consolidation_proposal_status,
    upsert_runtime_chronicle_consolidation_proposal,
)

_STALE_AFTER_DAYS = 14
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_chronicle_consolidation_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_chronicle_consolidation_proposals(
        proposals=_extract_chronicle_consolidation_proposal_candidates(run_id=run_id),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded chronicle/consolidation proposals."
            if items
            else "No bounded chronicle/consolidation proposal warranted tracking."
        ),
    }


def refresh_runtime_chronicle_consolidation_proposal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_chronicle_consolidation_proposals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_chronicle_consolidation_proposal_status(
            str(item.get("proposal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded chronicle/consolidation proposal inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "chronicle_consolidation_proposal.stale",
            {
                "proposal_id": refreshed_item.get("proposal_id"),
                "proposal_type": refreshed_item.get("proposal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_chronicle_consolidation_proposal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_chronicle_consolidation_proposal_statuses()
    items = list_runtime_chronicle_consolidation_proposals(limit=max(limit, 1))
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
            "current_proposal": str((latest or {}).get("title") or "No active chronicle/consolidation proposal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_proposal_type": str((latest or {}).get("proposal_type") or "none"),
            "current_weight": str((latest or {}).get("proposal_weight") or "low"),
            "current_confidence": str((latest or {}).get("proposal_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "writeback_state": "not-writing-to-canonical-files",
        },
    }


def _extract_chronicle_consolidation_proposal_candidates(*, run_id: str) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for item in build_runtime_chronicle_consolidation_brief_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("brief_confidence") or item.get("confidence") or "low") not in {"medium", "high"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["chronicle_brief"] = item

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
        chronicle_brief = snapshot.get("chronicle_brief")
        if chronicle_brief is None:
            continue
        temporal_promotion = snapshot.get("temporal_promotion")
        remembered_fact = snapshot.get("remembered_fact")
        executive_contradiction = snapshot.get("executive_contradiction")

        proposal_type = _proposal_type(
            brief_type=str(chronicle_brief.get("brief_type") or ""),
            has_remembered_fact=remembered_fact is not None,
            has_temporal_promotion=temporal_promotion is not None,
        )
        proposal_focus = str(chronicle_brief.get("brief_focus") or _focus_title(domain_key)).strip()[:96]
        proposal_weight = _proposal_weight(
            brief_weight=str(chronicle_brief.get("brief_weight") or "low"),
            contradiction_pressure=str((executive_contradiction or {}).get("control_pressure") or ""),
            has_temporal_promotion=temporal_promotion is not None,
        )
        proposal_reason = _merge_fragments(
            str(chronicle_brief.get("brief_reason") or chronicle_brief.get("summary") or ""),
            str((temporal_promotion or {}).get("promotion_summary") or ""),
            str((remembered_fact or {}).get("signal_summary") or (remembered_fact or {}).get("summary") or ""),
            str((executive_contradiction or {}).get("control_summary") or (executive_contradiction or {}).get("summary") or ""),
        )[:220]
        proposal_confidence = _stronger_confidence(
            str(chronicle_brief.get("brief_confidence") or chronicle_brief.get("confidence") or "low"),
            str((temporal_promotion or {}).get("promotion_confidence") or (temporal_promotion or {}).get("confidence") or ""),
            str((remembered_fact or {}).get("signal_confidence") or (remembered_fact or {}).get("confidence") or ""),
            str((executive_contradiction or {}).get("control_confidence") or (executive_contradiction or {}).get("confidence") or ""),
        )
        source_anchor = _merge_fragments(
            str(chronicle_brief.get("source_anchor") or ""),
            _anchor(temporal_promotion),
            _anchor(remembered_fact),
            _anchor(executive_contradiction),
        )
        status = str(chronicle_brief.get("status") or "active")

        candidates.append(
            {
                "proposal_type": proposal_type,
                "canonical_key": f"chronicle-consolidation-proposal:{proposal_type}:{domain_key}",
                "domain_key": domain_key,
                "status": status,
                "title": f"Chronicle proposal: {proposal_focus}",
                "summary": f"Bounded chronicle proposal is preparing {proposal_focus.lower()} as a small future carry-forward candidate.",
                "rationale": (
                    "A bounded chronicle proposal may return only when an existing chronicle/consolidation brief already marks a thread as worth carrying, without becoming a diary engine, writeback path, or hidden authority."
                ),
                "source_kind": "runtime-derived-support",
                "confidence": proposal_confidence,
                "evidence_summary": _merge_fragments(
                    str(chronicle_brief.get("evidence_summary") or ""),
                    str((temporal_promotion or {}).get("evidence_summary") or ""),
                    str((remembered_fact or {}).get("evidence_summary") or ""),
                    str((executive_contradiction or {}).get("evidence_summary") or ""),
                ),
                "support_summary": _merge_fragments(
                    "Derived primarily from an existing bounded chronicle/consolidation brief, with only optional promotion/fact/contradiction sharpening.",
                    source_anchor,
                ),
                "support_count": 1,
                "session_count": 1,
                "status_reason": (
                    "Bounded chronicle proposal remains non-authoritative runtime support and is not yet writing to chronicle or memory files."
                ),
                "proposal_focus": proposal_focus,
                "proposal_weight": proposal_weight,
                "proposal_summary": str(chronicle_brief.get("summary") or ""),
                "proposal_reason": proposal_reason,
                "proposal_confidence": proposal_confidence,
                "source_anchor": source_anchor,
                "grounding_mode": _grounding_mode(
                    has_temporal_promotion=temporal_promotion is not None,
                    has_remembered_fact=remembered_fact is not None,
                    has_executive_contradiction=executive_contradiction is not None,
                ),
                "writeback_state": "not-writing-to-canonical-files",
                "chronicle_brief_id": str(chronicle_brief.get("brief_id") or ""),
            }
        )

    return candidates[:4]


def _persist_chronicle_consolidation_proposals(
    *,
    proposals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for proposal in proposals:
        persisted_item = upsert_runtime_chronicle_consolidation_proposal(
            proposal_id=f"chronicle-consolidation-proposal-{uuid4().hex}",
            proposal_type=str(proposal.get("proposal_type") or "chronicle-proposal"),
            canonical_key=str(proposal.get("canonical_key") or ""),
            status=str(proposal.get("status") or "active"),
            title=str(proposal.get("title") or ""),
            summary=str(proposal.get("summary") or ""),
            rationale=str(proposal.get("rationale") or ""),
            source_kind=str(proposal.get("source_kind") or "runtime-derived-support"),
            confidence=str(proposal.get("confidence") or "low"),
            evidence_summary=str(proposal.get("evidence_summary") or ""),
            support_summary=str(proposal.get("support_summary") or ""),
            status_reason=str(proposal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
            support_count=int(proposal.get("support_count") or 1),
            session_count=int(proposal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
        )
        superseded_count = supersede_runtime_chronicle_consolidation_proposals_for_domain(
            domain_key=str(proposal.get("domain_key") or ""),
            exclude_proposal_id=str(persisted_item.get("proposal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded chronicle/consolidation proposal for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "chronicle_consolidation_proposal.superseded",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "chronicle_consolidation_proposal.created",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "chronicle_consolidation_proposal.updated",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, proposal))
    return persisted


def _with_runtime_view(item: dict[str, object], proposal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["proposal_focus"] = str(proposal.get("proposal_focus") or "")
    enriched["proposal_weight"] = str(proposal.get("proposal_weight") or "low")
    enriched["proposal_summary"] = str(proposal.get("proposal_summary") or item.get("summary") or "")
    enriched["proposal_reason"] = str(proposal.get("proposal_reason") or "")
    enriched["proposal_confidence"] = str(proposal.get("proposal_confidence") or item.get("confidence") or "low")
    enriched["source_anchor"] = str(proposal.get("source_anchor") or "")
    enriched["grounding_mode"] = str(proposal.get("grounding_mode") or "chronicle-consolidation-brief")
    enriched["writeback_state"] = str(proposal.get("writeback_state") or "not-writing-to-canonical-files")
    enriched["chronicle_brief_id"] = str(proposal.get("chronicle_brief_id") or "")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    proposal_type = str(item.get("proposal_type") or _canonical_segment(str(item.get("canonical_key") or ""), index=1) or "chronicle-proposal")
    enriched["proposal_type"] = proposal_type
    enriched["proposal_focus"] = _value(
        item.get("proposal_focus"),
        _focus_title(_domain_key(str(item.get("canonical_key") or ""))),
        default="visible continuity",
    )
    enriched["proposal_weight"] = _value(
        item.get("proposal_weight"),
        _weight_from_proposal_type(proposal_type),
        default="low",
    )
    enriched["proposal_summary"] = str(item.get("proposal_summary") or item.get("summary") or "")
    enriched["proposal_reason"] = str(item.get("proposal_reason") or item.get("summary") or "")
    enriched["proposal_confidence"] = str(item.get("proposal_confidence") or item.get("confidence") or "low")
    enriched["source_anchor"] = _value(
        item.get("source_anchor"),
        item.get("support_summary"),
        item.get("title"),
        default="",
    )
    enriched["grounding_mode"] = str(item.get("grounding_mode") or "chronicle-consolidation-brief")
    enriched["writeback_state"] = str(item.get("writeback_state") or "not-writing-to-canonical-files")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _proposal_type(*, brief_type: str, has_remembered_fact: bool, has_temporal_promotion: bool) -> str:
    if has_remembered_fact:
        return "anchored-proposal"
    if has_temporal_promotion or brief_type == "consolidation-brief":
        return "consolidation-proposal"
    if brief_type == "carry-forward-brief":
        return "carry-forward-proposal"
    return "chronicle-proposal"


def _proposal_weight(*, brief_weight: str, contradiction_pressure: str, has_temporal_promotion: bool) -> str:
    if contradiction_pressure == "high":
        return "high"
    if brief_weight == "high" or has_temporal_promotion:
        return "high"
    if brief_weight == "medium":
        return "medium"
    return "low"


def _grounding_mode(
    *,
    has_temporal_promotion: bool,
    has_remembered_fact: bool,
    has_executive_contradiction: bool,
) -> str:
    parts = ["chronicle-consolidation-brief"]
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


def _weight_from_proposal_type(proposal_type: str) -> str:
    normalized = str(proposal_type or "").strip()
    if normalized == "consolidation-proposal":
        return "high"
    if normalized in {"anchored-proposal", "carry-forward-proposal", "chronicle-proposal"}:
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
