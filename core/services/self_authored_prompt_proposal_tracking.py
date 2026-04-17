from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.dream_hypothesis_signal_tracking import (
    build_runtime_dream_hypothesis_signal_surface,
)
from core.services.dream_influence_proposal_tracking import (
    build_runtime_dream_influence_proposal_surface,
)
from core.services.self_review_outcome_tracking import (
    build_runtime_self_review_outcome_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_self_authored_prompt_proposals,
    list_runtime_self_model_signals,
    supersede_runtime_self_authored_prompt_proposals_for_domain,
    update_runtime_self_authored_prompt_proposal_status,
    upsert_runtime_self_authored_prompt_proposal,
)

_STALE_AFTER_DAYS = 14


def track_runtime_self_authored_prompt_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_self_authored_prompt_proposals(
        proposals=_extract_self_authored_prompt_proposals(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded self-authored prompt proposals."
            if items
            else "No bounded self-authored prompt proposal warranted tracking."
        ),
    }


def refresh_runtime_self_authored_prompt_proposal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_self_authored_prompt_proposals(limit=40):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_self_authored_prompt_proposal_status(
            str(item.get("proposal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded self-authored prompt inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "self_authored_prompt_proposal.stale",
            {
                "proposal_id": refreshed_item.get("proposal_id"),
                "proposal_type": refreshed_item.get("proposal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_self_authored_prompt_proposal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_self_authored_prompt_proposal_statuses()
    items = list_runtime_self_authored_prompt_proposals(limit=max(limit, 1))
    snapshots = _build_prompt_snapshots()
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
            "current_proposal": str((latest or {}).get("title") or "No active self-authored prompt proposal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_proposal_type": str((latest or {}).get("proposal_type") or "none"),
            "current_proposal_confidence": str((latest or {}).get("proposal_confidence") or "low"),
        },
    }


def _extract_self_authored_prompt_proposals() -> list[dict[str, object]]:
    snapshots = _build_prompt_snapshots()
    proposals: list[dict[str, object]] = []

    for item in build_runtime_dream_influence_proposal_surface(limit=12).get("items", []):
        influence_status = str(item.get("status") or "")
        if influence_status not in {"fresh", "active", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        snapshot = snapshots.get(domain_key) or {}
        proposal_type = _build_proposal_type(item=item, snapshot=snapshot)
        if not proposal_type:
            continue
        prompt_target = _prompt_target_from_proposal_type(proposal_type)
        proposed_nudge = _build_proposed_nudge(proposal_type=proposal_type)
        proposal_confidence = _build_proposal_confidence(
            proposal_type=proposal_type,
            influence_confidence=str(item.get("influence_confidence") or ""),
        )
        proposal_reason = _build_proposal_reason(
            proposal_type=proposal_type,
            proposal_confidence=proposal_confidence,
        )
        influence_anchor = _build_influence_anchor(item=item, snapshot=snapshot)
        source_items = [
            item,
            snapshot.get("hypothesis"),
            snapshot.get("focus"),
            snapshot.get("goal"),
            snapshot.get("self_model"),
            snapshot.get("review_outcome"),
        ]
        proposals.append(
            {
                "proposal_type": proposal_type,
                "canonical_key": f"self-authored-prompt-proposal:{proposal_type}:{domain_key}",
                "domain_key": domain_key,
                "status": _build_prompt_status(
                    influence_status=influence_status,
                    proposal_type=proposal_type,
                ),
                "title": f"Self-authored prompt proposal: {_domain_title(domain_key)}",
                "summary": proposal_reason,
                "rationale": str(item.get("proposal_reason") or item.get("summary") or "")
                or "A bounded dream influence proposal now materializes as a small prompt-framing proposal.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(
                    str(item.get("confidence") or "low"),
                    proposal_confidence,
                    str((snapshot.get("goal") or {}).get("confidence") or ""),
                ),
                "evidence_summary": _merge_fragments(
                    *[str(source.get("evidence_summary") or "") for source in source_items if source]
                ),
                "support_summary": _merge_fragments(
                    *[str(source.get("support_summary") or "") for source in source_items if source],
                    influence_anchor,
                    proposed_nudge,
                ),
                "support_count": max([int(source.get("support_count") or 1) for source in source_items if source], default=1),
                "session_count": max([int(source.get("session_count") or 1) for source in source_items if source], default=1),
                "status_reason": _build_status_reason(proposal_type=proposal_type),
                "hypothesis_type": str(item.get("hypothesis_type") or ""),
                "influence_target": str(item.get("influence_target") or ""),
                "prompt_target": prompt_target,
                "proposed_nudge": proposed_nudge,
                "proposal_reason": proposal_reason,
                "proposal_confidence": proposal_confidence,
                "influence_anchor": influence_anchor,
            }
        )

    return proposals[:4]


def _persist_self_authored_prompt_proposals(
    *,
    proposals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    existing_by_key = {
        str(item.get("canonical_key") or ""): item
        for item in list_runtime_self_authored_prompt_proposals(limit=40)
    }
    persisted: list[dict[str, object]] = []
    for proposal in proposals:
        existing = existing_by_key.get(str(proposal.get("canonical_key") or ""))
        persisted_item = upsert_runtime_self_authored_prompt_proposal(
            proposal_id=f"self-authored-prompt-proposal-{uuid4().hex}",
            proposal_type=str(proposal.get("proposal_type") or "focus-nudge"),
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
        superseded_count = supersede_runtime_self_authored_prompt_proposals_for_domain(
            domain_key=str(proposal.get("domain_key") or ""),
            exclude_proposal_id=str(persisted_item.get("proposal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded self-authored prompt proposal for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "self_authored_prompt_proposal.superseded",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "self_authored_prompt_proposal.created",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "self_authored_prompt_proposal.updated",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, proposal))
    return persisted


def _build_prompt_snapshots() -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=18):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["focus"] = focus

    for goal in list_runtime_goal_signals(limit=18):
        if str(goal.get("status") or "") not in {"active", "completed", "blocked"}:
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

    for item in build_runtime_dream_hypothesis_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "integrating", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["hypothesis"] = item

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
    enriched["influence_target"] = str(proposal.get("influence_target") or "")
    enriched["prompt_target"] = str(proposal.get("prompt_target") or "")
    enriched["proposed_nudge"] = str(proposal.get("proposed_nudge") or "")
    enriched["proposal_reason"] = str(proposal.get("proposal_reason") or item.get("summary") or "")
    enriched["proposal_confidence"] = str(proposal.get("proposal_confidence") or "low")
    enriched["influence_anchor"] = str(proposal.get("influence_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object], *, snapshots: dict[str, dict[str, object]]) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key) or {}
    proposal_type = str(item.get("proposal_type") or "")
    enriched["domain"] = domain_key
    enriched["hypothesis_type"] = _hypothesis_type_from_snapshot(snapshot=snapshot)
    enriched["influence_target"] = _influence_target_from_summary(str(item.get("summary") or ""))
    enriched["prompt_target"] = _prompt_target_from_proposal_type(proposal_type)
    enriched["proposed_nudge"] = _build_proposed_nudge(proposal_type=proposal_type)
    enriched["proposal_reason"] = str(item.get("summary") or "")
    enriched["proposal_confidence"] = _proposal_confidence_from_summary(str(item.get("summary") or ""))
    enriched["influence_anchor"] = _build_influence_anchor(item=enriched, snapshot=snapshot)
    return enriched


def _build_proposal_type(*, item: dict[str, object], snapshot: dict[str, object]) -> str:
    influence_target = str(item.get("influence_target") or "")
    hypothesis_type = str(
        (snapshot.get("hypothesis") or {}).get("hypothesis_type")
        or (snapshot.get("hypothesis") or {}).get("signal_type")
        or item.get("hypothesis_type")
        or ""
    )
    if influence_target == "self-model" and snapshot.get("self_model"):
        return "communication-nudge"
    if influence_target == "goals" and snapshot.get("goal"):
        return "focus-nudge"
    if influence_target == "development-focus" and snapshot.get("focus"):
        return "challenge-nudge"
    if influence_target == "world-model" and hypothesis_type == "tension-hypothesis":
        return "world-caution-nudge"
    return ""


def _prompt_target_from_proposal_type(proposal_type: str) -> str:
    mapping = {
        "communication-nudge": "communication-style",
        "focus-nudge": "direction-framing",
        "challenge-nudge": "challenge-posture",
        "world-caution-nudge": "world-caution",
    }
    return mapping.get(proposal_type, "none")


def _build_proposed_nudge(*, proposal_type: str) -> str:
    if proposal_type == "communication-nudge":
        return "Keep replies plain, grounded, and slightly more self-calibrating."
    if proposal_type == "focus-nudge":
        return "Keep future framing pointed at the carried direction instead of reopening scope."
    if proposal_type == "challenge-nudge":
        return "Carry a small internal challenge before settling on the current thread."
    return "Add a small caution marker when world interpretation still looks unstable."


def _build_prompt_status(*, influence_status: str, proposal_type: str) -> str:
    if influence_status == "fresh":
        return "fresh"
    if influence_status == "fading":
        return "fading"
    return "active"


def _build_proposal_confidence(*, proposal_type: str, influence_confidence: str) -> str:
    if proposal_type == "communication-nudge" and influence_confidence == "high":
        return "high"
    if influence_confidence in {"high", "medium"}:
        return "medium"
    return "low"


def _build_proposal_reason(*, proposal_type: str, proposal_confidence: str) -> str:
    if proposal_type == "communication-nudge":
        return "This dream line now looks like a bounded future communication nudge, not a prompt mutation."
    if proposal_type == "focus-nudge":
        return "This dream line now looks like a bounded future direction-framing nudge, not a goal writeback."
    if proposal_type == "challenge-nudge":
        return "This dream line now looks like a bounded future challenge-posture nudge while it remains tentative."
    return f"This dream line now looks like a bounded future world-caution nudge while proposal confidence stays {proposal_confidence}."


def _build_influence_anchor(*, item: dict[str, object], snapshot: dict[str, object]) -> str:
    parts: list[str] = []
    influence_target = str(item.get("influence_target") or "")
    hypothesis_type = str((snapshot.get("hypothesis") or {}).get("hypothesis_type") or "")
    outcome_type = str((snapshot.get("review_outcome") or {}).get("outcome_type") or "")
    if influence_target:
        parts.append(influence_target)
    if hypothesis_type:
        parts.append(hypothesis_type)
    if outcome_type:
        parts.append(outcome_type)
    return " · ".join(parts[:3])


def _build_status_reason(*, proposal_type: str) -> str:
    if proposal_type == "communication-nudge":
        return "The bounded dream line now most plausibly points toward a communication-framing nudge later."
    if proposal_type == "focus-nudge":
        return "The bounded dream line now most plausibly points toward a direction-framing nudge later."
    if proposal_type == "challenge-nudge":
        return "The bounded dream line now most plausibly points toward a challenge-posture nudge later."
    return "The bounded dream line now most plausibly points toward a world-caution nudge later."


def _hypothesis_type_from_snapshot(*, snapshot: dict[str, object]) -> str:
    return str((snapshot.get("hypothesis") or {}).get("hypothesis_type") or (snapshot.get("hypothesis") or {}).get("signal_type") or "")


def _influence_target_from_summary(summary: str) -> str:
    text = str(summary or "").lower()
    if "communication nudge" in text:
        return "self-model"
    if "direction-framing" in text:
        return "goals"
    if "challenge-posture" in text:
        return "development-focus"
    return "world-model"


def _proposal_confidence_from_summary(summary: str) -> str:
    text = str(summary or "").lower()
    if "proposal confidence stays high" in text:
        return "high"
    if "bounded future" in text:
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
