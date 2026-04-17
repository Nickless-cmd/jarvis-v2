from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_executive_contradiction_signals,
    list_runtime_internal_opposition_signals,
    list_runtime_open_loop_signals,
    list_runtime_private_initiative_tension_signals,
    list_runtime_private_state_snapshots,
    list_runtime_self_review_outcomes,
    supersede_runtime_executive_contradiction_signals_for_domain,
    update_runtime_executive_contradiction_signal_status,
    upsert_runtime_executive_contradiction_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_executive_contradiction_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_executive_contradiction_signals(
        signals=_extract_executive_contradiction_candidates(run_id=run_id),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded executive contradiction signals."
            if items
            else "No bounded executive contradiction signal warranted tracking."
        ),
    }


def refresh_runtime_executive_contradiction_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_executive_contradiction_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_executive_contradiction_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded executive-contradiction inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "executive_contradiction_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_executive_contradiction_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_executive_contradiction_signal_statuses()
    items = list_runtime_executive_contradiction_signals(limit=max(limit, 1))
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
        "execution_veto_state": "not-authorized",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active executive contradiction support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_control_type": str((latest or {}).get("control_type") or "none"),
            "current_pressure": str((latest or {}).get("control_pressure") or "low"),
            "current_confidence": str((latest or {}).get("control_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "execution_veto_state": "not-authorized",
        },
    }


