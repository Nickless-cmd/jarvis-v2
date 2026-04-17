from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_executive_contradiction_signals,
    list_runtime_meaning_significance_signals,
    list_runtime_private_state_snapshots,
    list_runtime_private_temporal_promotion_signals,
    list_runtime_regulation_homeostasis_signals,
    list_runtime_relation_continuity_signals,
    list_runtime_temperament_tendency_signals,
    supersede_runtime_temperament_tendency_signals_for_focus,
    update_runtime_temperament_tendency_signal_status,
    upsert_runtime_temperament_tendency_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_temperament_tendency_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_temperament_tendency_signals(
        signals=_extract_temperament_tendency_candidates(run_id=run_id),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded temperament-tendency signals."
            if items
            else "No bounded temperament-tendency signal warranted tracking."
        ),
    }


def refresh_runtime_temperament_tendency_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_temperament_tendency_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_temperament_tendency_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded temperament-tendency inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "temperament_tendency_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_temperament_tendency_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_temperament_tendency_signal_statuses()
    items = list_runtime_temperament_tendency_signals(limit=max(limit, 1))
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
        "canonical_personality_state": "not-canonical-personality-truth",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active temperament support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_type": str((latest or {}).get("temperament_type") or "none"),
            "current_balance": str((latest or {}).get("temperament_balance") or "steady"),
            "current_weight": str((latest or {}).get("temperament_weight") or "low"),
            "current_confidence": str((latest or {}).get("temperament_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_personality_state": "not-canonical-personality-truth",
        },
    }


def _extract_temperament_tendency_candidates(*, run_id: str) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for meaning_signal in list_runtime_meaning_significance_signals(limit=18):
        if str(meaning_signal.get("status") or "") not in {"active", "softening"}:
            continue
        if str(meaning_signal.get("run_id") or "") != run_id:
            continue
        focus = _focus_key(meaning_signal)
        relation_continuity = _latest_relation_continuity(run_id=run_id, focus_key=focus)
        regulation = _latest_regulation(run_id=run_id, focus_key=focus)
        private_state = _latest_private_state(run_id=run_id, focus_key=focus)
        if relation_continuity is None or (regulation is None and private_state is None):
            continue
        executive_contradiction = _latest_executive_contradiction(run_id=run_id, focus_key=focus)
        temporal_promotion = _latest_temporal_promotion(run_id=run_id, focus_key=focus)
        candidates.append(
            _build_candidate(
                focus=focus,
                meaning_signal=meaning_signal,
                relation_continuity=relation_continuity,
                regulation=regulation,
                private_state=private_state,
                executive_contradiction=executive_contradiction,
                temporal_promotion=temporal_promotion,
            )
        )
    return candidates[:4]


