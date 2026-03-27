from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.self_authored_prompt_proposal_tracking import (
    build_runtime_self_authored_prompt_proposal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_user_md_update_proposals,
    supersede_runtime_user_md_update_proposals_for_dimension,
    update_runtime_user_md_update_proposal_status,
    upsert_runtime_user_md_update_proposal,
)

_STALE_AFTER_DAYS = 14


def track_runtime_user_md_update_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_user_md_update_proposals(
        proposals=_extract_user_md_update_proposals(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded USER.md update proposals."
            if items
            else "No bounded USER.md update proposal warranted tracking."
        ),
    }


def refresh_runtime_user_md_update_proposal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_user_md_update_proposals(limit=40):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_user_md_update_proposal_status(
            str(item.get("proposal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded USER.md proposal inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "user_md_update_proposal.stale",
            {
                "proposal_id": refreshed_item.get("proposal_id"),
                "proposal_type": refreshed_item.get("proposal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_user_md_update_proposal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_user_md_update_proposal_statuses()
    items = list_runtime_user_md_update_proposals(limit=max(limit, 1))
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
            "current_proposal": str((latest or {}).get("title") or "No active USER.md update proposal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_proposal_type": str((latest or {}).get("proposal_type") or "none"),
            "current_proposal_confidence": str((latest or {}).get("proposal_confidence") or "low"),
        },
    }


def _extract_user_md_update_proposals() -> list[dict[str, object]]:
    proposals: list[dict[str, object]] = []
    for item in build_runtime_self_authored_prompt_proposal_surface(limit=12).get("items", []):
        prompt_status = str(item.get("status") or "")
        if prompt_status not in {"fresh", "active", "fading"}:
            continue
        proposal_type = _build_proposal_type(item=item)
        if not proposal_type:
            continue
        user_dimension = _build_user_dimension(item=item, proposal_type=proposal_type)
        proposal_confidence = _build_proposal_confidence(
            prompt_confidence=str(item.get("proposal_confidence") or ""),
            proposal_type=proposal_type,
        )
        proposed_update = _build_proposed_update(proposal_type=proposal_type)
        proposal_reason = _build_proposal_reason(
            proposal_type=proposal_type,
            proposal_confidence=proposal_confidence,
        )
        source_anchor = _build_source_anchor(item=item)
        proposals.append(
            {
                "proposal_type": proposal_type,
                "canonical_key": f"user-md-update-proposal:{proposal_type}:{user_dimension}",
                "dimension_key": user_dimension,
                "status": prompt_status,
                "title": f"USER.md update proposal: {_title_suffix(user_dimension)}",
                "summary": proposal_reason,
                "rationale": str(item.get("proposal_reason") or item.get("summary") or "")
                or "A bounded self-authored prompt proposal now points toward a small USER.md update proposal.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(
                    str(item.get("confidence") or "low"),
                    proposal_confidence,
                ),
                "evidence_summary": str(item.get("evidence_summary") or ""),
                "support_summary": _merge_fragments(
                    str(item.get("support_summary") or ""),
                    source_anchor,
                    proposed_update,
                ),
                "support_count": int(item.get("support_count") or 1),
                "session_count": int(item.get("session_count") or 1),
                "status_reason": _build_status_reason(proposal_type=proposal_type),
                "user_dimension": user_dimension,
                "proposed_update": proposed_update,
                "proposal_reason": proposal_reason,
                "proposal_confidence": proposal_confidence,
                "source_anchor": source_anchor,
            }
        )
    return proposals[:4]


def _persist_user_md_update_proposals(
    *,
    proposals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    existing_by_key = {
        str(item.get("canonical_key") or ""): item for item in list_runtime_user_md_update_proposals(limit=40)
    }
    persisted: list[dict[str, object]] = []
    for proposal in proposals:
        existing = existing_by_key.get(str(proposal.get("canonical_key") or ""))
        persisted_item = upsert_runtime_user_md_update_proposal(
            proposal_id=f"user-md-update-proposal-{uuid4().hex}",
            proposal_type=str(proposal.get("proposal_type") or "preference-update"),
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
        superseded_count = supersede_runtime_user_md_update_proposals_for_dimension(
            dimension_key=str(proposal.get("dimension_key") or ""),
            exclude_proposal_id=str(persisted_item.get("proposal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded USER.md update proposal for the same user dimension.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "user_md_update_proposal.superseded",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "user_md_update_proposal.created",
                {
                    "proposal_id": persisted_item.get("proposal_id"),
                    "proposal_type": persisted_item.get("proposal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "user_md_update_proposal.updated",
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
    enriched["user_dimension"] = str(proposal.get("user_dimension") or "")
    enriched["proposed_update"] = str(proposal.get("proposed_update") or "")
    enriched["proposal_reason"] = str(proposal.get("proposal_reason") or item.get("summary") or "")
    enriched["proposal_confidence"] = str(proposal.get("proposal_confidence") or "low")
    enriched["source_anchor"] = str(proposal.get("source_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["user_dimension"] = _dimension_from_canonical_key(str(item.get("canonical_key") or ""))
    enriched["proposed_update"] = str(item.get("support_summary") or "")
    enriched["proposal_reason"] = str(item.get("summary") or "")
    enriched["proposal_confidence"] = _proposal_confidence_from_summary(str(item.get("summary") or ""))
    enriched["source_anchor"] = _source_anchor_from_support_summary(str(item.get("support_summary") or ""))
    return enriched


def _build_proposal_type(*, item: dict[str, object]) -> str:
    prompt_type = str(item.get("proposal_type") or "")
    mapping = {
        "communication-nudge": "preference-update",
        "focus-nudge": "workstyle-update",
        "challenge-nudge": "cadence-preference-update",
        "world-caution-nudge": "reminder-worthiness-update",
    }
    return mapping.get(prompt_type, "")


def _build_user_dimension(*, item: dict[str, object], proposal_type: str) -> str:
    prompt_target = str(item.get("prompt_target") or "")
    if proposal_type == "preference-update":
        return "reply-style"
    if proposal_type == "workstyle-update":
        return "workstyle"
    if proposal_type == "cadence-preference-update":
        return "cadence-preference"
    if prompt_target == "world-caution":
        return "reminder-worthiness"
    return "user-insight"


def _build_proposed_update(*, proposal_type: str) -> str:
    if proposal_type == "preference-update":
        return "User appears to prefer plain, grounded, and concise replies."
    if proposal_type == "workstyle-update":
        return "User appears to prefer keeping direction stable once a thread is active."
    if proposal_type == "cadence-preference-update":
        return "User appears to prefer challenge or review before settling too quickly."
    return "User-facing reminders may be worth surfacing when assumptions or context look fragile."


def _build_proposal_reason(*, proposal_type: str, proposal_confidence: str) -> str:
    if proposal_type == "preference-update":
        return "This bounded lane now looks like a small durable preference update candidate for USER.md, not a writeback."
    if proposal_type == "workstyle-update":
        return "This bounded lane now looks like a small workstyle update candidate for USER.md, not a profile mutation."
    if proposal_type == "cadence-preference-update":
        return "This bounded lane now looks like a small cadence-preference update candidate for USER.md while it remains tentative."
    return f"This bounded lane now looks like a small reminder-worthiness update candidate for USER.md while proposal confidence stays {proposal_confidence}."


def _build_proposal_confidence(*, prompt_confidence: str, proposal_type: str) -> str:
    if proposal_type in {"preference-update", "workstyle-update"} and prompt_confidence == "high":
        return "high"
    if prompt_confidence in {"high", "medium"}:
        return "medium"
    return "low"


def _build_source_anchor(*, item: dict[str, object]) -> str:
    parts = [
        str(item.get("proposal_type") or ""),
        str(item.get("prompt_target") or ""),
        str(item.get("influence_anchor") or ""),
    ]
    return " · ".join([part for part in parts if part][:3])


def _build_status_reason(*, proposal_type: str) -> str:
    if proposal_type == "preference-update":
        return "The bounded lane now most plausibly points toward a durable reply preference note later."
    if proposal_type == "workstyle-update":
        return "The bounded lane now most plausibly points toward a durable workstyle note later."
    if proposal_type == "cadence-preference-update":
        return "The bounded lane now most plausibly points toward a durable cadence-preference note later."
    return "The bounded lane now most plausibly points toward a durable reminder-worthiness note later."


def _title_suffix(user_dimension: str) -> str:
    text = str(user_dimension or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "User insight"


def _dimension_from_canonical_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _proposal_confidence_from_summary(summary: str) -> str:
    text = str(summary or "").lower()
    if "proposal confidence stays high" in text:
        return "high"
    if "bounded lane now looks" in text:
        return "medium"
    return "low"


def _source_anchor_from_support_summary(summary: str) -> str:
    parts = [part.strip() for part in str(summary or "").split("|") if part.strip()]
    return parts[1] if len(parts) > 1 else (parts[0] if parts else "")


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