def _extract_executive_contradiction_candidates(*, run_id: str) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for item in list_runtime_internal_opposition_signals(limit=18):
        status = str(item.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_opposition"] = item
        else:
            bucket["softening_opposition"] = item

    for item in list_runtime_open_loop_signals(limit=18):
        status = str(item.get("status") or "")
        if status not in {"open", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "open":
            bucket["open_loop"] = item
        else:
            bucket["softening_loop"] = item

    for item in list_runtime_self_review_outcomes(limit=18):
        status = str(item.get("status") or "")
        if status not in {"fresh", "active", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status in {"fresh", "active"}:
            bucket["active_review_outcome"] = item
        else:
            bucket["fading_review_outcome"] = item

    for item in list_runtime_private_state_snapshots(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        snapshots.setdefault(domain_key, {})["private_state"] = item

    for item in list_runtime_private_initiative_tension_signals(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        snapshots.setdefault(domain_key, {})["initiative_tension"] = item

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        active_opposition = snapshot.get("active_opposition")
        softening_opposition = snapshot.get("softening_opposition")
        if active_opposition is None and softening_opposition is None:
            continue

        open_loop = snapshot.get("open_loop")
        softening_loop = snapshot.get("softening_loop")
        active_review_outcome = snapshot.get("active_review_outcome")
        fading_review_outcome = snapshot.get("fading_review_outcome")
        private_state = snapshot.get("private_state")
        initiative_tension = snapshot.get("initiative_tension")

        if not any((open_loop, softening_loop, active_review_outcome, fading_review_outcome)):
            continue

        title_suffix = _title_suffix(domain_key)
        state_pressure = _value(private_state.get("state_pressure") if private_state else "", default="low")
        tension_type = _value(initiative_tension.get("tension_type") if initiative_tension else "", default="none")
        control_target = _target_text(
            active_review_outcome,
            open_loop,
            active_opposition or softening_opposition,
            fallback=title_suffix,
        )

        has_sharp_pressure = active_opposition is not None and (open_loop is not None or active_review_outcome is not None)
        has_softening_pressure = softening_opposition is not None and (softening_loop is not None or fading_review_outcome is not None)
        if has_sharp_pressure:
            control_type = "contradiction-pressure"
            status = "active"
            control_pressure = _pressure(
                opposition_status="active",
                has_open_loop=bool(open_loop),
                has_active_review=bool(active_review_outcome),
                state_pressure=state_pressure,
                tension_type=tension_type,
            )
            summary = f"Bounded executive contradiction pressure is asking Jarvis not to carry {control_target.lower()} forward blindly."
            rationale = "Active internal opposition plus unresolved loop or live self-review outcome produces bounded contradiction awareness, without granting direct veto or planner authority."
            status_reason = "Bounded executive contradiction remains runtime support only and is not yet allowed to directly veto execution."
        elif has_softening_pressure:
            control_type = "veto-watch"
            status = "softening"
            control_pressure = "medium" if state_pressure == "medium" or tension_type == "unresolved" else "low"
            summary = f"Bounded executive contradiction still watches {control_target.lower()}, but the sharper veto pressure is easing."
            rationale = "Softening opposition plus easing loop/review pressure still supports bounded contradiction awareness, but not a sharp contradiction push."
            status_reason = "Bounded executive contradiction is softening and remains runtime support only, with no direct execution veto authority."
        else:
            continue

        control_confidence = _stronger_confidence(
            str((active_opposition or softening_opposition or {}).get("confidence") or "low"),
            str((open_loop or softening_loop or {}).get("closure_confidence") or ""),
            str((active_review_outcome or fading_review_outcome or {}).get("confidence") or ""),
            str(private_state.get("state_confidence") or private_state.get("confidence") or "low")
            if private_state
            else "low",
            str((initiative_tension or {}).get("tension_confidence") or ""),
        )
        source_anchor = _merge_fragments(
            _anchor(active_opposition or softening_opposition),
            _anchor(open_loop or softening_loop),
            _anchor(active_review_outcome or fading_review_outcome),
            _anchor(private_state),
            _anchor(initiative_tension),
        )
        evidence_summary = _merge_fragments(
            str((active_opposition or softening_opposition or {}).get("evidence_summary") or ""),
            str((open_loop or softening_loop or {}).get("evidence_summary") or ""),
            str((active_review_outcome or fading_review_outcome or {}).get("evidence_summary") or ""),
            str((private_state or {}).get("evidence_summary") or ""),
            str((initiative_tension or {}).get("evidence_summary") or ""),
        )
        support_summary = _merge_fragments(
            "Derived only from internal opposition, open-loop, self-review, and optional bounded inner-state support.",
            source_anchor,
        )
        candidates.append(
            {
                "signal_type": "executive-contradiction",
                "canonical_key": f"executive-contradiction:{control_type}:{domain_key}",
                "domain_key": domain_key,
                "status": status,
                "title": f"Executive contradiction support: {title_suffix}",
                "summary": summary,
                "rationale": rationale,
                "source_kind": "runtime-derived-support",
                "confidence": control_confidence,
                "evidence_summary": evidence_summary,
                "support_summary": support_summary,
                "support_count": 1,
                "session_count": 1,
                "status_reason": status_reason,
                "control_type": control_type,
                "control_target": control_target,
                "control_pressure": control_pressure,
                "control_summary": _merge_fragments(
                    str((active_opposition or softening_opposition or {}).get("summary") or ""),
                    str((open_loop or softening_loop or {}).get("summary") or ""),
                    str((active_review_outcome or fading_review_outcome or {}).get("summary") or ""),
                )[:220],
                "control_confidence": control_confidence,
                "source_anchor": source_anchor,
                "grounding_mode": _grounding_mode(
                    has_private_state=private_state is not None,
                    has_tension=initiative_tension is not None,
                ),
                "execution_veto_state": "not-authorized",
            }
        )
    return candidates[:4]


def _persist_executive_contradiction_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_executive_contradiction_signal(
            signal_id=f"executive-contradiction-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "executive-contradiction"),
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
        superseded_count = supersede_runtime_executive_contradiction_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded executive contradiction signal for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "executive_contradiction_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "executive_contradiction_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "executive_contradiction_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


def _with_runtime_view(persisted: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    item = dict(persisted)
    item.update(
        {
            "control_type": signal.get("control_type"),
            "control_target": signal.get("control_target"),
            "control_pressure": signal.get("control_pressure"),
            "control_summary": signal.get("control_summary"),
            "control_confidence": signal.get("control_confidence"),
            "source_anchor": signal.get("source_anchor"),
            "grounding_mode": signal.get("grounding_mode"),
            "execution_veto_state": signal.get("execution_veto_state"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        }
    )
    return item


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    control_type = _value(
        item.get("control_type"),
        _canonical_segment(str(item.get("canonical_key") or ""), index=1),
        default="contradiction-pressure",
    )
    control_pressure = _value(
        item.get("control_pressure"),
        default=_surface_pressure_default(
            control_type=control_type,
            status=str(item.get("status") or ""),
        ),
    )
    enriched = dict(item)
    enriched.update(
        {
            "control_type": control_type,
            "control_target": _value(item.get("control_target"), item.get("title"), default="visible direction"),
            "control_pressure": control_pressure,
            "control_summary": _value(item.get("control_summary"), item.get("summary"), default="No bounded executive contradiction support."),
            "control_confidence": _value(item.get("control_confidence"), item.get("confidence"), default="low"),
            "source_anchor": _anchor(item),
            "grounding_mode": _value(item.get("grounding_mode"), default="opposition+open-loop+self-review-outcome"),
            "execution_veto_state": _value(item.get("execution_veto_state"), default="not-authorized"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "source": "/mc/runtime.executive_contradiction_signal",
            "createdAt": str(item.get("created_at") or ""),
        }
    )
    return enriched


def _surface_pressure_default(*, control_type: str, status: str) -> str:
    normalized_type = str(control_type or "").strip()
    normalized_status = str(status or "").strip()
    if normalized_type == "contradiction-pressure":
        return "high" if normalized_status == "active" else "medium"
    if normalized_type == "veto-watch":
        return "medium" if normalized_status == "softening" else "low"
    return "low"


def _pressure(
    *,
    opposition_status: str,
    has_open_loop: bool,
    has_active_review: bool,
    state_pressure: str,
    tension_type: str,
) -> str:
    if opposition_status == "active" and has_open_loop and has_active_review:
        return "high"
    if state_pressure == "medium" or tension_type == "unresolved":
        return "high"
    return "medium"


def _grounding_mode(*, has_private_state: bool, has_tension: bool) -> str:
    if has_private_state and has_tension:
        return "opposition+open-loop+self-review-outcome+private-state+initiative-tension"
    if has_private_state:
        return "opposition+open-loop+self-review-outcome+private-state"
    if has_tension:
        return "opposition+open-loop+self-review-outcome+initiative-tension"
    return "opposition+open-loop+self-review-outcome"


def _target_text(*items: dict[str, object] | None, fallback: str) -> str:
    for item in items:
        if not item:
            continue
        for key in ("review_focus", "control_target", "title", "summary"):
            value = str(item.get(key) or "").strip()
            if value:
                return value[:96]
    return fallback[:96]


def _title_suffix(domain_key: str) -> str:
    return domain_key.replace("-", " ") or "visible thread"


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


def _stronger_confidence(*values: str) -> str:
    winner = "low"
    best = -1
    for value in values:
        normalized = str(value or "").strip().lower()
        rank = _CONFIDENCE_RANKS.get(normalized, -1)
        if rank > best:
            best = rank
            winner = normalized or "low"
    return winner


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
