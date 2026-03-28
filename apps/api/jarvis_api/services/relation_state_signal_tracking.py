from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_executive_contradiction_signals,
    list_runtime_inner_visible_support_signals,
    list_runtime_private_state_snapshots,
    list_runtime_regulation_homeostasis_signals,
    list_runtime_relation_state_signals,
    list_runtime_user_understanding_signals,
    supersede_runtime_relation_state_signals_for_focus,
    update_runtime_relation_state_signal_status,
    upsert_runtime_relation_state_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_relation_state_signals_for_visible_turn(
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
            "summary": "No bounded relation-state grounding was available for this visible turn.",
        }

    persisted = _persist_relation_state_signals(
        signals=[candidate],
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in persisted if item.get("was_created")]),
        "updated": len([item for item in persisted if item.get("was_updated")]),
        "items": persisted,
        "summary": (
            "Tracked 1 bounded relation-state runtime signal."
            if persisted
            else "No bounded relation-state runtime signal warranted tracking."
        ),
    }


def refresh_runtime_relation_state_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_relation_state_signals(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_relation_state_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded relation-state inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "relation_state_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_relation_state_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_relation_state_signal_statuses()
    items = list_runtime_relation_state_signals(limit=max(limit, 1))
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
        "canonical_relation_state": "not-canonical-relationship-truth",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active relation-state support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("relation_state") or "none"),
            "current_alignment": str((latest or {}).get("relation_alignment") or "working-alignment"),
            "current_watchfulness": str((latest or {}).get("relation_watchfulness") or "low"),
            "current_pressure": str((latest or {}).get("relation_pressure") or "low"),
            "current_confidence": str((latest or {}).get("relation_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_relation_state": "not-canonical-relationship-truth",
        },
    }


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    user_understanding = _latest_user_understanding_signal(run_id=run_id)
    if user_understanding is None:
        return None

    private_state = _latest_private_state_snapshot(run_id=run_id)
    regulation = _latest_regulation_homeostasis_signal(run_id=run_id)
    if private_state is None and regulation is None:
        return None

    focus = _focus_key(private_state, regulation, user_understanding)
    executive_contradiction = _latest_executive_contradiction_signal(run_id=run_id, focus_key=focus)
    inner_visible_support = _latest_inner_visible_support_signal(run_id=run_id, focus_key=focus)

    user_dimension = _value(
        user_understanding.get("user_dimension"),
        _canonical_segment(str(user_understanding.get("canonical_key") or ""), index=-1),
        default="current-user",
    )
    user_confidence = _value(
        user_understanding.get("signal_confidence"),
        user_understanding.get("confidence"),
        default="low",
    )
    relation_alignment = _derive_relation_alignment(
        user_confidence=user_confidence,
        user_signal_type=_value(user_understanding.get("signal_type"), default="preference-signal"),
        regulation_state=_value((regulation or {}).get("regulation_state"), default="steady-support"),
        contradiction_status=_value((executive_contradiction or {}).get("status"), default="none"),
    )
    relation_watchfulness = _derive_relation_watchfulness(
        regulation_watchfulness=_value((regulation or {}).get("regulation_watchfulness"), default="low"),
        contradiction_pressure=_value((executive_contradiction or {}).get("control_pressure"), default="low"),
        visible_watchfulness=_value((inner_visible_support or {}).get("support_watchfulness"), default="low"),
    )
    relation_pressure = _derive_relation_pressure(
        regulation_pressure=_value((regulation or {}).get("regulation_pressure"), default="low"),
        contradiction_pressure=_value((executive_contradiction or {}).get("control_pressure"), default="low"),
    )
    relation_state = _derive_relation_state(
        alignment=relation_alignment,
        watchfulness=relation_watchfulness,
        pressure=relation_pressure,
    )
    relation_confidence = _stronger_confidence(
        str(user_understanding.get("signal_confidence") or user_understanding.get("confidence") or "low"),
        str((private_state or {}).get("state_confidence") or (private_state or {}).get("confidence") or "low"),
        str((regulation or {}).get("regulation_confidence") or (regulation or {}).get("confidence") or "low"),
        str((executive_contradiction or {}).get("control_confidence") or (executive_contradiction or {}).get("confidence") or "low"),
        str((inner_visible_support or {}).get("support_confidence") or (inner_visible_support or {}).get("confidence") or "low"),
    )
    grounding_mode = _grounding_mode(
        has_private_state=private_state is not None,
        has_regulation=regulation is not None,
        has_executive_contradiction=executive_contradiction is not None,
        has_inner_visible_support=inner_visible_support is not None,
    )
    source_anchor = _merge_fragments(
        _support_anchor(user_understanding),
        _support_anchor(private_state) if private_state else "",
        _support_anchor(regulation) if regulation else "",
        _support_anchor(executive_contradiction) if executive_contradiction else "",
        _support_anchor(inner_visible_support) if inner_visible_support else "",
    )
    evidence_summary = _merge_fragments(
        str(user_understanding.get("evidence_summary") or ""),
        str((private_state or {}).get("evidence_summary") or ""),
        str((regulation or {}).get("evidence_summary") or ""),
        str((executive_contradiction or {}).get("evidence_summary") or ""),
        str((inner_visible_support or {}).get("evidence_summary") or ""),
    )

    return {
        "signal_type": "relation-state",
        "canonical_key": f"relation-state:{relation_state}:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Relation state support: {focus.replace('-', ' ')}",
        "summary": (
            f"Bounded relation-state runtime support is holding a small working relationship state around {focus.replace('-', ' ')}."
        ),
        "rationale": (
            "A bounded relation-state signal may be derived only from already-returned user-understanding runtime support plus bounded regulation, private-state, executive-contradiction, and inner-visible support, without becoming canonical relationship truth, hidden emotional authority, workflow authority, or planner authority."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": relation_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded user-understanding runtime support plus bounded regulation, private-state, executive-contradiction, and optional inner-visible sharpening.",
            f"grounding-mode={grounding_mode}",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "Bounded relation-state remains subordinate to visible/runtime truth, is non-authoritative runtime support only, and is not canonical relationship truth."
        ),
        "relation_state": relation_state,
        "relation_alignment": relation_alignment,
        "relation_watchfulness": relation_watchfulness,
        "relation_pressure": relation_pressure,
        "relation_summary": _relation_summary(
            focus=focus,
            relation_state=relation_state,
            relation_alignment=relation_alignment,
            relation_watchfulness=relation_watchfulness,
            relation_pressure=relation_pressure,
        ),
        "relation_confidence": relation_confidence,
        "source_anchor": source_anchor,
        "user_understanding_signal_id": str(user_understanding.get("signal_id") or ""),
        "state_snapshot_id": str((private_state or {}).get("snapshot_id") or ""),
        "regulation_signal_id": str((regulation or {}).get("signal_id") or ""),
        "executive_contradiction_signal_id": str((executive_contradiction or {}).get("signal_id") or ""),
        "inner_visible_support_signal_id": str((inner_visible_support or {}).get("signal_id") or ""),
        "grounding_mode": grounding_mode,
        "relation_dimension": user_dimension,
    }