def _build_candidate(
    *,
    focus: str,
    meaning_signal: dict[str, object],
    relation_continuity: dict[str, object],
    regulation: dict[str, object] | None,
    private_state: dict[str, object] | None,
    executive_contradiction: dict[str, object] | None,
    temporal_promotion: dict[str, object] | None,
) -> dict[str, object]:
    meaning_weight = _value(meaning_signal.get("meaning_weight"), default="low")
    continuity_state = _value(relation_continuity.get("continuity_state"), default="carried-alignment")
    continuity_watchfulness = _value(relation_continuity.get("continuity_watchfulness"), default="low")
    continuity_weight = _value(relation_continuity.get("continuity_weight"), default="low")
    regulation_state = _value((regulation or {}).get("regulation_state"), default="steady-support")
    regulation_watchfulness = _value((regulation or {}).get("regulation_watchfulness"), default="low")
    contradiction_pressure = _value((executive_contradiction or {}).get("control_pressure"), default="low")
    promotion_pull = _value((temporal_promotion or {}).get("promotion_pull"), default="low")
    state_tone = _value((private_state or {}).get("state_tone"), default="steady-support")

    temperament_type = _derive_temperament_type(
        meaning_weight=meaning_weight,
        continuity_state=continuity_state,
        continuity_watchfulness=continuity_watchfulness,
        regulation_state=regulation_state,
        regulation_watchfulness=regulation_watchfulness,
        contradiction_pressure=contradiction_pressure,
        promotion_pull=promotion_pull,
        state_tone=state_tone,
    )
    temperament_balance = _derive_temperament_balance(
        temperament_type=temperament_type,
        regulation_state=regulation_state,
        contradiction_pressure=contradiction_pressure,
        promotion_pull=promotion_pull,
    )
    temperament_weight = _derive_temperament_weight(
        meaning_weight=meaning_weight,
        continuity_weight=continuity_weight,
        contradiction_pressure=contradiction_pressure,
    )
    temperament_confidence = _stronger_confidence(
        str(meaning_signal.get("meaning_confidence") or meaning_signal.get("confidence") or "low"),
        str(relation_continuity.get("continuity_confidence") or relation_continuity.get("confidence") or "low"),
        str((regulation or {}).get("regulation_confidence") or (regulation or {}).get("confidence") or "low"),
        str((executive_contradiction or {}).get("control_confidence") or (executive_contradiction or {}).get("confidence") or "low"),
        str((temporal_promotion or {}).get("promotion_confidence") or (temporal_promotion or {}).get("confidence") or "low"),
        str((private_state or {}).get("state_confidence") or (private_state or {}).get("confidence") or "low"),
    )
    status = _derive_status(
        meaning_status=str(meaning_signal.get("status") or ""),
        continuity_status=str(relation_continuity.get("status") or ""),
        regulation_status=str((regulation or {}).get("status") or ""),
    )
    grounding_mode = _grounding_mode(
        has_regulation=regulation is not None,
        has_private_state=private_state is not None,
        has_contradiction=executive_contradiction is not None,
        has_promotion=temporal_promotion is not None,
    )
    source_anchor = _merge_fragments(
        _anchor(meaning_signal),
        _anchor(relation_continuity),
        _anchor(regulation),
        _anchor(executive_contradiction),
        _anchor(temporal_promotion),
        _anchor(private_state),
    )
    evidence_summary = _merge_fragments(
        str(meaning_signal.get("evidence_summary") or ""),
        str(relation_continuity.get("evidence_summary") or ""),
        str((regulation or {}).get("evidence_summary") or ""),
        str((executive_contradiction or {}).get("evidence_summary") or ""),
        str((temporal_promotion or {}).get("evidence_summary") or ""),
        str((private_state or {}).get("evidence_summary") or ""),
    )
    focus_text = focus.replace("-", " ")

    return {
        "signal_type": "temperament-tendency",
        "canonical_key": f"temperament-tendency:{temperament_type}:{focus}",
        "focus_key": focus,
        "status": status,
        "title": f"Temperament support: {focus_text}",
        "summary": f"Bounded temperament runtime support is holding a small character-tilt around {focus_text}.",
        "rationale": (
            "A bounded temperament-tendency signal may return only when meaning/significance support already carries weight, relation continuity shows persistence, and regulation or private-state support provides stabilizing substrate, with only small contradiction or promotion sharpening, without becoming canonical personality truth, prompt authority, workflow authority, or hidden temperament engine."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": temperament_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded meaning/significance support, relation continuity support, regulation or private-state substrate, and small contradiction or temporal-promotion sharpening.",
            f"grounding-mode={grounding_mode}",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "Bounded temperament remains non-authoritative runtime support only and is not canonical personality truth."
        ),
        "temperament_type": temperament_type,
        "temperament_balance": temperament_balance,
        "temperament_weight": temperament_weight,
        "temperament_summary": _temperament_summary(
            focus=focus_text,
            temperament_type=temperament_type,
            temperament_balance=temperament_balance,
            temperament_weight=temperament_weight,
        ),
        "temperament_confidence": temperament_confidence,
        "source_anchor": source_anchor,
        "grounding_mode": grounding_mode,
        "meaning_signal_id": str(meaning_signal.get("signal_id") or ""),
        "relation_continuity_signal_id": str(relation_continuity.get("signal_id") or ""),
        "regulation_signal_id": str((regulation or {}).get("signal_id") or ""),
        "executive_contradiction_signal_id": str((executive_contradiction or {}).get("signal_id") or ""),
        "temporal_promotion_signal_id": str((temporal_promotion or {}).get("signal_id") or ""),
        "state_snapshot_id": str((private_state or {}).get("snapshot_id") or ""),
    }


