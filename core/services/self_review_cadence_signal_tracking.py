from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.self_review_outcome_tracking import (
    build_runtime_self_review_outcome_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_self_review_cadence_signals,
    supersede_runtime_self_review_cadence_signals_for_domain,
    update_runtime_self_review_cadence_signal_status,
    upsert_runtime_self_review_cadence_signal,
)

_STALE_AFTER_DAYS = 14
_RECENTLY_REVIEWED_DAYS = 2
_DUE_AFTER_DAYS = 5


def track_runtime_self_review_cadence_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    # Deduplicate candidates per domain_key BEFORE we persist. Without
    # this, multiple candidates mapping to the same domain end up
    # superseding each other inside a single 100ms window (created →
    # superseded → created → superseded …). Keep the first occurrence
    # for each (canonical_key, domain_key) tuple — downstream cadence
    # state is already computed per candidate, so taking the first one
    # is stable.
    raw_candidates = _extract_self_review_cadence_candidates()
    seen_keys: set[tuple[str, str]] = set()
    deduped: list[dict[str, object]] = []
    for candidate in raw_candidates:
        key = (
            str(candidate.get("canonical_key") or ""),
            str(candidate.get("domain_key") or ""),
        )
        if key in seen_keys or not key[1]:
            continue
        seen_keys.add(key)
        deduped.append(candidate)

    items = _persist_self_review_cadence_signals(
        signals=deduped,
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded self-review cadence signals."
            if items
            else "No bounded self-review cadence signal warranted tracking."
        ),
    }


def refresh_runtime_self_review_cadence_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_self_review_cadence_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_self_review_cadence_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded self-review cadence inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "self_review_cadence_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_self_review_cadence_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_self_review_cadence_signal_statuses()
    items = list_runtime_self_review_cadence_signals(limit=max(limit, 1))
    snapshots = _build_cadence_snapshots()
    enriched_items = [_with_surface_view(item, snapshots=snapshots) for item in items]
    active = [item for item in enriched_items if str(item.get("status") or "") == "active"]
    softening = [item for item in enriched_items if str(item.get("status") or "") == "softening"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
    ordered = [*active, *softening, *stale, *superseded]
    latest = next(iter(active or softening or stale or superseded), None)
    return {
        "active": bool(active or softening),
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active self-review cadence signal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_cadence_state": str((latest or {}).get("cadence_state") or "none"),
        },
    }


def _extract_self_review_cadence_candidates() -> list[dict[str, object]]:
    now = datetime.now(UTC)
    candidates: list[dict[str, object]] = []

    for item in build_runtime_self_review_outcome_surface(limit=12).get("items", []):
        outcome_status = str(item.get("status") or "")
        if outcome_status not in {"fresh", "active", "fading", "stale"}:
            continue
        domain_key = _self_review_cadence_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        reviewed_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if reviewed_at is None:
            continue
        review_age = now - reviewed_at
        cadence_state = _build_cadence_state(review_age=review_age, outcome_status=outcome_status)
        signal_status = "softening" if cadence_state == "recently-reviewed" else "active"
        title_suffix = _domain_title(domain_key)
        due_hint = _build_due_hint(cadence_state=cadence_state)
        candidates.append(
            {
                "signal_type": "review-cadence",
                "canonical_key": f"self-review-cadence:{str(item.get('review_type') or 'self-review')}:{domain_key}",
                "domain_key": domain_key,
                "status": signal_status,
                "title": f"Self-review cadence: {title_suffix}",
                "summary": _build_cadence_reason(
                    cadence_state=cadence_state,
                    review_type=str(item.get("review_type") or "self-review"),
                ),
                "rationale": str(item.get("short_outcome") or item.get("summary") or "")
                or "A bounded self-review outcome now carries a small cadence signal.",
                "source_kind": "runtime-derived-support",
                "confidence": str(item.get("confidence") or "low"),
                "evidence_summary": str(item.get("evidence_summary") or ""),
                "support_summary": _merge_fragments(
                    str(item.get("support_summary") or ""),
                    str(item.get("review_focus") or ""),
                    due_hint,
                ),
                "support_count": int(item.get("support_count") or 1),
                "session_count": int(item.get("session_count") or 1),
                "status_reason": _build_status_reason(cadence_state=cadence_state),
                "cadence_state": cadence_state,
                "cadence_reason": _build_cadence_reason(
                    cadence_state=cadence_state,
                    review_type=str(item.get("review_type") or "self-review"),
                ),
                "last_reviewed_at": reviewed_at.isoformat(),
                "due_hint": due_hint,
            }
        )

    return candidates[:4]


