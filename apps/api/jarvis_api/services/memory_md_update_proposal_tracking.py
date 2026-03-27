from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from apps.api.jarvis_api.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_memory_md_update_proposals,
    supersede_runtime_memory_md_update_proposals_for_dimension,
    update_runtime_memory_md_update_proposal_status,
    upsert_runtime_memory_md_update_proposal,
)

_STALE_AFTER_DAYS = 14


def track_runtime_memory_md_update_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_memory_md_update_proposals(
        proposals=_extract_memory_md_update_proposals(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded MEMORY.md update proposals."
            if items
            else "No bounded MEMORY.md update proposal warranted tracking."
        ),
    }


def refresh_runtime_memory_md_update_proposal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_memory_md_update_proposals(limit=40):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_memory_md_update_proposal_status(
            str(item.get("proposal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded MEMORY.md proposal inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "memory_md_update_proposal.stale",
            {
                "proposal_id": refreshed_item.get("proposal_id"),
                "proposal_type": refreshed_item.get("proposal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_memory_md_update_proposal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_memory_md_update_proposal_statuses()
    items = list_runtime_memory_md_update_proposals(limit=max(limit, 1))
    enriched_items = [_with_surface_view(item) for item in items]
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
            "current_proposal": str((latest or {}).get("title") or "No active MEMORY.md update proposal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_proposal_type": str((latest or {}).get("proposal_type") or "none"),
            "current_proposal_confidence": str((latest or {}).get("proposal_confidence") or "low"),
        },
    }


def _extract_memory_md_update_proposals() -> list[dict[str, object]]:
    proposals: list[dict[str, object]] = []

    for item in build_runtime_open_loop_signal_surface(limit=12).get("items", []):
        loop_status = str(item.get("status") or "")
        if loop_status not in {"open", "softening"}:
            continue
        proposal_type = "open-followup-update" if loop_status == "open" else "carry-forward-thread-update"
        domain_key = _domain_from_canonical_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        memory_kind = "open-followup" if loop_status == "open" else "carry-forward-thread"
        proposal_confidence = _build_proposal_confidence(
            source_confidence=str(item.get("confidence") or "low"),
            proposal_type=proposal_type,
        )
        proposal_reason = _build_proposal_reason(
            proposal_type=proposal_type,
            source_summary=str(item.get("summary") or ""),
            proposal_confidence=proposal_confidence,
        )
        source_anchor = _build_source_anchor(
            source_type=str(item.get("signal_type") or ""),
            domain_key=domain_key,
            support_summary=str(item.get("support_summary") or ""),
        )
        proposals.append(
            {
                "proposal_type": proposal_type,
                "canonical_key": f"memory-md-update-proposal:{proposal_type}:{domain_key}",
                "dimension_key": f"{proposal_type}:{domain_key}",
                "status": "fresh" if loop_status == "open" else "fading",
                "title": f"MEMORY.md update proposal: {_title_suffix(domain_key)}",
                "summary": proposal_reason,
                "rationale": str(item.get("summary") or "")
                or "A bounded open-loop signal now points toward a small MEMORY.md carry-forward proposal.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(str(item.get("confidence") or "low"), proposal_confidence),
                "evidence_summary": str(item.get("evidence_summary") or ""),
                "support_summary": _merge_fragments(
                    str(item.get("support_summary") or ""),
                    source_anchor,
                    _build_proposed_update(proposal_type=proposal_type, domain_key=domain_key),
                ),
                "support_count": int(item.get("support_count") or 1),
                "session_count": int(item.get("session_count") or 1),
                "status_reason": _build_status_reason(proposal_type=proposal_type, source_status=loop_status),
                "memory_kind": memory_kind,
                "proposed_update": _build_proposed_update(proposal_type=proposal_type, domain_key=domain_key),
                "proposal_reason": proposal_reason,
                "proposal_confidence": proposal_confidence,
                "source_anchor": source_anchor,
            }
        )

    for item in build_runtime_witness_signal_surface(limit=12).get("items", []):
        witness_status = str(item.get("status") or "")
        if witness_status not in {"fresh", "carried"}:
            continue
        domain_key = _domain_from_canonical_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        proposal_type = "stable-context-update"
        proposal_confidence = _build_proposal_confidence(
            source_confidence=str(item.get("confidence") or "low"),
            proposal_type=proposal_type,
        )
        proposal_reason = _build_proposal_reason(
            proposal_type=proposal_type,
            source_summary=str(item.get("summary") or ""),
            proposal_confidence=proposal_confidence,
        )
        source_anchor = _build_source_anchor(
            source_type=str(item.get("signal_type") or ""),
            domain_key=domain_key,
            support_summary=str(item.get("support_summary") or ""),
        )
        proposals.append(
            {
                "proposal_type": proposal_type,
                "canonical_key": f"memory-md-update-proposal:{proposal_type}:{domain_key}",
                "dimension_key": f"{proposal_type}:{domain_key}",
                "status": "fresh" if witness_status == "fresh" else "active",
                "title": f"MEMORY.md update proposal: {_title_suffix(domain_key)}",
                "summary": proposal_reason,
                "rationale": str(item.get("summary") or "")
                or "A bounded witness signal now points toward a small stable-context MEMORY.md proposal.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(str(item.get("confidence") or "low"), proposal_confidence),
                "evidence_summary": str(item.get("evidence_summary") or ""),
                "support_summary": _merge_fragments(
                    str(item.get("support_summary") or ""),
                    source_anchor,
                    _build_proposed_update(proposal_type=proposal_type, domain_key=domain_key),
                ),
                "support_count": int(item.get("support_count") or 1),
                "session_count": int(item.get("session_count") or 1),
                "status_reason": _build_status_reason(proposal_type=proposal_type, source_status=witness_status),
                "memory_kind": "stable-context",
                "proposed_update": _build_proposed_update(proposal_type=proposal_type, domain_key=domain_key),
                "proposal_reason": proposal_reason,
                "proposal_confidence": proposal_confidence,
                "source_anchor": source_anchor,
            }
        )

    deduped: dict[str, dict[str, object]] = {}
    for proposal in proposals:
        canonical_key = str(proposal.get("canonical_key") or "")
        if not canonical_key:
            continue
        current = deduped.get(canonical_key)
        if current is None:
            deduped[canonical_key] = proposal
            continue
        if _rank_confidence(str(proposal.get("confidence") or "")) >= _rank_confidence(
            str(current.get("confidence") or "")
        ):
            deduped[canonical_key] = proposal
    return list(deduped.values())[:4]


def _persist_memory_md_update_proposals(
    *,
    proposals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for proposal in proposals:
        persisted_item = upsert_runtime_memory_md_update_proposal(
            proposal_id=f"memory-md-update-proposal-{uuid4().hex}",
            proposal_type=str(proposal.get("proposal_type") or "carry-forward-thread-update"),
            canonical_key=str(proposal.get("canonical_key") or ""),
            status=str(proposal.get("status") or "fresh"),
            title=str(proposal.get("title") or ""),
            summary=str(proposal.get("proposal_reason") or proposal.get("summary") or ""),
            rationale=str(proposal.get("rationale") or ""),
            source_kind=str(proposal.get("source_kind") or "runtime-derived-support"),
            confidence=str(proposal.get("confidence") or "low"),
            evidence_summary=str(proposal.get("evidence_summary") or ""),
            support_summary=str(proposal.get("support_summary") or ""),
            support_count=int(proposal.get("support_count") or 1),
            session_count=int(proposal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(proposal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        superseded_count = supersede_runtime_memory_md_update_proposals_for_dimension(
            dimension_key=str(proposal.get("dimension_key") or ""),
            exclude_proposal_id=str(persisted_item.get("proposal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded MEMORY.md update proposal for the same carried context.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "memory_md_update_proposal.superseded",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "memory_md_update_proposal.created",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "memory_md_update_proposal.updated",
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
    enriched["memory_kind"] = str(proposal.get("memory_kind") or "")
    enriched["proposed_update"] = str(proposal.get("proposed_update") or "")
    enriched["proposal_reason"] = str(proposal.get("proposal_reason") or item.get("summary") or "")
    enriched["proposal_confidence"] = str(proposal.get("proposal_confidence") or "low")
    enriched["source_anchor"] = str(proposal.get("source_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    canonical_key = str(item.get("canonical_key") or "")
    enriched["memory_kind"] = _memory_kind_from_canonical_key(canonical_key)
    enriched["proposed_update"] = str(item.get("support_summary") or "")
    enriched["proposal_reason"] = str(item.get("summary") or "")
    enriched["proposal_confidence"] = str(item.get("confidence") or "low")
    enriched["source_anchor"] = _source_anchor_from_support_summary(str(item.get("support_summary") or ""))
    return enriched


def _build_proposed_update(*, proposal_type: str, domain_key: str) -> str:
    title_suffix = _title_suffix(domain_key)
    if proposal_type == "open-followup-update":
        return f"Carry forward the still-open follow-up thread around {title_suffix.lower()}."
    if proposal_type == "carry-forward-thread-update":
        return f"Carry forward the softening thread around {title_suffix.lower()} as still relevant context."
    return f"Carry forward the stable context around {title_suffix.lower()} as remembered workspace continuity."


def _build_proposal_reason(*, proposal_type: str, source_summary: str, proposal_confidence: str) -> str:
    if proposal_type == "open-followup-update":
        return source_summary or "This bounded runtime truth now looks like a small open follow-up candidate for MEMORY.md, not a writeback."
    if proposal_type == "carry-forward-thread-update":
        return source_summary or "This bounded runtime truth now looks like a small carry-forward thread candidate for MEMORY.md while it remains tentative."
    return source_summary or f"This bounded runtime truth now looks like a small stable-context candidate for MEMORY.md while proposal confidence stays {proposal_confidence}."


def _build_proposal_confidence(*, source_confidence: str, proposal_type: str) -> str:
    if proposal_type in {"open-followup-update", "stable-context-update"} and source_confidence in {"high", "medium"}:
        return "medium" if source_confidence == "medium" else "high"
    if source_confidence in {"high", "medium"}:
        return "medium"
    return "low"


def _build_source_anchor(*, source_type: str, domain_key: str, support_summary: str) -> str:
    parts = [source_type, domain_key, _source_anchor_from_support_summary(support_summary)]
    return " · ".join([part for part in parts if part][:3])


def _build_status_reason(*, proposal_type: str, source_status: str) -> str:
    if proposal_type == "open-followup-update":
        return "A bounded open-loop signal now warrants a visible MEMORY.md follow-up proposal without any writeback."
    if proposal_type == "carry-forward-thread-update":
        return "A bounded open-loop signal is softening, but still warrants a visible MEMORY.md carry-forward proposal."
    if source_status == "fresh":
        return "A bounded witness signal now warrants a visible MEMORY.md stable-context proposal without any writeback."
    return "A bounded witness signal remains carried strongly enough to keep a visible MEMORY.md stable-context proposal active."


def _title_suffix(domain_key: str) -> str:
    return domain_key.replace("-", " ").strip().title() or "Carried Context"


def _domain_from_canonical_key(canonical_key: str) -> str:
    parts = [part for part in canonical_key.split(":") if part]
    return parts[-1] if parts else ""


def _memory_kind_from_canonical_key(canonical_key: str) -> str:
    parts = [part for part in canonical_key.split(":") if part]
    proposal_type = parts[1] if len(parts) >= 2 else ""
    mapping = {
        "open-followup-update": "open-followup",
        "carry-forward-thread-update": "carry-forward-thread",
        "stable-context-update": "stable-context",
    }
    return mapping.get(proposal_type, "")


def _source_anchor_from_support_summary(support_summary: str) -> str:
    for fragment in [part.strip() for part in support_summary.split("|")]:
        if "anchor" in fragment.lower():
            return fragment
    return ""


def _merge_fragments(*parts: str) -> str:
    ordered: list[str] = []
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized or normalized in ordered:
            continue
        ordered.append(normalized)
    return " | ".join(ordered[:4])


def _stronger_confidence(left: str, right: str) -> str:
    return left if _rank_confidence(left) >= _rank_confidence(right) else right


def _rank_confidence(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(str(value or "").lower(), 0)


def _parse_dt(value: str) -> datetime | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None