def _persist_temperament_tendency_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_temperament_tendency_signal(
            signal_id=f"temperament-tendency-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "temperament-tendency"),
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
        superseded_count = supersede_runtime_temperament_tendency_signals_for_focus(
            focus_key=str(signal.get("focus_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded temperament-tendency signal for the same visible-work focus.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "temperament_tendency_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "temperament_tendency_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "temperament_tendency_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


def _latest_relation_continuity(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_relation_continuity_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_regulation(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_regulation_homeostasis_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_private_state(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_private_state_snapshots(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_executive_contradiction(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_executive_contradiction_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_temporal_promotion(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_private_temporal_promotion_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _derive_temperament_type(
    *,
    meaning_weight: str,
    continuity_state: str,
    continuity_watchfulness: str,
    regulation_state: str,
    regulation_watchfulness: str,
    contradiction_pressure: str,
    promotion_pull: str,
    state_tone: str,
) -> str:
    if contradiction_pressure == "medium" or continuity_watchfulness == "medium" or regulation_watchfulness == "medium":
        return "watchful-restraint"
    if promotion_pull == "medium" and meaning_weight in {"medium", "high"} and continuity_state == "trustful-continuity":
        return "openness"
    if meaning_weight == "high" and promotion_pull == "medium":
        return "firmness"
    if regulation_state in {"steady-support", "settling-support"} or state_tone == "steady-support":
        return "steadiness"
    return "caution"


def _derive_temperament_balance(
    *,
    temperament_type: str,
    regulation_state: str,
    contradiction_pressure: str,
    promotion_pull: str,
) -> str:
    if temperament_type == "watchful-restraint":
        return "guarded"
    if temperament_type == "firmness":
        return "steady-firmness"
    if temperament_type == "openness":
        return "steady-openness" if contradiction_pressure == "low" else "guarded-openness"
    if temperament_type == "steadiness":
        return "steady"
    if promotion_pull == "medium":
        return "curious-caution"
    return "steady-caution"


def _derive_temperament_weight(
    *,
    meaning_weight: str,
    continuity_weight: str,
    contradiction_pressure: str,
) -> str:
    if meaning_weight == "high" and continuity_weight == "high":
        return "high"
    if meaning_weight == "medium" or continuity_weight == "medium" or contradiction_pressure == "medium":
        return "medium"
    return "low"


def _derive_status(*, meaning_status: str, continuity_status: str, regulation_status: str) -> str:
    if "softening" in {meaning_status, continuity_status, regulation_status}:
        return "softening"
    return "active"


def _grounding_mode(
    *,
    has_regulation: bool,
    has_private_state: bool,
    has_contradiction: bool,
    has_promotion: bool,
) -> str:
    parts = ["meaning-significance", "relation-continuity"]
    if has_regulation:
        parts.append("regulation")
    if has_private_state:
        parts.append("private-state")
    if has_contradiction:
        parts.append("executive-contradiction")
    if has_promotion:
        parts.append("temporal-promotion")
    return "+".join(parts)


def _temperament_summary(
    *,
    focus: str,
    temperament_type: str,
    temperament_balance: str,
    temperament_weight: str,
) -> str:
    return (
        f"{focus} is carrying {temperament_weight} {temperament_type.replace('-', ' ')} "
        f"with a {temperament_balance.replace('-', ' ')} balance."
    )[:220]


def _focus_key(item: dict[str, object] | None) -> str:
    canonical_key = str((item or {}).get("canonical_key") or "")
    if canonical_key.count(":") >= 2:
        return canonical_key.split(":", 2)[2].strip() or "visible-work"
    title = str((item or {}).get("title") or "").strip().lower().replace(" ", "-")
    return title or "visible-work"


def _value(*values: object, default: str = "") -> str:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return default


def _stronger_confidence(*values: str) -> str:
    best = "low"
    best_rank = -1
    for value in values:
        rank = _CONFIDENCE_RANKS.get(str(value or "").strip().lower(), -1)
        if rank > best_rank:
            best = str(value or "").strip() or "low"
            best_rank = rank
    return best if best else "low"


def _merge_fragments(*values: object) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split()).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return " | ".join(parts[:4])


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    support_summary = str(item.get("support_summary") or "").strip()
    if support_summary:
        parts = [piece.strip() for piece in support_summary.split("|") if piece.strip()]
        if parts:
            return parts[-1][:120]
    return str(item.get("canonical_key") or item.get("title") or "").strip()[:120]


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    return {
        **item,
        "temperament_type": str(signal.get("temperament_type") or "steadiness"),
        "temperament_balance": str(signal.get("temperament_balance") or "steady"),
        "temperament_weight": str(signal.get("temperament_weight") or "low"),
        "temperament_summary": str(signal.get("temperament_summary") or item.get("summary") or ""),
        "temperament_confidence": str(signal.get("temperament_confidence") or item.get("confidence") or "low"),
        "source_anchor": str(signal.get("source_anchor") or ""),
        "grounding_mode": str(signal.get("grounding_mode") or "meaning-significance+relation-continuity"),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_personality_state": "not-canonical-personality-truth",
        "source": "/mc/runtime.temperament_tendency_signal",
    }


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    canonical_key = str(item.get("canonical_key") or "")
    support_summary = str(item.get("support_summary") or "")
    return {
        **item,
        "temperament_type": _value(
            item.get("temperament_type"),
            _canonical_segment(canonical_key, index=1),
            default="steadiness",
        ),
        "temperament_balance": _value(
            item.get("temperament_balance"),
            _balance_from_support_summary(support_summary),
            default="steady",
        ),
        "temperament_weight": _value(
            item.get("temperament_weight"),
            _weight_from_support_summary(support_summary, canonical_key=canonical_key),
            default="low",
        ),
        "temperament_summary": _value(
            item.get("temperament_summary"),
            item.get("summary"),
            default="No bounded temperament support",
        ),
        "temperament_confidence": _value(
            item.get("temperament_confidence"),
            item.get("confidence"),
            default="low",
        ),
        "source_anchor": _value(item.get("source_anchor"), _anchor(item)),
        "grounding_mode": _value(
            item.get("grounding_mode"),
            _grounding_mode_from_support_summary(support_summary),
            default="meaning-significance+relation-continuity",
        ),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_personality_state": "not-canonical-personality-truth",
        "source": "/mc/runtime.temperament_tendency_signal",
    }


def _canonical_segment(value: str, *, index: int) -> str:
    parts = [part.strip() for part in str(value or "").split(":")]
    if len(parts) <= index:
        return ""
    return parts[index]


def _grounding_mode_from_support_summary(value: str) -> str:
    for part in str(value or "").split("|"):
        normalized = part.strip()
        if normalized.startswith("grounding-mode="):
            return normalized.split("=", 1)[1].strip() or "meaning-significance+relation-continuity"
    return "meaning-significance+relation-continuity"


def _weight_from_support_summary(value: str, *, canonical_key: str) -> str:
    lowered = str(value or "").lower()
    if "high" in lowered:
        return "high"
    if "medium" in lowered:
        return "medium"
    if ":firmness:" in canonical_key:
        return "medium"
    return "low"


def _balance_from_support_summary(value: str) -> str:
    lowered = str(value or "").lower()
    for balance in ("steady-firmness", "steady-openness", "guarded-openness", "steady-caution", "curious-caution", "guarded", "steady"):
        if balance in lowered:
            return balance
    return "steady"
