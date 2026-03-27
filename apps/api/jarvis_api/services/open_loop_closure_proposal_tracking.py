from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from apps.api.jarvis_api.services.reflection_signal_tracking import (
    build_runtime_reflection_signal_surface,
)
from apps.api.jarvis_api.services.self_review_cadence_signal_tracking import (
    build_runtime_self_review_cadence_signal_surface,
)
from apps.api.jarvis_api.services.self_review_outcome_tracking import (
    build_runtime_self_review_outcome_surface,
)
from apps.api.jarvis_api.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_open_loop_closure_proposals,
    supersede_runtime_open_loop_closure_proposals_for_domain,
    update_runtime_open_loop_closure_proposal_status,
    upsert_runtime_open_loop_closure_proposal,
)

_STALE_AFTER_DAYS = 14


def track_runtime_open_loop_closure_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_open_loop_closure_proposals(
        proposals=_extract_open_loop_closure_proposal_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded open-loop closure proposals."
            if items
            else "No bounded open-loop closure proposal warranted tracking."
        ),
    }


def refresh_runtime_open_loop_closure_proposal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_open_loop_closure_proposals(limit=40):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_open_loop_closure_proposal_status(
            str(item.get("proposal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded loop-closure proposal inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "open_loop_closure_proposal.stale",
            {
                "proposal_id": refreshed_item.get("proposal_id"),
                "proposal_type": refreshed_item.get("proposal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_open_loop_closure_proposal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_open_loop_closure_proposal_statuses()
    items = list_runtime_open_loop_closure_proposals(limit=max(limit, 1))
    snapshots = _build_proposal_snapshots()
    enriched_items = [_with_surface_view(item, snapshots=snapshots) for item in items]
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
            "current_proposal": str((latest or {}).get("title") or "No active loop-closure proposal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_proposal_type": str((latest or {}).get("proposal_type") or "none"),
            "current_closure_confidence": str((latest or {}).get("closure_confidence") or "low"),
        },
    }


def _extract_open_loop_closure_proposal_candidates() -> list[dict[str, object]]:
    snapshots = _build_proposal_snapshots()
    candidates: list[dict[str, object]] = []

    for item in build_runtime_open_loop_signal_surface(limit=12).get("items", []):
        loop_status = str(item.get("status") or "")
        if loop_status not in {"open", "softening"}:
            continue
        closure_confidence = str(item.get("closure_confidence") or "low")
        if closure_confidence not in {"medium", "high"}:
            continue
        domain_key = _open_loop_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        snapshot = snapshots.get(domain_key) or {}
        proposal_type = _build_proposal_type(item=item, snapshot=snapshot)
        if not proposal_type:
            continue
        title_suffix = _domain_title(domain_key)
        proposal_reason = _build_proposal_reason(
            proposal_type=proposal_type,
            loop_status=loop_status,
            closure_confidence=closure_confidence,
        )
        review_anchor = _build_review_anchor(snapshot=snapshot)
        source_items = [
            item,
            snapshot.get("settled_reflection"),
            snapshot.get("witness"),
            snapshot.get("review_outcome"),
            snapshot.get("review_cadence"),
        ]
        candidates.append(
            {
                "proposal_type": proposal_type,
                "canonical_key": f"open-loop-closure-proposal:{proposal_type}:{domain_key}",
                "domain_key": domain_key,
                "status": _proposal_status(proposal_type=proposal_type, loop_status=loop_status),
                "title": f"Loop closure proposal: {title_suffix}",
                "summary": proposal_reason,
                "rationale": str(item.get("closure_reason") or item.get("summary") or "")
                or "An open loop now carries bounded closure evidence worth surfacing as a small proposal.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(
                    str(item.get("confidence") or "low"),
                    closure_confidence,
                ),
                "evidence_summary": _merge_fragments(
                    *[str(source.get("evidence_summary") or "") for source in source_items if source]
                ),
                "support_summary": _merge_fragments(
                    *[str(source.get("support_summary") or "") for source in source_items if source],
                    review_anchor,
                ),
                "support_count": max([int(source.get("support_count") or 1) for source in source_items if source], default=1),
                "session_count": max([int(source.get("session_count") or 1) for source in source_items if source], default=1),
                "status_reason": str(item.get("closure_reason") or ""),
                "loop_status": loop_status,
                "closure_confidence": closure_confidence,
                "closure_readiness": str(item.get("closure_readiness") or closure_confidence),
                "proposal_reason": proposal_reason,
                "review_anchor": review_anchor,
            }
        )

    return candidates[:4]


def _persist_open_loop_closure_proposals(
    *,
    proposals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    existing_by_key = {
        str(item.get("canonical_key") or ""): item for item in list_runtime_open_loop_closure_proposals(limit=40)
    }
    persisted: list[dict[str, object]] = []
    for proposal in proposals:
        existing = existing_by_key.get(str(proposal.get("canonical_key") or ""))
        persisted_item = upsert_runtime_open_loop_closure_proposal(
            proposal_id=f"open-loop-closure-proposal-{uuid4().hex}",
            proposal_type=str(proposal.get("proposal_type") or "hold-open"),
            canonical_key=str(proposal.get("canonical_key") or ""),
            status="active" if existing and str(proposal.get("status") or "") == "fresh" else str(proposal.get("status") or "fresh"),
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
        superseded_count = supersede_runtime_open_loop_closure_proposals_for_domain(
            domain_key=str(proposal.get("domain_key") or ""),
            exclude_proposal_id=str(persisted_item.get("proposal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded loop-closure proposal for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "open_loop_closure_proposal.superseded",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "open_loop_closure_proposal.created",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "open_loop_closure_proposal.updated",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, proposal))
    return persisted


def _build_proposal_snapshots() -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for item in build_runtime_reflection_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") != "settled":
            continue
        domain_key = _reflection_domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["settled_reflection"] = item

    for item in build_runtime_witness_signal_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"fresh", "carried"}:
            continue
        domain_key = _witness_domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["witness"] = item

    for item in build_runtime_self_review_outcome_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"fresh", "active", "fading"}:
            continue
        domain_key = _review_domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["review_outcome"] = item

    for item in build_runtime_self_review_cadence_signal_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _review_cadence_domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["review_cadence"] = item

    return snapshots


def _with_runtime_view(item: dict[str, object], proposal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["domain"] = _proposal_domain_key(str(item.get("canonical_key") or ""))
    enriched["loop_status"] = str(proposal.get("loop_status") or "open")
    enriched["closure_confidence"] = str(proposal.get("closure_confidence") or "low")
    enriched["closure_readiness"] = str(proposal.get("closure_readiness") or "low")
    enriched["proposal_reason"] = str(proposal.get("proposal_reason") or item.get("summary") or "")
    enriched["review_anchor"] = str(proposal.get("review_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object], *, snapshots: dict[str, dict[str, object]]) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _proposal_domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key) or {}
    open_loop = next(
        (
            candidate
            for candidate in build_runtime_open_loop_signal_surface(limit=12).get("items", [])
            if _open_loop_domain_key(str(candidate.get("canonical_key") or "")) == domain_key
        ),
        {},
    )
    enriched["domain"] = domain_key
    enriched["loop_status"] = str(open_loop.get("status") or "open")
    enriched["closure_confidence"] = str(open_loop.get("closure_confidence") or "low")
    enriched["closure_readiness"] = str(open_loop.get("closure_readiness") or "low")
    enriched["proposal_reason"] = str(item.get("summary") or "")
    enriched["review_anchor"] = _build_review_anchor(snapshot=snapshot)
    return enriched


def _build_proposal_type(*, item: dict[str, object], snapshot: dict[str, object]) -> str:
    closure_confidence = str(item.get("closure_confidence") or "low")
    outcome_type = str((snapshot.get("review_outcome") or {}).get("outcome_type") or "")
    cadence_state = str((snapshot.get("review_cadence") or {}).get("cadence_state") or "")

    if closure_confidence == "high" and outcome_type != "challenge-further" and cadence_state not in {"due", "lingering"}:
        return "close-candidate"
    if outcome_type == "challenge-further" or cadence_state in {"due", "lingering"}:
        return "revisit-before-close"
    if closure_confidence == "medium":
        return "hold-open"
    return ""


def _proposal_status(*, proposal_type: str, loop_status: str) -> str:
    if proposal_type == "close-candidate":
        return "fresh"
    if proposal_type == "hold-open" and loop_status == "softening":
        return "fading"
    return "active"


def _build_proposal_reason(*, proposal_type: str, loop_status: str, closure_confidence: str) -> str:
    if proposal_type == "close-candidate":
        return "This loop now looks like a bounded closure candidate under current runtime truth."
    if proposal_type == "revisit-before-close":
        return "This loop shows closure evidence, but it should be revisited once more before any closure move."
    if loop_status == "softening":
        return f"This loop is softening, but current closure confidence is still only {closure_confidence}, so it should stay open."
    return f"This loop still reads as better held open while closure confidence remains {closure_confidence}."


def _build_review_anchor(*, snapshot: dict[str, object]) -> str:
    parts: list[str] = []
    outcome_type = str((snapshot.get("review_outcome") or {}).get("outcome_type") or "")
    cadence_state = str((snapshot.get("review_cadence") or {}).get("cadence_state") or "")
    if outcome_type:
        parts.append(outcome_type)
    if cadence_state:
        parts.append(cadence_state)
    if snapshot.get("witness"):
        parts.append("witnessed shift")
    if snapshot.get("settled_reflection"):
        parts.append("settled reflection")
    return " · ".join(parts[:3])


def _stronger_confidence(*values: str) -> str:
    ordered = [str(value or "").strip() for value in values if str(value or "").strip()]
    if "high" in ordered:
        return "high"
    if "medium" in ordered:
        return "medium"
    return ordered[0] if ordered else "low"


def _open_loop_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _reflection_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _witness_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _review_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _review_cadence_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _proposal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Loop"


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
