from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.self_review_cadence_signal_tracking import (
    build_runtime_self_review_cadence_signal_surface,
)
from core.services.signal_noise_guard import (
    build_bounded_hypothesis_text,
    is_noisy_signal_text,
)
from core.services.self_review_outcome_tracking import (
    build_runtime_self_review_outcome_surface,
)
from core.services.temporal_recurrence_signal_tracking import (
    build_runtime_temporal_recurrence_signal_surface,
)
from core.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_dream_hypothesis_signals,
    supersede_runtime_dream_hypothesis_signals_for_domain,
    update_runtime_dream_hypothesis_signal_status,
    upsert_runtime_dream_hypothesis_signal,
)

_STALE_AFTER_DAYS = 14
_EARLY_RETIRE_DAYS = 1
_REFRESH_SCAN_LIMIT = 3000


def track_runtime_dream_hypothesis_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_dream_hypothesis_signals(
        signals=_extract_dream_hypothesis_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded dream hypothesis signals."
            if items
            else "No bounded dream hypothesis signal warranted tracking."
        ),
    }


def refresh_runtime_dream_hypothesis_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_dream_hypothesis_signals(limit=_REFRESH_SCAN_LIMIT):
        if str(item.get("status") or "") not in {"active", "integrating", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None:
            continue
        retire_early = (
            str(item.get("confidence") or "") == "low"
            or int(item.get("support_count") or 0) <= 1
            or is_noisy_signal_text(str(item.get("title") or "") + " " + str(item.get("summary") or ""))
        )
        stale_after = _EARLY_RETIRE_DAYS if retire_early else _STALE_AFTER_DAYS
        if updated_at > now - timedelta(days=stale_after):
            continue
        refreshed_item = update_runtime_dream_hypothesis_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded dream-hypothesis inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "dream_hypothesis_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_dream_hypothesis_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_dream_hypothesis_signal_statuses()
    items = list_runtime_dream_hypothesis_signals(limit=max(limit, 1))
    snapshots = _build_dream_snapshots()
    enriched_items = [_with_surface_view(item, snapshots=snapshots) for item in items]
    active = [item for item in enriched_items if str(item.get("status") or "") == "active"]
    integrating = [item for item in enriched_items if str(item.get("status") or "") == "integrating"]
    fading = [item for item in enriched_items if str(item.get("status") or "") == "fading"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
    ordered = [*active, *integrating, *fading, *stale, *superseded]
    latest = next(iter(active or integrating or fading or stale or superseded), None)
    return {
        "active": bool(active or integrating or fading),
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "integrating_count": len(integrating),
            "fading_count": len(fading),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active dream hypothesis signal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_hypothesis_type": str((latest or {}).get("hypothesis_type") or "none"),
        },
    }


def _extract_dream_hypothesis_candidates() -> list[dict[str, object]]:
    snapshots = _build_dream_snapshots()
    candidates: list[dict[str, object]] = []

    for item in build_runtime_temporal_recurrence_signal_surface(limit=12).get("items", []):
        recurrence_status = str(item.get("status") or "")
        if recurrence_status not in {"active", "softening"}:
            continue
        domain_key = _recurrence_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        snapshot = snapshots.get(domain_key) or {}
        if not any(snapshot.get(key) for key in ("focus", "witness", "review_outcome", "review_cadence")):
            continue
        hypothesis_type = _build_hypothesis_type(item=item, snapshot=snapshot)
        if not hypothesis_type:
            continue
        title_suffix = _domain_title(domain_key)
        hypothesis_note = _build_hypothesis_note(
            hypothesis_type=hypothesis_type,
            recurrence_type=str(item.get("signal_type") or ""),
            domain_key=domain_key,
        )
        hypothesis_anchor = _build_hypothesis_anchor(snapshot=snapshot)
        source_items = [
            item,
            snapshot.get("focus"),
            snapshot.get("witness"),
            snapshot.get("review_outcome"),
            snapshot.get("review_cadence"),
        ]
        candidates.append(
            {
                "signal_type": hypothesis_type,
                "canonical_key": f"dream-hypothesis:{hypothesis_type}:{domain_key}",
                "domain_key": domain_key,
                "status": _build_signal_status(
                    hypothesis_type=hypothesis_type,
                    recurrence_status=recurrence_status,
                    cadence_state=str((snapshot.get("review_cadence") or {}).get("cadence_state") or ""),
                ),
                "title": f"Dream hypothesis: {title_suffix}",
                "summary": hypothesis_note,
                "rationale": str(item.get("summary") or "")
                or "A recurring bounded thread now looks strong enough to surface as a small private hypothesis.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(
                    str(item.get("confidence") or "low"),
                    str((snapshot.get("review_outcome") or {}).get("confidence") or ""),
                    str((snapshot.get("witness") or {}).get("confidence") or ""),
                ),
                "evidence_summary": _merge_fragments(
                    *[str(source.get("evidence_summary") or "") for source in source_items if source]
                ),
                "support_summary": _merge_fragments(
                    *[str(source.get("support_summary") or "") for source in source_items if source],
                    hypothesis_anchor,
                ),
                "support_count": max([int(source.get("support_count") or 1) for source in source_items if source], default=1),
                "session_count": max([int(source.get("session_count") or 1) for source in source_items if source], default=1),
                "status_reason": _build_status_reason(hypothesis_type=hypothesis_type),
                "hypothesis_type": hypothesis_type,
                "hypothesis_note": hypothesis_note,
                "hypothesis_anchor": hypothesis_anchor,
            }
        )

    return candidates[:4]


