from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.dream_hypothesis_signal_tracking import (
    build_runtime_dream_hypothesis_signal_surface,
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
    list_runtime_development_focuses,
    list_runtime_dream_adoption_candidates,
    list_runtime_goal_signals,
    list_runtime_self_model_signals,
    supersede_runtime_dream_adoption_candidates_for_domain,
    update_runtime_dream_adoption_candidate_status,
    upsert_runtime_dream_adoption_candidate,
)

_STALE_AFTER_DAYS = 14


def track_runtime_dream_adoption_candidates_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_dream_adoption_candidates(
        candidates=_extract_dream_adoption_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded dream adoption candidates."
            if items
            else "No bounded dream adoption candidate warranted tracking."
        ),
    }


def refresh_runtime_dream_adoption_candidate_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_dream_adoption_candidates(limit=40):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_dream_adoption_candidate_status(
            str(item.get("candidate_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded dream-adoption candidate inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "dream_adoption_candidate.stale",
            {
                "candidate_id": refreshed_item.get("candidate_id"),
                "candidate_type": refreshed_item.get("candidate_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_dream_adoption_candidate_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_dream_adoption_candidate_statuses()
    items = list_runtime_dream_adoption_candidates(limit=max(limit, 1))
    snapshots = _build_adoption_snapshots()
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
            "current_candidate": str((latest or {}).get("title") or "No active dream adoption candidate"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_candidate_type": str((latest or {}).get("candidate_type") or "none"),
            "current_adoption_confidence": str((latest or {}).get("adoption_confidence") or "low"),
        },
    }


def _extract_dream_adoption_candidates() -> list[dict[str, object]]:
    snapshots = _build_adoption_snapshots()
    candidates: list[dict[str, object]] = []

    for item in build_runtime_dream_hypothesis_signal_surface(limit=12).get("items", []):
        hypothesis_status = str(item.get("status") or "")
        if hypothesis_status not in {"active", "integrating", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        snapshot = snapshots.get(domain_key) or {}
        candidate_type = _build_candidate_type(item=item, snapshot=snapshot)
        if not candidate_type:
            continue
        adoption_confidence = _build_adoption_confidence(candidate_type=candidate_type, snapshot=snapshot)
        adoption_reason = _build_adoption_reason(
            candidate_type=candidate_type,
            hypothesis_type=str(item.get("hypothesis_type") or item.get("signal_type") or ""),
            adoption_confidence=adoption_confidence,
        )
        adoption_anchor = _build_adoption_anchor(snapshot=snapshot)
        source_items = [
            item,
            snapshot.get("witness"),
            snapshot.get("review_outcome"),
            snapshot.get("review_cadence"),
            snapshot.get("focus"),
            snapshot.get("goal"),
            snapshot.get("self_model"),
        ]
        candidates.append(
            {
                "candidate_type": candidate_type,
                "canonical_key": f"dream-adoption-candidate:{candidate_type}:{domain_key}",
                "domain_key": domain_key,
                "status": _build_candidate_status(
                    candidate_type=candidate_type,
                    hypothesis_status=hypothesis_status,
                    cadence_state=str((snapshot.get("review_cadence") or {}).get("cadence_state") or ""),
                ),
                "title": f"Dream adoption candidate: {_domain_title(domain_key)}",
                "summary": adoption_reason,
                "rationale": str(item.get("hypothesis_note") or item.get("summary") or "")
                or "A bounded dream hypothesis now looks strong enough to surface as a small adoption candidate.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(
                    str(item.get("confidence") or "low"),
                    adoption_confidence,
                    str((snapshot.get("goal") or {}).get("confidence") or ""),
                ),
                "evidence_summary": _merge_fragments(
                    *[str(source.get("evidence_summary") or "") for source in source_items if source]
                ),
                "support_summary": _merge_fragments(
                    *[str(source.get("support_summary") or "") for source in source_items if source],
                    adoption_anchor,
                ),
                "support_count": max([int(source.get("support_count") or 1) for source in source_items if source], default=1),
                "session_count": max([int(source.get("session_count") or 1) for source in source_items if source], default=1),
                "status_reason": _build_status_reason(candidate_type=candidate_type),
                "hypothesis_type": str(item.get("hypothesis_type") or item.get("signal_type") or ""),
                "adoption_state": candidate_type,
                "adoption_reason": adoption_reason,
                "adoption_confidence": adoption_confidence,
                "adoption_anchor": adoption_anchor,
            }
        )

    return candidates[:4]


def _persist_dream_adoption_candidates(
    *,
    candidates: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    existing_by_key = {
        str(item.get("canonical_key") or ""): item
        for item in list_runtime_dream_adoption_candidates(limit=40)
    }
    persisted: list[dict[str, object]] = []
    for candidate in candidates:
        existing = existing_by_key.get(str(candidate.get("canonical_key") or ""))
        persisted_item = upsert_runtime_dream_adoption_candidate(
            candidate_id=f"dream-adoption-candidate-{uuid4().hex}",
            candidate_type=str(candidate.get("candidate_type") or "tentative-candidate"),
            canonical_key=str(candidate.get("canonical_key") or ""),
            status="active" if existing and str(candidate.get("status") or "") == "fresh" else str(candidate.get("status") or "fresh"),
            title=str(candidate.get("title") or ""),
            summary=str(candidate.get("adoption_reason") or candidate.get("summary") or ""),
            rationale=str(candidate.get("rationale") or ""),
            source_kind=str(candidate.get("source_kind") or "runtime-derived-support"),
            confidence=str(candidate.get("confidence") or "low"),
            evidence_summary=str(candidate.get("evidence_summary") or ""),
            support_summary=str(candidate.get("support_summary") or ""),
            support_count=int(candidate.get("support_count") or 1),
            session_count=int(candidate.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(candidate.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        superseded_count = supersede_runtime_dream_adoption_candidates_for_domain(
            domain_key=str(candidate.get("domain_key") or ""),
            exclude_candidate_id=str(persisted_item.get("candidate_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded dream-adoption candidate for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "dream_adoption_candidate.superseded",
                {
                    "candidate_id": persisted_item.get("candidate_id"),
                    "candidate_type": persisted_item.get("candidate_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "dream_adoption_candidate.created",
                {
                    "candidate_id": persisted_item.get("candidate_id"),
                    "candidate_type": persisted_item.get("candidate_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "dream_adoption_candidate.updated",
                {
                    "candidate_id": persisted_item.get("candidate_id"),
                    "candidate_type": persisted_item.get("candidate_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, candidate))
    return persisted


def _build_adoption_snapshots() -> dict[str, dict[str, object]]:
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

    for item in build_runtime_self_review_cadence_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["review_cadence"] = item

    return snapshots


def _with_runtime_view(item: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["domain"] = _domain_key(str(item.get("canonical_key") or ""))
    enriched["hypothesis_type"] = str(candidate.get("hypothesis_type") or "")
    enriched["adoption_state"] = str(candidate.get("adoption_state") or item.get("candidate_type") or "")
    enriched["adoption_reason"] = str(candidate.get("adoption_reason") or item.get("summary") or "")
    enriched["adoption_confidence"] = str(candidate.get("adoption_confidence") or "low")
    enriched["adoption_anchor"] = str(candidate.get("adoption_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object], *, snapshots: dict[str, dict[str, object]]) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key) or {}
    enriched["domain"] = domain_key
    enriched["hypothesis_type"] = _hypothesis_type_from_candidate_key(str(item.get("canonical_key") or ""))
    enriched["adoption_state"] = str(item.get("candidate_type") or "")
    enriched["adoption_reason"] = str(item.get("summary") or "")
    enriched["adoption_confidence"] = _adoption_confidence_from_summary(str(item.get("summary") or ""))
    enriched["adoption_anchor"] = _build_adoption_anchor(snapshot=snapshot)
    return enriched


def _build_candidate_type(*, item: dict[str, object], snapshot: dict[str, object]) -> str:
    hypothesis_type = str(item.get("hypothesis_type") or item.get("signal_type") or "")
    witness_status = str((snapshot.get("witness") or {}).get("status") or "")
    outcome_type = str((snapshot.get("review_outcome") or {}).get("outcome_type") or "")
    has_goal = bool(snapshot.get("goal"))
    has_focus = bool(snapshot.get("focus"))

    if hypothesis_type == "carried-hypothesis" and witness_status == "carried" and outcome_type in {"carry-forward", "nearing-closure"} and (has_goal or has_focus):
        return "strong-candidate"
    if hypothesis_type in {"carried-hypothesis", "emerging-hypothesis"} and (witness_status in {"fresh", "carried"} or outcome_type == "carry-forward") and (has_goal or has_focus):
        return "carried-candidate"
    if has_focus or outcome_type in {"watch-closely", "challenge-further", "carry-forward"}:
        return "tentative-candidate"
    return ""


def _build_candidate_status(*, candidate_type: str, hypothesis_status: str, cadence_state: str) -> str:
    if candidate_type == "strong-candidate":
        return "fresh"
    if hypothesis_status == "fading" or cadence_state == "recently-reviewed":
        return "fading"
    return "active"


def _build_adoption_confidence(*, candidate_type: str, snapshot: dict[str, object]) -> str:
    if candidate_type == "strong-candidate":
        return "high"
    if candidate_type == "carried-candidate" or snapshot.get("witness"):
        return "medium"
    return "low"


def _build_adoption_reason(*, candidate_type: str, hypothesis_type: str, adoption_confidence: str) -> str:
    if candidate_type == "strong-candidate":
        return "This dream line now looks like a strong candidate to be carried forward later under explicit adoption rules."
    if candidate_type == "carried-candidate":
        return "This dream line now looks like something that could be carried forward, but it should stay bounded and reviewable."
    return f"This dream line is still tentative and should remain only a bounded candidate while adoption confidence stays {adoption_confidence}."


def _build_adoption_anchor(*, snapshot: dict[str, object]) -> str:
    parts: list[str] = []
    witness_type = str((snapshot.get("witness") or {}).get("signal_type") or "")
    outcome_type = str((snapshot.get("review_outcome") or {}).get("outcome_type") or "")
    cadence_state = str((snapshot.get("review_cadence") or {}).get("cadence_state") or "")
    goal_status = str((snapshot.get("goal") or {}).get("status") or "")
    if witness_type:
        parts.append(witness_type)
    if outcome_type:
        parts.append(outcome_type)
    if cadence_state:
        parts.append(cadence_state)
    if goal_status:
        parts.append(f"goal {goal_status}")
    return " · ".join(parts[:3])


def _build_status_reason(*, candidate_type: str) -> str:
    if candidate_type == "strong-candidate":
        return "Multiple bounded layers now agree that this dream line could plausibly be carried later."
    if candidate_type == "carried-candidate":
        return "The bounded dream line has enough continuity support to remain observable as a carried candidate."
    return "The bounded dream line remains tentative and should stay provisional."


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


def _self_model_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _hypothesis_type_from_candidate_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[1] if len(parts) >= 3 else ""


def _adoption_confidence_from_summary(summary: str) -> str:
    text = str(summary or "").lower()
    if "strong candidate" in text:
        return "high"
    if "could be carried forward" in text:
        return "medium"
    return "low"


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Thread"


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
