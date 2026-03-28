from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.executive_contradiction_signal_tracking import (
    build_runtime_executive_contradiction_signal_surface,
)
from apps.api.jarvis_api.services.private_state_snapshot_tracking import (
    build_runtime_private_state_snapshot_surface,
)
from apps.api.jarvis_api.services.private_temporal_promotion_signal_tracking import (
    build_runtime_private_temporal_promotion_signal_surface,
)
from apps.api.jarvis_api.services.remembered_fact_signal_tracking import (
    build_runtime_remembered_fact_signal_surface,
)
from apps.api.jarvis_api.services.self_review_cadence_signal_tracking import (
    build_runtime_self_review_cadence_signal_surface,
)
from apps.api.jarvis_api.services.self_review_outcome_tracking import (
    build_runtime_self_review_outcome_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_chronicle_consolidation_signals,
    supersede_runtime_chronicle_consolidation_signals_for_domain,
    update_runtime_chronicle_consolidation_signal_status,
    upsert_runtime_chronicle_consolidation_signal,
)

_STALE_AFTER_DAYS = 14
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_chronicle_consolidation_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_chronicle_consolidation_signals(
        signals=_extract_chronicle_consolidation_candidates(run_id=run_id),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded chronicle/consolidation signals."
            if items
            else "No bounded chronicle/consolidation signal warranted tracking."
        ),
    }


