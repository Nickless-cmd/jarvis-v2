from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_executive_contradiction_signals,
    list_runtime_inner_visible_support_signals,
    list_runtime_private_initiative_tension_signals,
    list_runtime_private_state_snapshots,
    list_runtime_private_temporal_curiosity_states,
    list_runtime_regulation_homeostasis_signals,
    supersede_runtime_regulation_homeostasis_signals_for_focus,
    update_runtime_regulation_homeostasis_signal_status,
    upsert_runtime_regulation_homeostasis_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_regulation_homeostasis_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    candidate = _extract_candidate_for_run(run_id=run_id)
    if candidate is None:
        return {
            "created": 0,
            "updated": 0,
            "items": [],
            "summary": "No bounded regulation/homeostasis grounding was available for this visible turn.",
        }

    persisted = _persist_regulation_homeostasis_signals(
        signals=[candidate],
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in persisted if item.get("was_created")]),
        "updated": len([item for item in persisted if item.get("was_updated")]),
        "items": persisted,
        "summary": (
            "Tracked 1 bounded regulation/homeostasis runtime signal."
            if persisted
            else "No bounded regulation/homeostasis runtime signal warranted tracking."
        ),
    }


def refresh_runtime_regulation_homeostasis_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_regulation_homeostasis_signals(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_regulation_homeostasis_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded regulation/homeostasis inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "regulation_homeostasis_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_regulation_homeostasis_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_regulation_homeostasis_signal_statuses()
    items = list_runtime_regulation_homeostasis_signals(limit=max(limit, 1))
    enriched_items = [_with_surface_view(item) for item in items]
    active = [item for item in enriched_items if str(item.get("status") or "") == "active"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
    ordered = [*active, *stale, *superseded]
    latest = next(iter(active or stale or superseded), None)
    return {
        "active": bool(active),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_mood_state": "not-canonical-mood-or-personality",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active regulation/homeostasis support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("regulation_state") or "none"),
            "current_pressure": str((latest or {}).get("regulation_pressure") or "low"),
            "current_watchfulness": str((latest or {}).get("regulation_watchfulness") or "low"),
            "current_pacing": str((latest or {}).get("regulation_pacing") or "steady"),
            "current_confidence": str((latest or {}).get("regulation_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_mood_state": "not-canonical-mood-or-personality",
        },
    }


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    private_state = _latest_private_state_snapshot(run_id=run_id)
    if private_state is None:
        return None

    focus = _focus_key(private_state)
    initiative_tension = _latest_initiative_tension_signal(run_id=run_id, focus_key=focus)
    temporal_curiosity = _latest_temporal_curiosity_state(run_id=run_id, focus_key=focus)
    executive_contradiction = _latest_executive_contradiction_signal(run_id=run_id, focus_key=focus)
    inner_visible_support = _latest_inner_visible_support_signal(run_id=run_id, focus_key=focus)

    state_tone = _value(private_state.get("state_tone"), default="steady-support")
    state_pressure = _value(private_state.get("state_pressure"), default="low")
    tension_type = _value(
        initiative_tension.get("tension_type") if initiative_tension else "",
        _canonical_segment(str((initiative_tension or {}).get("canonical_key") or ""), index=1),
        default="none",
    )
    curiosity_pull = _value(
        temporal_curiosity.get("curiosity_pull") if temporal_curiosity else "",
        default="low",
    )
    contradiction_pressure = _value(
        executive_contradiction.get("control_pressure") if executive_contradiction else "",
        default="low",
    )
    contradiction_status = _value(
        executive_contradiction.get("status") if executive_contradiction else "",
        default="none",
    )
    visible_watchfulness = _value(
        inner_visible_support.get("support_watchfulness") if inner_visible_support else "",
        default="low",
    )

    regulation_pressure = _derive_regulation_pressure(
        state_pressure=state_pressure,
        tension_type=tension_type,
        contradiction_pressure=contradiction_pressure,
    )
    regulation_watchfulness = _derive_regulation_watchfulness(
        contradiction_status=contradiction_status,
        contradiction_pressure=contradiction_pressure,
        visible_watchfulness=visible_watchfulness,
    )
    regulation_pacing = _derive_regulation_pacing(
        pressure=regulation_pressure,
        watchfulness=regulation_watchfulness,
        curiosity_pull=curiosity_pull,
    )
    regulation_state = _derive_regulation_state(
        state_tone=state_tone,
        pressure=regulation_pressure,
        watchfulness=regulation_watchfulness,
        pacing=regulation_pacing,
    )
    regulation_confidence = _stronger_confidence(
        str(private_state.get("state_confidence") or private_state.get("confidence") or "low"),
        str((initiative_tension or {}).get("tension_confidence") or (initiative_tension or {}).get("confidence") or "low"),
        str((temporal_curiosity or {}).get("curiosity_confidence") or (temporal_curiosity or {}).get("confidence") or "low"),
        str((executive_contradiction or {}).get("control_confidence") or (executive_contradiction or {}).get("confidence") or "low"),
        str((inner_visible_support or {}).get("support_confidence") or (inner_visible_support or {}).get("confidence") or "low"),
    )
    grounding_mode = _grounding_mode(
        has_tension=initiative_tension is not None,
        has_curiosity=temporal_curiosity is not None,
        has_executive_contradiction=executive_contradiction is not None,
        has_inner_visible_support=inner_visible_support is not None,
    )
    source_anchor = _merge_fragments(
        _support_anchor(private_state),
        _support_anchor(initiative_tension) if initiative_tension else "",
        _support_anchor(temporal_curiosity) if temporal_curiosity else "",
        _support_anchor(executive_contradiction) if executive_contradiction else "",
        _support_anchor(inner_visible_support) if inner_visible_support else "",
    )
    evidence_summary = _merge_fragments(
        str(private_state.get("evidence_summary") or ""),
        str((initiative_tension or {}).get("evidence_summary") or ""),
        str((temporal_curiosity or {}).get("evidence_summary") or ""),
        str((executive_contradiction or {}).get("evidence_summary") or ""),
        str((inner_visible_support or {}).get("evidence_summary") or ""),
    )

    return {
        "signal_type": "regulation-homeostasis",
        "canonical_key": f"regulation-homeostasis:{regulation_state}:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Regulation support: {focus.replace('-', ' ')}",
        "summary": (
            f"Bounded regulation/homeostasis runtime support is holding a small regulation state around {focus.replace('-', ' ')}."
        ),
        "rationale": (
            "A bounded regulation/homeostasis signal may be derived only from already-returned private-state runtime support, optional initiative-tension and temporal-curiosity sharpening, optional executive-contradiction watchfulness pressure, and optional inner-visible support sharpening, without becoming canonical mood, personality, workflow authority, or planner authority."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": regulation_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded private-state runtime support, optional initiative-tension and temporal-curiosity sharpening, and small executive-contradiction or inner-visible watchfulness sharpening.",
            f"grounding-mode={grounding_mode}",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "Bounded regulation/homeostasis remains subordinate to visible/runtime truth, is non-authoritative runtime support only, and is not canonical mood or personality."
        ),
        "regulation_state": regulation_state,
        "regulation_pressure": regulation_pressure,
        "regulation_watchfulness": regulation_watchfulness,
        "regulation_pacing": regulation_pacing,
        "regulation_summary": _bounded_regulation_summary(
            focus=focus,
            regulation_state=regulation_state,
            regulation_pressure=regulation_pressure,
            regulation_watchfulness=regulation_watchfulness,
            regulation_pacing=regulation_pacing,
        ),
        "regulation_confidence": regulation_confidence,
        "source_anchor": source_anchor,
        "state_snapshot_id": str(private_state.get("snapshot_id") or ""),
        "initiative_tension_signal_id": str((initiative_tension or {}).get("signal_id") or ""),
        "temporal_curiosity_state_id": str((temporal_curiosity or {}).get("state_id") or ""),
        "executive_contradiction_signal_id": str((executive_contradiction or {}).get("signal_id") or ""),
        "inner_visible_support_signal_id": str((inner_visible_support or {}).get("signal_id") or ""),
        "grounding_mode": grounding_mode,
    }


def _persist_regulation_homeostasis_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_regulation_homeostasis_signal(
            signal_id=f"regulation-homeostasis-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "regulation-homeostasis"),
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
        superseded_count = supersede_runtime_regulation_homeostasis_signals_for_focus(
            focus_key=str(signal.get("focus_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded regulation/homeostasis signal for the same visible-work focus.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "regulation_homeostasis_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "regulation_homeostasis_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "regulation_homeostasis_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


def _latest_private_state_snapshot(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_state_snapshots(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        return item
    return None


def _latest_initiative_tension_signal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_private_initiative_tension_signals(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_temporal_curiosity_state(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_private_temporal_curiosity_states(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_executive_contradiction_signal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_executive_contradiction_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_inner_visible_support_signal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_inner_visible_support_signals(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _derive_regulation_pressure(
    *,
    state_pressure: str,
    tension_type: str,
    contradiction_pressure: str,
) -> str:
    if state_pressure == "medium" or tension_type == "unresolved" or contradiction_pressure in {"medium", "high"}:
        return "medium"
    return "low"


def _derive_regulation_watchfulness(
    *,
    contradiction_status: str,
    contradiction_pressure: str,
    visible_watchfulness: str,
) -> str:
    if contradiction_status in {"active", "softening"} and contradiction_pressure in {"medium", "high"}:
        return "medium"
    if visible_watchfulness == "medium":
        return "medium"
    return "low"


def _derive_regulation_pacing(
    *,
    pressure: str,
    watchfulness: str,
    curiosity_pull: str,
) -> str:
    if watchfulness == "medium":
        return "slow-and-check"
    if pressure == "medium" and curiosity_pull == "low":
        return "settling-needed"
    if curiosity_pull == "medium":
        return "careful-forward"
    return "steady"


def _derive_regulation_state(
    *,
    state_tone: str,
    pressure: str,
    watchfulness: str,
    pacing: str,
) -> str:
    if watchfulness == "medium" and pressure == "medium":
        return "watchful-pressure"
    if pressure == "medium" or state_tone == "steady-pressure":
        return "steady-pressure"
    if pacing == "settling-needed":
        return "settling-support"
    return "steady-support"


def _bounded_regulation_summary(
    *,
    focus: str,
    regulation_state: str,
    regulation_pressure: str,
    regulation_watchfulness: str,
    regulation_pacing: str,
) -> str:
    label = focus.replace("-", " ")
    return (
        f"{label} is currently held in a bounded {regulation_state} regulation state, with {regulation_pressure} pressure, "
        f"{regulation_watchfulness} watchfulness, and {regulation_pacing} pacing."
    )


def _grounding_mode(
    *,
    has_tension: bool,
    has_curiosity: bool,
    has_executive_contradiction: bool,
    has_inner_visible_support: bool,
) -> str:
    parts = ["private-state"]
    if has_tension:
        parts.append("initiative-tension")
    if has_curiosity:
        parts.append("temporal-curiosity")
    if has_executive_contradiction:
        parts.append("executive-contradiction")
    if has_inner_visible_support:
        parts.append("inner-visible-sharpening")
    return "+".join(parts)


def _with_runtime_view(
    record: dict[str, object],
    signal: dict[str, object],
) -> dict[str, object]:
    enriched = dict(record)
    enriched.update(
        {
            "regulation_state": signal.get("regulation_state", "steady-support"),
            "regulation_pressure": signal.get("regulation_pressure", "low"),
            "regulation_watchfulness": signal.get("regulation_watchfulness", "low"),
            "regulation_pacing": signal.get("regulation_pacing", "steady"),
            "regulation_summary": signal.get("regulation_summary", ""),
            "regulation_confidence": signal.get("regulation_confidence", record.get("confidence", "low")),
            "source_anchor": signal.get("source_anchor", ""),
            "grounding_mode": signal.get("grounding_mode", "private-state"),
            "state_snapshot_id": signal.get("state_snapshot_id", ""),
            "initiative_tension_signal_id": signal.get("initiative_tension_signal_id", ""),
            "temporal_curiosity_state_id": signal.get("temporal_curiosity_state_id", ""),
            "executive_contradiction_signal_id": signal.get("executive_contradiction_signal_id", ""),
            "inner_visible_support_signal_id": signal.get("inner_visible_support_signal_id", ""),
        }
    )
    return _with_surface_view(enriched)


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched.setdefault("regulation_state", _canonical_segment(str(item.get("canonical_key") or ""), index=1) or "steady-support")
    enriched.setdefault("regulation_pressure", "low")
    enriched.setdefault("regulation_watchfulness", "low")
    enriched.setdefault("regulation_pacing", "steady")
    enriched.setdefault("regulation_summary", str(item.get("summary") or ""))
    enriched.setdefault("regulation_confidence", str(item.get("confidence") or "low"))
    enriched.setdefault(
        "source_anchor",
        _source_anchor_from_support_summary(str(item.get("support_summary") or "")),
    )
    enriched.setdefault(
        "grounding_mode",
        _grounding_mode_from_support_summary(str(item.get("support_summary") or "")) or "private-state",
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["canonical_mood_state"] = "not-canonical-mood-or-personality"
    return enriched


def _focus_key(item: dict[str, object] | None) -> str:
    return _canonical_segment(str((item or {}).get("canonical_key") or ""), index=-1) or "visible-work"


def _support_anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    title = str(item.get("title") or "").strip()
    canonical_key = str(item.get("canonical_key") or "").strip()
    if title and canonical_key:
        return f"{title} [{canonical_key}]"
    return title or canonical_key


def _canonical_segment(value: str, *, index: int) -> str:
    if not value:
        return ""
    parts = [part.strip() for part in value.split(":") if part.strip()]
    if not parts:
        return ""
    try:
        return parts[index]
    except IndexError:
        return ""


def _merge_fragments(*values: str) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return " | ".join(ordered)


def _grounding_mode_from_support_summary(value: str) -> str:
    for piece in str(value or "").split(" | "):
        normalized = piece.strip()
        if normalized.startswith("grounding-mode="):
            return normalized.split("=", 1)[1].strip()
    return ""


def _source_anchor_from_support_summary(value: str) -> str:
    anchors: list[str] = []
    for piece in str(value or "").split(" | "):
        normalized = piece.strip()
        if not normalized:
            continue
        if normalized.startswith("Derived only from "):
            continue
        if normalized.startswith("grounding-mode="):
            continue
        anchors.append(normalized)
    return " | ".join(anchors)


def _stronger_confidence(*values: str) -> str:
    best = "low"
    best_rank = _CONFIDENCE_RANKS[best]
    for raw_value in values:
        value = _value(raw_value, default="low")
        rank = _CONFIDENCE_RANKS.get(value, 0)
        if rank > best_rank:
            best = value
            best_rank = rank
    return best


def _value(*values: object, default: str) -> str:
    for raw_value in values:
        value = str(raw_value or "").strip().lower()
        if value:
            return value
    return default


def _parse_dt(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
