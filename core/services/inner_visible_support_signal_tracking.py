from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_executive_contradiction_signals,
    list_runtime_inner_visible_support_signals,
    list_runtime_private_state_snapshots,
    list_runtime_private_temporal_curiosity_states,
    supersede_runtime_inner_visible_support_signals_for_focus,
    update_runtime_inner_visible_support_signal_status,
    upsert_runtime_inner_visible_support_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_inner_visible_support_signals_for_visible_turn(
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
            "summary": "No bounded inner-visible support grounding was available for this visible turn.",
        }

    persisted = _persist_inner_visible_support_signals(
        signals=[candidate],
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in persisted if item.get("was_created")]),
        "updated": len([item for item in persisted if item.get("was_updated")]),
        "items": persisted,
        "summary": (
            "Tracked 1 bounded inner-visible runtime support signal."
            if persisted
            else "No bounded inner-visible runtime support signal warranted tracking."
        ),
    }


def refresh_runtime_inner_visible_support_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_inner_visible_support_signals(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_inner_visible_support_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded inner-visible support inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "inner_visible_support_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_inner_visible_support_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_inner_visible_support_signal_statuses()
    items = list_runtime_inner_visible_support_signals(limit=max(limit, 1))
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
        "prompt_bridge_state": "gated-visible-prompt-bridge",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active inner-visible support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_tone": str((latest or {}).get("support_tone") or "none"),
            "current_stance": str((latest or {}).get("support_stance") or "steady"),
            "current_directness": str((latest or {}).get("support_directness") or "medium"),
            "current_watchfulness": str((latest or {}).get("support_watchfulness") or "low"),
            "current_watchfulness_source": str(
                (latest or {}).get("support_watchfulness_source") or "state-or-curiosity"
            ),
            "current_contradiction_sharpening": str(
                (latest or {}).get("support_contradiction_sharpening") or "none"
            ),
            "current_momentum": str((latest or {}).get("support_momentum") or "steady"),
            "current_confidence": str((latest or {}).get("support_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "prompt_bridge_state": "gated-visible-prompt-bridge",
        },
    }


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    private_state = _latest_private_state_snapshot(run_id=run_id)
    if private_state is None:
        return None
    curiosity_state = _latest_temporal_curiosity_state(run_id=run_id)

    focus = _focus_key(private_state, curiosity_state)
    executive_contradiction = _latest_executive_contradiction_signal(run_id=run_id, focus_key=focus)
    state_tone = _value(private_state.get("state_tone"), default="steady-support")
    state_pressure = _value(private_state.get("state_pressure"), default="low")
    curiosity_type = _value(curiosity_state.get("curiosity_type") if curiosity_state else "", default="none")
    curiosity_pull = _value(curiosity_state.get("curiosity_pull") if curiosity_state else "", default="low")
    contradiction_pressure = _value(
        executive_contradiction.get("control_pressure") if executive_contradiction else "",
        default="low",
    )
    contradiction_status = _value(
        executive_contradiction.get("status") if executive_contradiction else "",
        default="none",
    )
    contradiction_type = _value(
        executive_contradiction.get("control_type") if executive_contradiction else "",
        default="none",
    )
    contradiction_sharpening = (
        "bounded-watchfulness"
        if executive_contradiction is not None and contradiction_status in {"active", "softening"}
        else "none"
    )

    support_tone = _derive_support_tone(
        state_tone=state_tone,
        curiosity_pull=curiosity_pull,
        contradiction_pressure=contradiction_pressure,
    )
    support_stance = _derive_support_stance(
        state_tone=state_tone,
        curiosity_type=curiosity_type,
        contradiction_type=contradiction_type,
    )
    support_directness = _derive_support_directness(
        state_pressure=state_pressure,
        curiosity_pull=curiosity_pull,
        contradiction_pressure=contradiction_pressure,
    )
    support_watchfulness = _derive_support_watchfulness(
        state_pressure=state_pressure,
        curiosity_pull=curiosity_pull,
        curiosity_type=curiosity_type,
        contradiction_pressure=contradiction_pressure,
    )
    support_momentum = _derive_support_momentum(
        state_pressure=state_pressure,
        curiosity_type=curiosity_type,
    )
    support_watchfulness_source = (
        "executive-contradiction" if contradiction_sharpening != "none" else "state-or-curiosity"
    )
    support_confidence = _stronger_confidence(
        str(private_state.get("state_confidence") or private_state.get("confidence") or "low"),
        str(curiosity_state.get("curiosity_confidence") or curiosity_state.get("confidence") or "low")
        if curiosity_state
        else "low",
        str(executive_contradiction.get("control_confidence") or executive_contradiction.get("confidence") or "low")
        if executive_contradiction
        else "low",
    )
    support_summary = _bounded_support_summary(
        private_state=private_state,
        curiosity_state=curiosity_state,
        executive_contradiction=executive_contradiction,
        tone=support_tone,
        stance=support_stance,
    )
    source_anchor = _merge_fragments(
        _support_anchor(private_state),
        _support_anchor(curiosity_state) if curiosity_state else "",
        _support_anchor(executive_contradiction) if executive_contradiction else "",
    )
    evidence_summary = _merge_fragments(
        str(private_state.get("evidence_summary") or ""),
        str(curiosity_state.get("evidence_summary") or "") if curiosity_state else "",
        str(executive_contradiction.get("evidence_summary") or "") if executive_contradiction else "",
    )
    grounding_mode = _grounding_mode(
        has_curiosity=curiosity_state is not None,
        has_executive_contradiction=executive_contradiction is not None,
    )

    return {
        "signal_type": "inner-visible-support",
        "canonical_key": f"inner-visible-support:{support_tone}:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Inner visible support: {focus.replace('-', ' ')}",
        "summary": (
            f"Bounded inner-visible runtime support is holding a small outward-facing support shape around {focus.replace('-', ' ')}."
        ),
        "rationale": (
            "A bounded inner-visible support signal may be derived only from already-returned private-state runtime support, optional temporal-curiosity sharpening, and small executive-contradiction watchfulness sharpening, without becoming prompt authority, planner authority, workflow authority, or canonical self."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": support_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded private-state runtime support, optional temporal-curiosity sharpening, and small executive-contradiction watchfulness sharpening.",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "Bounded inner-visible support remains subordinate to visible/runtime truth, is non-authoritative, may contribute only one tiny gated prompt-support line, and cannot directly veto execution."
        ),
        "support_type": "bounded-inner-visible-support",
        "support_tone": support_tone,
        "support_stance": support_stance,
        "support_directness": support_directness,
        "support_watchfulness": support_watchfulness,
        "support_watchfulness_source": support_watchfulness_source,
        "support_contradiction_sharpening": contradiction_sharpening,
        "support_momentum": support_momentum,
        "support_summary_text": support_summary,
        "support_confidence": support_confidence,
        "source_anchor": source_anchor,
        "state_snapshot_id": str(private_state.get("snapshot_id") or ""),
        "temporal_curiosity_state_id": str(curiosity_state.get("state_id") or "") if curiosity_state else "",
        "executive_contradiction_signal_id": str(executive_contradiction.get("signal_id") or "")
        if executive_contradiction
        else "",
        "grounding_mode": grounding_mode,
        "prompt_bridge_state": "gated-visible-prompt-bridge",
    }


def _persist_inner_visible_support_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_inner_visible_support_signal(
            signal_id=f"inner-visible-support-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "inner-visible-support"),
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
        superseded_count = supersede_runtime_inner_visible_support_signals_for_focus(
            focus_key=str(signal.get("focus_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded inner-visible runtime support signal for the same visible-work focus.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "inner_visible_support_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "inner_visible_support_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "inner_visible_support_signal.updated",
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
    for item in list_runtime_private_state_snapshots(limit=12):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        return item
    return None


def _latest_temporal_curiosity_state(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_temporal_curiosity_states(limit=12):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        return item
    return None


def _latest_executive_contradiction_signal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    fallback: dict[str, object] | None = None
    for item in list_runtime_executive_contradiction_signals(limit=16):
        status = str(item.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if fallback is None:
            fallback = item
        if _canonical_focus_segment(str(item.get("canonical_key") or "")) == focus_key:
            return item
    return fallback


def _with_runtime_view(
    persisted: dict[str, object],
    signal: dict[str, object],
) -> dict[str, object]:
    item = dict(persisted)
    item.update(
        {
            "support_type": signal.get("support_type"),
            "support_tone": signal.get("support_tone"),
            "support_stance": signal.get("support_stance"),
            "support_directness": signal.get("support_directness"),
            "support_watchfulness": signal.get("support_watchfulness"),
            "support_watchfulness_source": signal.get("support_watchfulness_source"),
            "support_contradiction_sharpening": signal.get("support_contradiction_sharpening"),
            "support_momentum": signal.get("support_momentum"),
            "support_summary": signal.get("support_summary_text"),
            "support_confidence": signal.get("support_confidence"),
            "source_anchor": signal.get("source_anchor"),
            "state_snapshot_id": signal.get("state_snapshot_id"),
            "temporal_curiosity_state_id": signal.get("temporal_curiosity_state_id"),
            "executive_contradiction_signal_id": signal.get("executive_contradiction_signal_id"),
            "grounding_mode": signal.get("grounding_mode"),
            "prompt_bridge_state": signal.get("prompt_bridge_state"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        }
    )
    return item


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    canonical_key = str(item.get("canonical_key") or "")
    has_executive_sharpening = _supports_executive_sharpening(item)
    support_tone = _value(
        item.get("support_tone"),
        _canonical_segment(canonical_key, index=1),
        default="steady-support",
    )
    support_stance = _value(
        item.get("support_stance"),
        default="careful" if has_executive_sharpening else "steady",
    )
    support_directness = _value(item.get("support_directness"), default="medium")
    support_watchfulness = _value(
        item.get("support_watchfulness"),
        default="medium" if has_executive_sharpening else "low",
    )
    support_momentum = _value(item.get("support_momentum"), default="steady")
    support_confidence = _value(
        item.get("support_confidence"),
        item.get("confidence"),
        default="low",
    )
    support_summary = _value(
        item.get("support_summary"),
        item.get("summary"),
        default="No bounded inner-visible runtime support.",
    )
    source_anchor = _support_anchor(item)
    enriched = dict(item)
    enriched.update(
        {
            "support_type": _value(item.get("support_type"), default="bounded-inner-visible-support"),
            "support_tone": support_tone,
            "support_stance": support_stance,
            "support_directness": support_directness,
            "support_watchfulness": support_watchfulness,
            "support_watchfulness_source": _value(
                item.get("support_watchfulness_source"),
                default="executive-contradiction" if has_executive_sharpening else "state-or-curiosity",
            ),
            "support_contradiction_sharpening": _value(
                item.get("support_contradiction_sharpening"),
                default="bounded-watchfulness" if has_executive_sharpening else "none",
            ),
            "support_momentum": support_momentum,
            "support_summary": support_summary,
            "support_confidence": support_confidence,
            "source_anchor": source_anchor,
            "grounding_mode": _value(
                item.get("grounding_mode"),
                default="private-state+executive-contradiction" if has_executive_sharpening else "private-state",
            ),
            "prompt_bridge_state": _value(item.get("prompt_bridge_state"), default="gated-visible-prompt-bridge"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "source": "/mc/runtime.inner_visible_support_signal",
            "createdAt": str(item.get("created_at") or ""),
        }
    )
    return enriched


def _focus_key(private_state: dict[str, object], curiosity_state: dict[str, object] | None) -> str:
    for candidate in (
        _canonical_focus_segment(str(private_state.get("canonical_key") or "")),
        _canonical_focus_segment(str(curiosity_state.get("canonical_key") or "")) if curiosity_state else "",
        _slug(str(private_state.get("title") or "")),
    ):
        if candidate:
            return candidate
    return "visible-work"


def _derive_support_tone(*, state_tone: str, curiosity_pull: str, contradiction_pressure: str) -> str:
    if contradiction_pressure in {"high", "medium"} and curiosity_pull == "medium":
        return "careful-forward"
    if contradiction_pressure in {"high", "medium"}:
        return "careful-steady"
    if state_tone == "steady-pressure" and curiosity_pull == "medium":
        return "careful-forward"
    if state_tone == "steady-pressure":
        return "careful-steady"
    if curiosity_pull == "medium":
        return "steady-forward"
    return "steady-support"


def _derive_support_stance(*, state_tone: str, curiosity_type: str, contradiction_type: str) -> str:
    if contradiction_type in {"contradiction-pressure", "veto-watch"} and curiosity_type == "active-observation":
        return "watchful"
    if contradiction_type in {"contradiction-pressure", "veto-watch"}:
        return "careful"
    if curiosity_type == "active-observation":
        return "watchful"
    if state_tone == "steady-pressure":
        return "careful"
    return "steady"


def _derive_support_directness(*, state_pressure: str, curiosity_pull: str, contradiction_pressure: str) -> str:
    if contradiction_pressure in {"high", "medium"}:
        return "medium"
    if curiosity_pull == "medium":
        return "medium"
    if state_pressure == "medium":
        return "medium"
    return "high"


def _derive_support_watchfulness(
    *,
    state_pressure: str,
    curiosity_pull: str,
    curiosity_type: str,
    contradiction_pressure: str,
) -> str:
    if contradiction_pressure in {"high", "medium"}:
        return "medium"
    if curiosity_type == "active-observation" or curiosity_pull == "medium":
        return "medium"
    if state_pressure == "medium":
        return "medium"
    return "low"


def _derive_support_momentum(*, state_pressure: str, curiosity_type: str) -> str:
    if curiosity_type == "active-observation":
        return "carried"
    if state_pressure == "medium":
        return "held"
    return "steady"


def _bounded_support_summary(
    *,
    private_state: dict[str, object],
    curiosity_state: dict[str, object] | None,
    executive_contradiction: dict[str, object] | None,
    tone: str,
    stance: str,
) -> str:
    state_summary = str(private_state.get("state_summary") or private_state.get("summary") or "").strip()
    curiosity_summary = (
        str(curiosity_state.get("curiosity_summary") or curiosity_state.get("summary") or "").strip()
        if curiosity_state
        else ""
    )
    contradiction_summary = (
        str(executive_contradiction.get("control_summary") or executive_contradiction.get("summary") or "").strip()
        if executive_contradiction
        else ""
    )
    prefix = f"{tone.replace('-', ' ')} / {stance}"
    return _merge_fragments(prefix, state_summary, curiosity_summary, contradiction_summary)[:220]


def _grounding_mode(*, has_curiosity: bool, has_executive_contradiction: bool) -> str:
    if has_curiosity and has_executive_contradiction:
        return "private-state+temporal-curiosity+executive-contradiction"
    if has_executive_contradiction:
        return "private-state+executive-contradiction"
    if has_curiosity:
        return "private-state+temporal-curiosity"
    return "private-state"


def _supports_executive_sharpening(item: dict[str, object]) -> bool:
    grounding_mode = str(item.get("grounding_mode") or "").strip().lower()
    if "executive-contradiction" in grounding_mode:
        return True
    support_summary = str(item.get("support_summary") or "").strip().lower()
    status_reason = str(item.get("status_reason") or "").strip().lower()
    return "executive-contradiction" in support_summary or "executive contradiction" in status_reason


def _support_anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    return str(item.get("source_anchor") or item.get("support_summary") or item.get("summary") or "").strip()[:180]


def _canonical_focus_segment(value: str) -> str:
    parts = [part.strip() for part in value.split(":") if part.strip()]
    if len(parts) >= 3:
        return _slug(parts[-1])
    return ""


def _canonical_segment(value: str, *, index: int) -> str:
    parts = [part.strip() for part in value.split(":") if part.strip()]
    if len(parts) > index:
        return parts[index]
    return ""


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
    return collapsed[:64] or "visible-work"


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