def refresh_runtime_chronicle_consolidation_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_chronicle_consolidation_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_chronicle_consolidation_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded chronicle/consolidation inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "chronicle_consolidation_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_chronicle_consolidation_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_chronicle_consolidation_signal_statuses()
    items = list_runtime_chronicle_consolidation_signals(limit=max(limit, 1))
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
            "current_signal": str((latest or {}).get("title") or "No active chronicle/consolidation support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_chronicle_type": str((latest or {}).get("chronicle_type") or "none"),
            "current_weight": str((latest or {}).get("chronicle_weight") or "low"),
            "current_confidence": str((latest or {}).get("chronicle_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "writeback_state": "not-writing-to-canonical-files",
        },
    }


def _extract_chronicle_consolidation_candidates(*, run_id: str) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for item in build_runtime_self_review_outcome_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["self_review_outcome"] = item

    for item in build_runtime_self_review_cadence_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["self_review_cadence"] = item

    for item in build_runtime_private_state_snapshot_surface(limit=12).get("items", []):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["private_state"] = item

    for item in build_runtime_private_temporal_promotion_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["temporal_promotion"] = item

    for item in build_runtime_executive_contradiction_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["executive_contradiction"] = item

    for item in build_runtime_remembered_fact_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["remembered_fact"] = item

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        outcome = snapshot.get("self_review_outcome")
        cadence = snapshot.get("self_review_cadence")
        if outcome is None or cadence is None:
            continue

        private_state = snapshot.get("private_state")
        temporal_promotion = snapshot.get("temporal_promotion")
        executive_contradiction = snapshot.get("executive_contradiction")
        remembered_fact = snapshot.get("remembered_fact")

        cadence_state = str(cadence.get("cadence_state") or "due")
        outcome_type = str(outcome.get("outcome_type") or "bounded-review")
        promotion_type = str((temporal_promotion or {}).get("promotion_type") or "")
        contradiction_pressure = str((executive_contradiction or {}).get("control_pressure") or "")

        chronicle_type = _chronicle_type(
            cadence_state=cadence_state,
            promotion_type=promotion_type,
            has_remembered_fact=remembered_fact is not None,
        )
        status = "active" if cadence_state in {"due", "lingering"} or temporal_promotion else "softening"
        chronicle_weight = _chronicle_weight(
            cadence_state=cadence_state,
            has_promotion=temporal_promotion is not None,
            contradiction_pressure=contradiction_pressure,
            outcome_status=str(outcome.get("status") or ""),
        )
        chronicle_focus = _focus_text(outcome, cadence, domain_key=domain_key)
        chronicle_summary = _merge_fragments(
            str(outcome.get("short_outcome") or outcome.get("summary") or ""),
            str(cadence.get("cadence_reason") or cadence.get("summary") or ""),
            str((private_state or {}).get("state_summary") or ""),
            str((temporal_promotion or {}).get("promotion_summary") or ""),
        )[:220]
        chronicle_confidence = _stronger_confidence(
            str(outcome.get("confidence") or "low"),
            str(cadence.get("confidence") or "low"),
            str((private_state or {}).get("state_confidence") or (private_state or {}).get("confidence") or ""),
            str((temporal_promotion or {}).get("promotion_confidence") or (temporal_promotion or {}).get("confidence") or ""),
            str((remembered_fact or {}).get("signal_confidence") or (remembered_fact or {}).get("confidence") or ""),
            str((executive_contradiction or {}).get("control_confidence") or (executive_contradiction or {}).get("confidence") or ""),
        )
        source_anchor = _merge_fragments(
            _anchor(outcome),
            _anchor(cadence),
            _anchor(private_state),
            _anchor(temporal_promotion),
            _anchor(remembered_fact),
            _anchor(executive_contradiction),
        )
        evidence_summary = _merge_fragments(
            str(outcome.get("evidence_summary") or ""),
            str(cadence.get("evidence_summary") or ""),
            str((private_state or {}).get("evidence_summary") or ""),
            str((temporal_promotion or {}).get("evidence_summary") or ""),
            str((remembered_fact or {}).get("evidence_summary") or ""),
            str((executive_contradiction or {}).get("evidence_summary") or ""),
        )
        support_summary = _merge_fragments(
            "Derived only from self-review outcome, self-review cadence, and optional bounded state/promotion/fact/contradiction support.",
            source_anchor,
        )
        candidates.append(
            {
                "signal_type": "chronicle-consolidation",
                "canonical_key": f"chronicle-consolidation:{chronicle_type}:{domain_key}",
                "domain_key": domain_key,
                "status": status,
                "title": f"Chronicle consolidation support: {chronicle_focus}",
                "summary": _summary_line(
                    chronicle_type=chronicle_type,
                    chronicle_focus=chronicle_focus,
                ),
                "rationale": (
                    "A bounded chronicle/consolidation signal may return only when bounded self-review outcome and cadence already indicate a thread that looks worth carrying or consolidating, without writing to canonical files or becoming a diary engine."
                ),
                "source_kind": "runtime-derived-support",
                "confidence": chronicle_confidence,
                "evidence_summary": evidence_summary,
                "support_summary": support_summary,
                "support_count": 1,
                "session_count": 1,
                "status_reason": (
                    "Bounded chronicle/consolidation support remains non-authoritative runtime support and is not yet writing to chronicle or memory files."
                ),
                "chronicle_type": chronicle_type,
                "chronicle_focus": chronicle_focus,
                "chronicle_weight": chronicle_weight,
                "chronicle_summary": chronicle_summary,
                "chronicle_confidence": chronicle_confidence,
                "source_anchor": source_anchor,
                "grounding_mode": _grounding_mode(
                    has_private_state=private_state is not None,
                    has_temporal_promotion=temporal_promotion is not None,
                    has_remembered_fact=remembered_fact is not None,
                    has_executive_contradiction=executive_contradiction is not None,
                ),
                "writeback_state": "not-writing-to-canonical-files",
            }
        )

    return candidates[:4]


def _persist_chronicle_consolidation_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_chronicle_consolidation_signal(
            signal_id=f"chronicle-consolidation-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "chronicle-consolidation"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "runtime-derived-support"),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=str(signal.get("support_summary") or ""),
            status_reason=str(signal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
        )
        superseded_count = supersede_runtime_chronicle_consolidation_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded chronicle/consolidation signal for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "chronicle_consolidation_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "chronicle_consolidation_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "chronicle_consolidation_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched.update(
        {
            "chronicle_type": signal.get("chronicle_type"),
            "chronicle_focus": signal.get("chronicle_focus"),
            "chronicle_weight": signal.get("chronicle_weight"),
            "chronicle_summary": signal.get("chronicle_summary"),
            "chronicle_confidence": signal.get("chronicle_confidence"),
            "source_anchor": signal.get("source_anchor"),
            "grounding_mode": signal.get("grounding_mode"),
            "writeback_state": signal.get("writeback_state"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        }
    )
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    chronicle_type = _value(
        item.get("chronicle_type"),
        _canonical_segment(str(item.get("canonical_key") or ""), index=1),
        default="chronicle-worthy",
    )
    chronicle_focus = _value(item.get("chronicle_focus"), item.get("title"), default="visible thread")
    chronicle_weight = _value(item.get("chronicle_weight"), default="medium")
    chronicle_summary = _value(
        item.get("chronicle_summary"),
        item.get("summary"),
        default="No bounded chronicle/consolidation support.",
    )
    chronicle_confidence = _value(
        item.get("chronicle_confidence"),
        item.get("confidence"),
        default="low",
    )
    enriched = dict(item)
    enriched.update(
        {
            "chronicle_type": chronicle_type,
            "chronicle_focus": chronicle_focus,
            "chronicle_weight": chronicle_weight,
            "chronicle_summary": chronicle_summary,
            "chronicle_confidence": chronicle_confidence,
            "source_anchor": _anchor(item),
            "grounding_mode": _value(item.get("grounding_mode"), default="self-review-outcome+self-review-cadence"),
            "writeback_state": _value(item.get("writeback_state"), default="not-writing-to-canonical-files"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "source": "/mc/runtime.chronicle_consolidation_signal",
            "createdAt": str(item.get("created_at") or ""),
        }
    )
    return enriched


def _chronicle_type(
    *,
    cadence_state: str,
    promotion_type: str,
    has_remembered_fact: bool,
) -> str:
    if promotion_type == "carry-forward":
        return "consolidation-worthy"
    if cadence_state == "lingering":
        return "carry-forward-thread"
    if has_remembered_fact:
        return "anchored-thread"
    return "chronicle-worthy"


def _chronicle_weight(
    *,
    cadence_state: str,
    has_promotion: bool,
    contradiction_pressure: str,
    outcome_status: str,
) -> str:
    if contradiction_pressure == "high" or (has_promotion and cadence_state in {"due", "lingering"}):
        return "high"
    if outcome_status in {"fresh", "active"} or cadence_state in {"due", "lingering"}:
        return "medium"
    return "low"


def _focus_text(
    outcome: dict[str, object],
    cadence: dict[str, object],
    *,
    domain_key: str,
) -> str:
    for key in ("review_focus", "chronicle_focus", "title", "summary"):
        value = str(outcome.get(key) or "").strip()
        if value:
            return value[:96]
    value = str(cadence.get("title") or "").strip()
    if value:
        return value[:96]
    return domain_key.replace("-", " ")[:96]


def _summary_line(*, chronicle_type: str, chronicle_focus: str) -> str:
    return (
        f"Bounded chronicle/consolidation support is marking {chronicle_focus.lower()} as {chronicle_type.replace('-', ' ')}."
    )


def _grounding_mode(
    *,
    has_private_state: bool,
    has_temporal_promotion: bool,
    has_remembered_fact: bool,
    has_executive_contradiction: bool,
) -> str:
    parts = ["self-review-outcome", "self-review-cadence"]
    if has_private_state:
        parts.append("private-state")
    if has_temporal_promotion:
        parts.append("temporal-promotion")
    if has_remembered_fact:
        parts.append("remembered-fact")
    if has_executive_contradiction:
        parts.append("executive-contradiction")
    return "+".join(parts)


def _domain_key(canonical_key: str) -> str:
    parts = [part.strip() for part in canonical_key.split(":") if part.strip()]
    if len(parts) >= 3:
        return _slug(parts[-1])
    return ""


def _canonical_segment(value: str, *, index: int) -> str:
    parts = [part.strip() for part in value.split(":") if part.strip()]
    if len(parts) > index:
        return parts[index]
    return ""


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    return str(item.get("source_anchor") or item.get("support_summary") or item.get("summary") or "").strip()[:180]


def _merge_fragments(*parts: str) -> str:
    seen: list[str] = []
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.append(normalized)
    return " | ".join(seen)


def _stronger_confidence(*values: str) -> str:
    winner = "low"
    best = -1
    for value in values:
        rank = _CONFIDENCE_RANKS.get(str(value or "").strip().lower(), -1)
        if rank > best:
            best = rank
            winner = str(value or "").strip().lower() or "low"
    return winner


def _value(*values: object, default: str = "") -> str:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return default


def _slug(value: str) -> str:
    lowered = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    collapsed = "-".join(part for part in lowered.split("-") if part)
    return collapsed[:64]


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