def _persist_relation_state_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_relation_state_signal(
            signal_id=f"relation-state-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "relation-state"),
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
        superseded_count = supersede_runtime_relation_state_signals_for_focus(
            focus_key=str(signal.get("focus_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded relation-state signal for the same visible-work focus.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "relation_state_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "relation_state_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "relation_state_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


def _latest_user_understanding_signal(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_user_understanding_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        return item
    return None


def _latest_private_state_snapshot(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_state_snapshots(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        return item
    return None


def _latest_regulation_homeostasis_signal(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_regulation_homeostasis_signals(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
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


def _derive_relation_alignment(
    *,
    user_confidence: str,
    user_signal_type: str,
    regulation_state: str,
    contradiction_status: str,
) -> str:
    if user_confidence == "high" and contradiction_status == "none":
        return "aligned"
    if user_signal_type in {"workstyle-signal", "preference-signal"} and regulation_state in {"steady-support", "settling-support"}:
        return "working-alignment"
    return "cautious-alignment"


def _derive_relation_watchfulness(
    *,
    regulation_watchfulness: str,
    contradiction_pressure: str,
    visible_watchfulness: str,
) -> str:
    if contradiction_pressure in {"medium", "high"}:
        return "medium"
    if regulation_watchfulness == "medium" or visible_watchfulness == "medium":
        return "medium"
    return "low"


def _derive_relation_pressure(
    *,
    regulation_pressure: str,
    contradiction_pressure: str,
) -> str:
    if regulation_pressure == "medium" or contradiction_pressure in {"medium", "high"}:
        return "medium"
    return "low"


def _derive_relation_state(
    *,
    alignment: str,
    watchfulness: str,
    pressure: str,
) -> str:
    if alignment == "aligned" and watchfulness == "low" and pressure == "low":
        return "trustful-flow"
    if watchfulness == "medium" and pressure == "medium":
        return "cautious-distance"
    if watchfulness == "medium":
        return "careful-collaboration"
    return "working-alignment"


def _relation_summary(
    *,
    focus: str,
    relation_state: str,
    relation_alignment: str,
    relation_watchfulness: str,
    relation_pressure: str,
) -> str:
    label = focus.replace("-", " ")
    return (
        f"{label} is currently held in a bounded {relation_state} relation state, with {relation_alignment} alignment, "
        f"{relation_watchfulness} watchfulness, and {relation_pressure} pressure."
    )


def _grounding_mode(
    *,
    has_private_state: bool,
    has_regulation: bool,
    has_executive_contradiction: bool,
    has_inner_visible_support: bool,
) -> str:
    parts = ["user-understanding"]
    if has_private_state:
        parts.append("private-state")
    if has_regulation:
        parts.append("regulation")
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
            "relation_state": signal.get("relation_state", "working-alignment"),
            "relation_alignment": signal.get("relation_alignment", "working-alignment"),
            "relation_watchfulness": signal.get("relation_watchfulness", "low"),
            "relation_pressure": signal.get("relation_pressure", "low"),
            "relation_summary": signal.get("relation_summary", ""),
            "relation_confidence": signal.get("relation_confidence", record.get("confidence", "low")),
            "source_anchor": signal.get("source_anchor", ""),
            "grounding_mode": signal.get("grounding_mode", "user-understanding"),
            "relation_dimension": signal.get("relation_dimension", "current-user"),
            "user_understanding_signal_id": signal.get("user_understanding_signal_id", ""),
            "state_snapshot_id": signal.get("state_snapshot_id", ""),
            "regulation_signal_id": signal.get("regulation_signal_id", ""),
            "executive_contradiction_signal_id": signal.get("executive_contradiction_signal_id", ""),
            "inner_visible_support_signal_id": signal.get("inner_visible_support_signal_id", ""),
        }
    )
    return _with_surface_view(enriched)


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched.setdefault("relation_state", _canonical_segment(str(item.get("canonical_key") or ""), index=1) or "working-alignment")
    enriched.setdefault("relation_alignment", "working-alignment")
    enriched.setdefault("relation_watchfulness", "low")
    enriched.setdefault("relation_pressure", "low")
    enriched.setdefault("relation_summary", str(item.get("summary") or ""))
    enriched.setdefault("relation_confidence", str(item.get("confidence") or "low"))
    enriched.setdefault("relation_dimension", "current-user")
    enriched.setdefault(
        "source_anchor",
        _source_anchor_from_support_summary(str(item.get("support_summary") or "")),
    )
    enriched.setdefault(
        "grounding_mode",
        _grounding_mode_from_support_summary(str(item.get("support_summary") or "")) or "user-understanding",
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["canonical_relation_state"] = "not-canonical-relationship-truth"
    return enriched


def _focus_key(*items: dict[str, object] | None) -> str:
    for item in items:
        value = _canonical_segment(str((item or {}).get("canonical_key") or ""), index=-1)
        if value:
            return value
    return "current-user"


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


def _parse_dt(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
