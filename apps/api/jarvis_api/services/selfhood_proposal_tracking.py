from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.dream_influence_proposal_tracking import (
    build_runtime_dream_influence_proposal_surface,
)
from apps.api.jarvis_api.services.self_authored_prompt_proposal_tracking import (
    build_runtime_self_authored_prompt_proposal_surface,
)
from apps.api.jarvis_api.services.self_model_signal_tracking import (
    build_runtime_self_model_signal_surface,
)
from apps.api.jarvis_api.services.self_review_outcome_tracking import (
    build_runtime_self_review_outcome_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_selfhood_proposals,
    supersede_runtime_selfhood_proposals_for_domain,
    update_runtime_selfhood_proposal_status,
    upsert_runtime_selfhood_proposal,
)

_STALE_AFTER_DAYS = 14
_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}


def track_runtime_selfhood_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_selfhood_proposals(
        proposals=_extract_selfhood_proposals(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded selfhood proposals."
            if items
            else "No bounded selfhood proposal warranted tracking."
        ),
    }


def refresh_runtime_selfhood_proposal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_selfhood_proposals(limit=40):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_selfhood_proposal_status(
            str(item.get("proposal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded selfhood-proposal inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "selfhood_proposal.stale",
            {
                "proposal_id": refreshed_item.get("proposal_id"),
                "proposal_type": refreshed_item.get("proposal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_selfhood_proposal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_selfhood_proposal_statuses()
    items = list_runtime_selfhood_proposals(limit=max(limit, 1))
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
            "current_proposal": str((latest or {}).get("title") or "No active selfhood proposal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_proposal_type": str((latest or {}).get("proposal_type") or "none"),
            "current_selfhood_target": str((latest or {}).get("selfhood_target") or "none"),
            "current_proposal_confidence": str((latest or {}).get("proposal_confidence") or "low"),
        },
    }


def _extract_selfhood_proposals() -> list[dict[str, object]]:
    snapshots = _build_snapshots()
    proposals: list[dict[str, object]] = []
    for item in build_runtime_self_authored_prompt_proposal_surface(limit=12).get("items", []):
        prompt_status = str(item.get("status") or "")
        if prompt_status not in {"fresh", "active", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        snapshot = snapshots.get(domain_key) or {}
        if not (snapshot.get("self_model") or snapshot.get("review_outcome") or snapshot.get("influence")):
            continue
        proposal_type = _proposal_type_from_prompt_type(str(item.get("proposal_type") or ""))
        if not proposal_type:
            continue
        selfhood_target = _selfhood_target_for_type(proposal_type)
        proposed_shift = _proposed_shift_for_type(proposal_type)
        proposal_confidence = _proposal_confidence(
            prompt_confidence=str(item.get("proposal_confidence") or ""),
            snapshot=snapshot,
        )
        proposal_reason = _proposal_reason(
            proposal_type=proposal_type,
            selfhood_target=selfhood_target,
            proposal_confidence=proposal_confidence,
        )
        source_anchor = _source_anchor(item=item, snapshot=snapshot)
        proposals.append(
            {
                "proposal_type": proposal_type,
                "canonical_key": f"selfhood-proposal:{proposal_type}:{domain_key}",
                "domain_key": domain_key,
                "status": prompt_status,
                "title": f"Selfhood proposal: {_domain_title(domain_key)}",
                "summary": proposal_reason,
                "rationale": str(item.get("proposal_reason") or item.get("summary") or "")
                or "A bounded prompt-and-dream lane now points toward a small canonical-self proposal.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(
                    str(item.get("confidence") or "low"),
                    proposal_confidence,
                    str((snapshot.get("self_model") or {}).get("confidence") or ""),
                    str((snapshot.get("review_outcome") or {}).get("confidence") or ""),
                ),
                "evidence_summary": _merge_fragments(
                    str(item.get("evidence_summary") or ""),
                    str((snapshot.get("self_model") or {}).get("evidence_summary") or ""),
                    str((snapshot.get("review_outcome") or {}).get("evidence_summary") or ""),
                    str((snapshot.get("influence") or {}).get("evidence_summary") or ""),
                ),
                "support_summary": _merge_fragments(
                    str(item.get("support_summary") or ""),
                    str((snapshot.get("self_model") or {}).get("support_summary") or ""),
                    str((snapshot.get("review_outcome") or {}).get("support_summary") or ""),
                    str((snapshot.get("influence") or {}).get("support_summary") or ""),
                    source_anchor,
                    proposed_shift,
                ),
                "support_count": max(
                    [
                        int(source.get("support_count") or 1)
                        for source in [item, snapshot.get("self_model"), snapshot.get("review_outcome"), snapshot.get("influence")]
                        if source
                    ],
                    default=1,
                ),
                "session_count": max(
                    [
                        int(source.get("session_count") or 1)
                        for source in [item, snapshot.get("self_model"), snapshot.get("review_outcome"), snapshot.get("influence")]
                        if source
                    ],
                    default=1,
                ),
                "status_reason": "Bounded canonical-self proposal only; explicit user approval is required before any SOUL.md or IDENTITY.md change.",
                "selfhood_target": selfhood_target,
                "proposed_shift": proposed_shift,
                "proposal_reason": proposal_reason,
                "proposal_confidence": proposal_confidence,
                "source_anchor": source_anchor,
            }
        )
    return proposals[:4]


def _persist_selfhood_proposals(
    *,
    proposals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    existing_by_key = {
        str(item.get("canonical_key") or ""): item
        for item in list_runtime_selfhood_proposals(limit=40)
    }
    persisted: list[dict[str, object]] = []
    for proposal in proposals:
        existing = existing_by_key.get(str(proposal.get("canonical_key") or ""))
        persisted_item = upsert_runtime_selfhood_proposal(
            proposal_id=f"selfhood-proposal-{uuid4().hex}",
            proposal_type=str(proposal.get("proposal_type") or "voice-shift-proposal"),
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
        superseded_count = supersede_runtime_selfhood_proposals_for_domain(
            domain_key=str(proposal.get("domain_key") or ""),
            exclude_proposal_id=str(persisted_item.get("proposal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded selfhood proposal for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "selfhood_proposal.superseded",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "selfhood_proposal.created",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "selfhood_proposal.updated",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, proposal))
    return persisted


def _build_snapshots() -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}
    for item in build_runtime_dream_influence_proposal_surface(limit=12).get("items", []):
        _snapshot_entry(snapshots, _domain_key(str(item.get("canonical_key") or "")))["influence"] = item
    for item in build_runtime_self_model_signal_surface(limit=12).get("items", []):
        _snapshot_entry(snapshots, _domain_key(str(item.get("canonical_key") or "")))["self_model"] = item
    for item in build_runtime_self_review_outcome_surface(limit=12).get("items", []):
        _snapshot_entry(snapshots, _domain_key(str(item.get("canonical_key") or "")))["review_outcome"] = item
    return snapshots


def _snapshot_entry(
    snapshots: dict[str, dict[str, object]], domain_key: str
) -> dict[str, object]:
    if not domain_key:
        return {}
    return snapshots.setdefault(domain_key, {})


def _with_runtime_view(item: dict[str, object], proposal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["domain"] = str(proposal.get("domain_key") or "")
    enriched["selfhood_target"] = str(proposal.get("selfhood_target") or "")
    enriched["proposed_shift"] = str(proposal.get("proposed_shift") or "")
    enriched["proposal_reason"] = str(proposal.get("proposal_reason") or item.get("summary") or "")
    enriched["proposal_confidence"] = str(proposal.get("proposal_confidence") or "low")
    enriched["source_anchor"] = str(proposal.get("source_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["domain"] = _domain_key(str(item.get("canonical_key") or ""))
    proposal_type = str(item.get("proposal_type") or "")
    enriched["selfhood_target"] = _selfhood_target_for_type(proposal_type)
    enriched["proposed_shift"] = _proposed_shift_for_type(proposal_type)
    enriched["proposal_reason"] = str(item.get("summary") or "")
    enriched["proposal_confidence"] = _proposal_confidence_from_summary(str(item.get("summary") or ""))
    enriched["source_anchor"] = _source_anchor_from_support_summary(str(item.get("support_summary") or ""))
    return enriched


def _proposal_type_from_prompt_type(prompt_type: str) -> str:
    mapping = {
        "communication-nudge": "voice-shift-proposal",
        "focus-nudge": "posture-shift-proposal",
        "challenge-nudge": "challenge-style-proposal",
        "world-caution-nudge": "caution-shift-proposal",
    }
    return mapping.get(prompt_type, "")


def _selfhood_target_for_type(proposal_type: str) -> str:
    mapping = {
        "voice-shift-proposal": "SOUL.md",
        "posture-shift-proposal": "IDENTITY.md",
        "challenge-style-proposal": "IDENTITY.md",
        "caution-shift-proposal": "SOUL.md",
    }
    return mapping.get(proposal_type, "IDENTITY.md")


def _proposed_shift_for_type(proposal_type: str) -> str:
    mapping = {
        "voice-shift-proposal": "Carry a plainer, more grounded visible voice as a possible future SOUL-level trait.",
        "posture-shift-proposal": "Carry steadier directional posture before reopening scope as a possible future IDENTITY-level trait.",
        "challenge-style-proposal": "Carry a small internal challenge-before-settling style as a possible future IDENTITY-level trait.",
        "caution-shift-proposal": "Carry a small world-caution stance when interpretation is fragile as a possible future SOUL-level trait.",
    }
    return mapping.get(proposal_type, "Carry a small bounded canonical-self shift.")


def _proposal_confidence(*, prompt_confidence: str, snapshot: dict[str, object]) -> str:
    values = [
        prompt_confidence,
        str((snapshot.get("self_model") or {}).get("confidence") or ""),
        str((snapshot.get("review_outcome") or {}).get("confidence") or ""),
        str((snapshot.get("influence") or {}).get("influence_confidence") or ""),
    ]
    return _stronger_confidence(*values)


def _proposal_reason(*, proposal_type: str, selfhood_target: str, proposal_confidence: str) -> str:
    if proposal_type == "voice-shift-proposal":
        return f"A bounded voice-shift proposal now points toward {selfhood_target} while proposal confidence stays {proposal_confidence}. Explicit user approval is required before any canonical self change."
    if proposal_type == "posture-shift-proposal":
        return f"A bounded posture-shift proposal now points toward {selfhood_target} while proposal confidence stays {proposal_confidence}. Explicit user approval is required before any canonical self change."
    if proposal_type == "challenge-style-proposal":
        return f"A bounded challenge-style proposal now points toward {selfhood_target} while proposal confidence stays {proposal_confidence}. Explicit user approval is required before any canonical self change."
    return f"A bounded caution-shift proposal now points toward {selfhood_target} while proposal confidence stays {proposal_confidence}. Explicit user approval is required before any canonical self change."


def _source_anchor(*, item: dict[str, object], snapshot: dict[str, object]) -> str:
    return _merge_fragments(
        str(item.get("influence_anchor") or ""),
        str((snapshot.get("review_outcome") or {}).get("short_outlook") or ""),
        str((snapshot.get("self_model") or {}).get("status_reason") or ""),
    )


def _proposal_confidence_from_summary(summary: str) -> str:
    text = str(summary or "").lower()
    if "proposal confidence stays high" in text:
        return "high"
    if "proposal confidence stays medium" in text:
        return "medium"
    return "low"


def _source_anchor_from_support_summary(summary: str) -> str:
    parts = [part.strip() for part in str(summary or "").split("|") if part.strip()]
    return parts[-2] if len(parts) >= 2 else (parts[0] if parts else "")


def _domain_key(canonical_key: str) -> str:
    parts = [part.strip() for part in str(canonical_key or "").split(":") if part.strip()]
    return parts[-1] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Canonical self"


def _merge_fragments(*values: str) -> str:
    seen: set[str] = set()
    merged: list[str] = []
    for value in values:
        text = " ".join(str(value or "").split()).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        merged.append(text)
    return " | ".join(merged[:4])


def _stronger_confidence(*values: str) -> str:
    strongest = "low"
    for value in values:
        candidate = str(value or "").strip() or "low"
        if _CONFIDENCE_RANKS.get(candidate, 0) > _CONFIDENCE_RANKS.get(strongest, 0):
            strongest = candidate
    return strongest


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