def _persist_self_review_cadence_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    # Defensive: track domains we've already processed in this batch
    # so we don't supersede sibling rows we just created.
    processed_domains: set[str] = set()
    for signal in signals:
        signal_domain = str(signal.get("domain_key") or "")
        if signal_domain in processed_domains:
            continue
        processed_domains.add(signal_domain)
        persisted_item = upsert_runtime_self_review_cadence_signal(
            signal_id=f"self-review-cadence-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "review-cadence"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
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
        superseded_count = supersede_runtime_self_review_cadence_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded self-review cadence signal for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "self_review_cadence_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "self_review_cadence_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "self_review_cadence_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


def _build_cadence_snapshots() -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}
    for item in build_runtime_self_review_outcome_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"fresh", "active", "fading", "stale"}:
            continue
        domain_key = _self_review_cadence_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        snapshots[domain_key] = {
            "outcome": item,
            "reviewed_at": str(item.get("updated_at") or item.get("created_at") or ""),
            "cadence_state": _build_cadence_state(
                review_age=datetime.now(UTC) - _parse_dt(str(item.get("updated_at") or item.get("created_at") or "")) if _parse_dt(str(item.get("updated_at") or item.get("created_at") or "")) else timedelta(days=_DUE_AFTER_DAYS),
                outcome_status=status,
            ),
        }
    return snapshots


def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["domain"] = _self_review_cadence_domain_key(str(item.get("canonical_key") or ""))
    enriched["cadence_state"] = str(signal.get("cadence_state") or "due")
    enriched["cadence_reason"] = str(signal.get("cadence_reason") or item.get("summary") or "")
    enriched["last_reviewed_at"] = str(signal.get("last_reviewed_at") or "")
    enriched["due_hint"] = str(signal.get("due_hint") or "")
    return enriched


def _with_surface_view(item: dict[str, object], *, snapshots: dict[str, dict[str, object]]) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _self_review_cadence_domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key) or {}
    cadence_state = str(snapshot.get("cadence_state") or _cadence_state_from_summary(str(item.get("summary") or "")))
    enriched["domain"] = domain_key
    enriched["cadence_state"] = cadence_state
    enriched["cadence_reason"] = str(item.get("summary") or "")
    enriched["last_reviewed_at"] = str(snapshot.get("reviewed_at") or "")
    enriched["due_hint"] = _build_due_hint(cadence_state=cadence_state)
    return enriched


def _build_cadence_state(*, review_age: timedelta, outcome_status: str) -> str:
    if outcome_status == "stale" or review_age >= timedelta(days=_DUE_AFTER_DAYS + 3):
        return "lingering"
    if review_age <= timedelta(days=_RECENTLY_REVIEWED_DAYS):
        return "recently-reviewed"
    return "due"


def _build_cadence_reason(*, cadence_state: str, review_type: str) -> str:
    if cadence_state == "recently-reviewed":
        return f"This {review_type.replace('-', ' ')} thread was reviewed recently and can stay quiet for now."
    if cadence_state == "lingering":
        return f"This {review_type.replace('-', ' ')} thread has been left too long after review and now looks lingering."
    return f"This {review_type.replace('-', ' ')} thread now looks due for another bounded review pass."


def _build_status_reason(*, cadence_state: str) -> str:
    if cadence_state == "recently-reviewed":
        return "recently-reviewed"
    if cadence_state == "lingering":
        return "lingering"
    return "due"


def _build_due_hint(*, cadence_state: str) -> str:
    if cadence_state == "recently-reviewed":
        return "No new review window is needed yet."
    if cadence_state == "lingering":
        return "The review window has hung open long enough that it should be revisited soon."
    return "A small follow-up review window is now open."


def _cadence_state_from_summary(summary: str) -> str:
    text = str(summary or "").lower()
    if "reviewed recently" in text:
        return "recently-reviewed"
    if "lingering" in text:
        return "lingering"
    if "due" in text:
        return "due"
    return "due"


def _self_review_cadence_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Self-review"


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