def _persist_dream_hypothesis_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_dream_hypothesis_signal(
            signal_id=f"dream-hypothesis-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "emerging-hypothesis"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("hypothesis_note") or signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "runtime-derived-support"),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=str(signal.get("support_summary") or ""),
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(signal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        superseded_count = supersede_runtime_dream_hypothesis_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded dream hypothesis for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "dream_hypothesis_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "dream_hypothesis_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "dream_hypothesis_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


def _build_dream_snapshots() -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=18):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["focus"] = focus

    for item in build_runtime_witness_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"fresh", "carried"}:
            continue
        domain_key = _witness_domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["witness"] = item

    for item in build_runtime_self_review_outcome_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        domain_key = _review_domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["review_outcome"] = item

    for item in build_runtime_self_review_cadence_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _review_cadence_domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["review_cadence"] = item

    return snapshots


def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["domain"] = _signal_domain_key(str(item.get("canonical_key") or ""))
    enriched["hypothesis_type"] = str(signal.get("hypothesis_type") or item.get("signal_type") or "")
    enriched["hypothesis_note"] = str(signal.get("hypothesis_note") or item.get("summary") or "")
    enriched["hypothesis_anchor"] = str(signal.get("hypothesis_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object], *, snapshots: dict[str, dict[str, object]]) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _signal_domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key) or {}
    enriched["domain"] = domain_key
    enriched["hypothesis_type"] = str(item.get("signal_type") or "")
    enriched["hypothesis_note"] = str(item.get("summary") or "")
    enriched["hypothesis_anchor"] = _build_hypothesis_anchor(snapshot=snapshot)
    return enriched


def _build_hypothesis_type(*, item: dict[str, object], snapshot: dict[str, object]) -> str:
    recurrence_type = str(item.get("signal_type") or "")
    outcome_type = str((snapshot.get("review_outcome") or {}).get("outcome_type") or "")
    has_witness = bool(snapshot.get("witness"))
    has_focus = bool(snapshot.get("focus"))

    if recurrence_type == "recurring-tension" and outcome_type == "challenge-further":
        return "tension-hypothesis"
    if recurrence_type == "recurring-direction" and has_witness and outcome_type in {"carry-forward", "nearing-closure", "watch-closely"}:
        return "carried-hypothesis"
    if has_focus and (outcome_type in {"watch-closely", "carry-forward", "challenge-further"} or has_witness):
        return "emerging-hypothesis"
    return ""


def _build_signal_status(*, hypothesis_type: str, recurrence_status: str, cadence_state: str) -> str:
    if hypothesis_type == "carried-hypothesis":
        return "integrating"
    if cadence_state == "recently-reviewed" or recurrence_status == "softening":
        return "fading"
    return "active"


def _build_hypothesis_note(*, hypothesis_type: str, recurrence_type: str, domain_key: str) -> str:
    title = _domain_title(domain_key).lower()
    if hypothesis_type == "tension-hypothesis":
        return build_bounded_hypothesis_text(
            f"{title} still wants deeper challenge rather than quick settling"
        )
    if hypothesis_type == "carried-hypothesis":
        return build_bounded_hypothesis_text(
            f"{title} may become a carried development line rather than a passing thread"
        )
    if recurrence_type == "recurring-direction":
        return build_bounded_hypothesis_text(
            f"{title} keeps wanting gentle continued development"
        )
    return build_bounded_hypothesis_text(
        f"{title} keeps returning as a bounded development thread"
    )


def _build_hypothesis_anchor(*, snapshot: dict[str, object]) -> str:
    parts: list[str] = []
    witness_type = str((snapshot.get("witness") or {}).get("signal_type") or "")
    outcome_type = str((snapshot.get("review_outcome") or {}).get("outcome_type") or "")
    cadence_state = str((snapshot.get("review_cadence") or {}).get("cadence_state") or "")
    if witness_type:
        parts.append(witness_type)
    if outcome_type:
        parts.append(outcome_type)
    if cadence_state:
        parts.append(cadence_state)
    if snapshot.get("focus"):
        parts.append("active focus")
    return " · ".join(parts[:3])


def _build_status_reason(*, hypothesis_type: str) -> str:
    if hypothesis_type == "tension-hypothesis":
        return "Recurring tension and review pressure still align around the same bounded domain."
    if hypothesis_type == "carried-hypothesis":
        return "Recurring direction now reads less like friction and more like a carried private line."
    return "Recurring bounded evidence is now enough to surface a small private hypothesis."


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


def _recurrence_domain_key(canonical_key: str) -> str:
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


def _signal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


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
