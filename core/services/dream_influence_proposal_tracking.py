from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.dream_adoption_candidate_tracking import (
    build_runtime_dream_adoption_candidate_surface,
)
from core.services.dream_hypothesis_signal_tracking import (
    build_runtime_dream_hypothesis_signal_surface,
)
from core.services.self_review_outcome_tracking import (
    build_runtime_self_review_outcome_surface,
)
from core.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from core.services.world_model_signal_tracking import (
    build_runtime_world_model_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_dream_influence_proposals,
    list_runtime_goal_signals,
    list_runtime_self_model_signals,
    supersede_runtime_dream_influence_proposals_for_domain,
    update_runtime_dream_influence_proposal_status,
    upsert_runtime_dream_influence_proposal,
)

_STALE_AFTER_DAYS = 14


def track_runtime_dream_influence_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_dream_influence_proposals(
        proposals=_extract_dream_influence_proposals(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded dream influence proposals."
            if items
            else "No bounded dream influence proposal warranted tracking."
        ),
    }


def refresh_runtime_dream_influence_proposal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_dream_influence_proposals(limit=40):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_dream_influence_proposal_status(
            str(item.get("proposal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded dream-influence inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "dream_influence_proposal.stale",
            {
                "proposal_id": refreshed_item.get("proposal_id"),
                "proposal_type": refreshed_item.get("proposal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_dream_influence_proposal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_dream_influence_proposal_statuses()
    items = list_runtime_dream_influence_proposals(limit=max(limit, 1))
    snapshots = _build_influence_snapshots()
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
            "current_proposal": str((latest or {}).get("title") or "No active dream influence proposal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_proposal_type": str((latest or {}).get("proposal_type") or "none"),
            "current_influence_confidence": str((latest or {}).get("influence_confidence") or "low"),
        },
    }


def _extract_dream_influence_proposals() -> list[dict[str, object]]:
    snapshots = _build_influence_snapshots()
    proposals: list[dict[str, object]] = []

    for item in build_runtime_dream_adoption_candidate_surface(limit=12).get("items", []):
        candidate_status = str(item.get("status") or "")
        if candidate_status not in {"fresh", "active", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        snapshot = snapshots.get(domain_key) or {}
        proposal_type = _build_proposal_type(item=item, snapshot=snapshot)
        if not proposal_type:
            continue
        influence_target = _influence_target_from_proposal_type(proposal_type)
        influence_confidence = _build_influence_confidence(
            proposal_type=proposal_type,
            candidate_type=str(item.get("candidate_type") or ""),
        )
        proposal_reason = _build_proposal_reason(
            proposal_type=proposal_type,
            candidate_type=str(item.get("candidate_type") or ""),
            influence_confidence=influence_confidence,
        )
        influence_anchor = _build_influence_anchor(snapshot=snapshot)
        source_items = [
            item,
            snapshot.get("hypothesis"),
            snapshot.get("focus"),
            snapshot.get("goal"),
            snapshot.get("self_model"),
            snapshot.get("world_model"),
            snapshot.get("witness"),
            snapshot.get("review_outcome"),
        ]
        proposals.append(
            {
                "proposal_type": proposal_type,
                "canonical_key": f"dream-influence-proposal:{proposal_type}:{domain_key}",
                "domain_key": domain_key,
                "status": _build_proposal_status(
                    candidate_status=candidate_status,
                    proposal_type=proposal_type,
                ),
                "title": f"Dream influence proposal: {_domain_title(domain_key)}",
                "summary": proposal_reason,
                "rationale": str(item.get("adoption_reason") or item.get("summary") or "")
                or "A bounded dream-adoption candidate now points toward a small possible future influence lane.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(
                    str(item.get("confidence") or "low"),
                    influence_confidence,
                    str((snapshot.get("world_model") or {}).get("confidence") or ""),
                ),
                "evidence_summary": _merge_fragments(
                    *[str(source.get("evidence_summary") or "") for source in source_items if source]
                ),
                "support_summary": _merge_fragments(
                    *[str(source.get("support_summary") or "") for source in source_items if source],
                    influence_anchor,
                ),
                "support_count": max([int(source.get("support_count") or 1) for source in source_items if source], default=1),
                "session_count": max([int(source.get("session_count") or 1) for source in source_items if source], default=1),
                "status_reason": _build_status_reason(proposal_type=proposal_type),
                "hypothesis_type": str(item.get("hypothesis_type") or ""),
                "candidate_state": str(item.get("candidate_type") or ""),
                "influence_target": influence_target,
                "influence_confidence": influence_confidence,
                "proposal_reason": proposal_reason,
                "influence_anchor": influence_anchor,
            }
        )

    return proposals[:4]


def _persist_dream_influence_proposals(
    *,
    proposals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    existing_by_key = {
        str(item.get("canonical_key") or ""): item for item in list_runtime_dream_influence_proposals(limit=40)
    }
    persisted: list[dict[str, object]] = []
    for proposal in proposals:
        existing = existing_by_key.get(str(proposal.get("canonical_key") or ""))
        persisted_item = upsert_runtime_dream_influence_proposal(
            proposal_id=f"dream-influence-proposal-{uuid4().hex}",
            proposal_type=str(proposal.get("proposal_type") or "nudge-direction"),
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
        superseded_count = supersede_runtime_dream_influence_proposals_for_domain(
            domain_key=str(proposal.get("domain_key") or ""),
            exclude_proposal_id=str(persisted_item.get("proposal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded dream-influence proposal for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "dream_influence_proposal.superseded",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "dream_influence_proposal.created",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "dream_influence_proposal.updated",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, proposal))
    return persisted


def _build_influence_snapshots() -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=18):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["focus"] = focus

    for goal in list_runtime_goal_signals(limit=18):
        if str(goal.get("status") or "") not in {"active", "completed"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["goal"] = goal

    for signal in list_runtime_self_model_signals(limit=18):
        if str(signal.get("status") or "") not in {"active", "uncertain", "corrected"}:
            continue
        domain_key = _self_model_domain_key(str(signal.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["self_model"] = signal

    for signal in build_runtime_world_model_signal_surface(limit=12).get("items", []):
        if str(signal.get("status") or "") not in {"active", "uncertain"}:
            continue
        domain_key = _world_model_domain_key(str(signal.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["world_model"] = signal

    for item in build_runtime_dream_hypothesis_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "integrating", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["hypothesis"] = item

    for item in build_runtime_witness_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"fresh", "carried"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["witness"] = item

    for item in build_runtime_self_review_outcome_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["review_outcome"] = item

    return snapshots


def _with_runtime_view(item: dict[str, object], proposal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["domain"] = _domain_key(str(item.get("canonical_key") or ""))
    enriched["hypothesis_type"] = str(proposal.get("hypothesis_type") or "")
    enriched["candidate_state"] = str(proposal.get("candidate_state") or "")
    enriched["influence_target"] = str(proposal.get("influence_target") or "")
    enriched["influence_confidence"] = str(proposal.get("influence_confidence") or "low")
    enriched["proposal_reason"] = str(proposal.get("proposal_reason") or item.get("summary") or "")
    enriched["influence_anchor"] = str(proposal.get("influence_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object], *, snapshots: dict[str, dict[str, object]]) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key) or {}
    enriched["domain"] = domain_key
    enriched["hypothesis_type"] = _hypothesis_type_from_snapshot(snapshot=snapshot)
    enriched["candidate_state"] = _candidate_state_from_summary(str(item.get("summary") or ""))
    enriched["influence_target"] = _influence_target_from_proposal_type(str(item.get("proposal_type") or ""))
    enriched["influence_confidence"] = _influence_confidence_from_summary(str(item.get("summary") or ""))
    enriched["proposal_reason"] = str(item.get("summary") or "")
    enriched["influence_anchor"] = _build_influence_anchor(snapshot=snapshot)
    return enriched


def _build_proposal_type(*, item: dict[str, object], snapshot: dict[str, object]) -> str:
    candidate_type = str(item.get("candidate_type") or "")
    hypothesis_type = str(
        (snapshot.get("hypothesis") or {}).get("hypothesis_type")
        or (snapshot.get("hypothesis") or {}).get("signal_type")
        or item.get("hypothesis_type")
        or ""
    )
    if candidate_type == "strong-candidate" and snapshot.get("self_model"):
        return "nudge-self-model"
    if candidate_type in {"strong-candidate", "carried-candidate"} and snapshot.get("goal"):
        return "nudge-direction"
    if candidate_type in {"carried-candidate", "tentative-candidate"} and snapshot.get("focus"):
        return "nudge-focus"
    if hypothesis_type == "tension-hypothesis" and snapshot.get("world_model"):
        return "nudge-world-view"
    return ""


def _influence_target_from_proposal_type(proposal_type: str) -> str:
    mapping = {
        "nudge-self-model": "self-model",
        "nudge-direction": "goals",
        "nudge-focus": "development-focus",
        "nudge-world-view": "world-model",
    }
    return mapping.get(proposal_type, "none")


def _build_proposal_status(*, candidate_status: str, proposal_type: str) -> str:
    if candidate_status == "fresh":
        return "fresh"
    if candidate_status == "fading" or proposal_type == "nudge-focus":
        return "fading"
    return "active"


def _build_influence_confidence(*, proposal_type: str, candidate_type: str) -> str:
    if proposal_type in {"nudge-self-model", "nudge-direction"} and candidate_type == "strong-candidate":
        return "high"
    if proposal_type in {"nudge-direction", "nudge-focus", "nudge-world-view"}:
        return "medium"
    return "low"


def _build_proposal_reason(*, proposal_type: str, candidate_type: str, influence_confidence: str) -> str:
    if proposal_type == "nudge-self-model":
        return "This dream line now looks like a bounded future nudge toward self-model interpretation, not a writeback."
    if proposal_type == "nudge-direction":
        return "This dream line now looks like a bounded future nudge toward development direction, not a goal update."
    if proposal_type == "nudge-focus":
        return "This dream line now looks like a bounded future nudge toward focus, but it still reads as tentative."
    return f"This dream line now looks like a bounded future nudge toward world-model interpretation while influence confidence stays {influence_confidence}."


def _build_influence_anchor(*, snapshot: dict[str, object]) -> str:
    parts: list[str] = []
    candidate_type = str((snapshot.get("candidate") or {}).get("candidate_type") or "")
    hypothesis_type = str((snapshot.get("hypothesis") or {}).get("hypothesis_type") or "")
    outcome_type = str((snapshot.get("review_outcome") or {}).get("outcome_type") or "")
    witness_type = str((snapshot.get("witness") or {}).get("signal_type") or "")
    if candidate_type:
        parts.append(candidate_type)
    if hypothesis_type:
        parts.append(hypothesis_type)
    if outcome_type:
        parts.append(outcome_type)
    if witness_type:
        parts.append(witness_type)
    return " · ".join(parts[:3])


def _build_status_reason(*, proposal_type: str) -> str:
    if proposal_type == "nudge-self-model":
        return "The bounded dream line now most plausibly points toward self-model influence later."
    if proposal_type == "nudge-direction":
        return "The bounded dream line now most plausibly points toward direction influence later."
    if proposal_type == "nudge-focus":
        return "The bounded dream line now most plausibly points toward focus influence later."
    return "The bounded dream line now most plausibly points toward world-model influence later."


def _hypothesis_type_from_snapshot(*, snapshot: dict[str, object]) -> str:
    return str((snapshot.get("hypothesis") or {}).get("hypothesis_type") or (snapshot.get("hypothesis") or {}).get("signal_type") or "")


def _candidate_state_from_summary(summary: str) -> str:
    text = str(summary or "").lower()
    if "self-model" in text or "direction" in text:
        return "strong-candidate"
    if "focus" in text:
        return "carried-candidate"
    return "tentative-candidate"


def _influence_confidence_from_summary(summary: str) -> str:
    text = str(summary or "").lower()
    if "not a writeback" in text and "self-model" in text:
        return "high"
    if "future nudge" in text:
        return "medium"
    return "low"


def _focus_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _goal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 2 else ""


def _self_model_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _world_model_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Thread"


def _stronger_confidence(*values: str) -> str:
    ordered = [str(value or "").strip() for value in values if str(value or "").strip()]
    if "high" in ordered:
        return "high"
    if "medium" in ordered:
        return "medium"
    return ordered[0] if ordered else "low"


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
