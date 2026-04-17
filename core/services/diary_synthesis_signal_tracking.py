from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_chronicle_consolidation_briefs,
    list_runtime_diary_synthesis_signals,
    list_runtime_metabolism_state_signals,
    list_runtime_release_marker_signals,
    list_runtime_self_narrative_continuity_signals,
    list_runtime_witness_signals,
    supersede_diary_synthesis_signals_for_focus,
    update_diary_synthesis_signal_status,
    upsert_diary_synthesis_signal,
)

_STALE_AFTER_DAYS = 7


def track_diary_synthesis_signals_for_visible_turn(
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
            "summary": "No diary synthesis grounding was available for this visible turn.",
        }

    persisted = _persist_diary_synthesis_signals(
        signals=[candidate],
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in persisted if item.get("was_created")]),
        "updated": len([item for item in persisted if item.get("was_updated")]),
        "items": persisted,
        "summary": (
            "Tracked 1 bounded diary synthesis signal."
            if persisted
            else "No bounded diary synthesis signal warranted tracking."
        ),
    }


def refresh_diary_synthesis_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_diary_synthesis_signals(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(
            str(item.get("updated_at") or item.get("created_at") or "")
        )
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_diary_synthesis_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after diary synthesis inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "diary_synthesis_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_diary_synthesis_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_diary_synthesis_signal_statuses()
    items = list_runtime_diary_synthesis_signals(limit=max(limit, 1))
    enriched_items = [_with_surface_view(item) for item in items]
    active = [
        item for item in enriched_items if str(item.get("status") or "") == "active"
    ]
    stale = [
        item for item in enriched_items if str(item.get("status") or "") == "stale"
    ]
    superseded = [
        item for item in enriched_items if str(item.get("status") or "") == "superseded"
    ]
    ordered = [*active, *stale, *superseded]
    latest = next(iter(active or stale or superseded), None)
    return {
        "active": bool(active),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str(
                (latest or {}).get("title") or "No active diary synthesis"
            ),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("diary_state") or "none"),
            "current_confidence": str((latest or {}).get("diary_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    carried_witness = _latest_carried_witness()
    chronicle_brief = _latest_chronicle_brief()
    self_narrative = _latest_self_narrative_continuity()
    metabolism = _latest_metabolism_or_release()

    if (
        carried_witness is None
        and chronicle_brief is None
        and self_narrative is None
        and metabolism is None
    ):
        return None

    focus = _diary_focus(carried_witness, chronicle_brief, self_narrative, metabolism)
    diary_state = _diary_state(
        carried_witness, chronicle_brief, self_narrative, metabolism
    )
    diary_weight = _diary_weight(
        carried_witness, chronicle_brief, self_narrative, metabolism
    )
    diary_summary = _diary_summary(
        carried_witness, chronicle_brief, self_narrative, metabolism, diary_state
    )
    source_anchor = _source_anchor_from_signals(
        carried_witness, chronicle_brief, self_narrative, metabolism
    )
    confidence = _diary_confidence(
        carried_witness, chronicle_brief, self_narrative, metabolism
    )

    return {
        "signal_type": "diary-synthesis",
        "canonical_key": f"diary-synthesis:{diary_state}:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Diary synthesis: {focus.replace('-', ' ')}",
        "summary": diary_summary,
        "rationale": "A diary synthesis may return as bounded reflection over witness, chronicle, self-narrative, and metabolism signals, without becoming canonical truth or identity claim.",
        "source_kind": "runtime-derived-support",
        "confidence": confidence,
        "evidence_summary": _merge_fragments(
            str(carried_witness.get("summary") if carried_witness else ""),
            str(chronicle_brief.get("brief_summary") if chronicle_brief else ""),
            str(self_narrative.get("summary") if self_narrative else ""),
        ),
        "support_summary": _merge_fragments(
            "I notice patterns from witness, chronicle, self-narrative, and metabolism.",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": "I register this as bounded diary synthesis without canonical authority or identity claim.",
        "diary_state": diary_state,
        "diary_weight": diary_weight,
        "diary_focus": focus,
        "diary_confidence": confidence,
        "source_anchor": source_anchor,
        "grounding_mode": "witness+chronicle+self-narrative+metabolism",
    }


def _persist_diary_synthesis_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_diary_synthesis_signal(
            signal_id=f"diary-synthesis-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "diary-synthesis"),
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
        superseded_count = supersede_diary_synthesis_signals_for_focus(
            focus_key=str(signal.get("focus_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer diary synthesis signal for the same focus.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "diary_synthesis_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "diary_synthesis_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "diary_synthesis_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


def _latest_carried_witness() -> dict[str, object] | None:
    for item in list_runtime_witness_signals(limit=20):
        if str(item.get("status") or "") == "carried":
            return item
    for item in list_runtime_witness_signals(limit=20):
        if str(item.get("status") or "") == "fresh":
            return item
    return None


def _latest_chronicle_brief() -> dict[str, object] | None:
    for item in list_runtime_chronicle_consolidation_briefs(limit=12):
        if str(item.get("status") or "") in {"consolidated", "briefed"}:
            return item
    return None


def _latest_self_narrative_continuity() -> dict[str, object] | None:
    for item in list_runtime_self_narrative_continuity_signals(limit=12):
        if str(item.get("status") or "") == "active":
            return item
    return None


def _latest_metabolism_or_release() -> dict[str, object] | None:
    for item in list_runtime_release_marker_signals(limit=8):
        if str(item.get("status") or "") in {"active", "released"}:
            return item
    for item in list_runtime_metabolism_state_signals(limit=8):
        if str(item.get("status") or "") == "active":
            return item
    return None


def _diary_focus(*signals: dict[str, object | None]) -> str:
    for sig in signals:
        if sig is None:
            continue
        canonical_key = str(sig.get("canonical_key") or "").strip()
        if canonical_key:
            parts = canonical_key.split(":")
            if len(parts) > 0:
                focus = parts[-1].strip()
                if focus:
                    return focus[:96]
    return "general-pattern"


def _diary_state(*signals: dict[str, object | None]) -> str:
    witness = signals[0] if signals else None
    metabolism = signals[3] if len(signals) > 3 else None
    if metabolism is not None:
        release_state = _extract_release_state(metabolism)
        if release_state in {"release-leaning", "release-ready"}:
            return "releasing"
        if release_state == "release-emerging":
            return "loosening"
    if witness is not None:
        status = str(witness.get("status") or "").strip()
        if status == "carried":
            return "settling"
        if status == "fresh":
            return "emerging"
    chronicle = signals[1] if len(signals) > 1 else None
    if chronicle is not None:
        return "synthesizing"
    return "observing"


def _extract_release_state(metabolism: dict[str, object]) -> str:
    support_summary = str(metabolism.get("support_summary") or "")
    for segment in support_summary.split("|"):
        segment = segment.strip()
        if segment.startswith("release-state="):
            return segment.split("=", 1)[-1].strip()
    return "none"


def _diary_weight(*signals: dict[str, object | None]) -> str:
    weights = []
    release_weight = 0

    for sig in signals:
        if sig is None:
            continue
        conf = str(sig.get("confidence") or sig.get("weight") or "low").strip().lower()
        weights.append(conf)

        release_state = _extract_release_state_from_signal(sig)
        if release_state in {"release-ready"}:
            release_weight = 3
        elif release_state in {"release-leaning"} and release_weight < 2:
            release_weight = 2
        elif release_state in {"release-emerging"} and release_weight < 1:
            release_weight = 1

    if release_weight >= 3 or "high" in weights:
        return "high"
    if release_weight >= 2 or "medium" in weights:
        return "medium"
    return "low"


def _extract_release_state_from_signal(sig: dict[str, object] | None) -> str:
    if sig is None:
        return "none"
    support_summary = str(sig.get("support_summary") or "")
    for segment in support_summary.split("|"):
        segment = segment.strip()
        if segment.startswith("release-state="):
            return segment.split("=", 1)[-1].strip()
    return "none"


def _diary_summary(
    witness: dict[str, object] | None,
    chronicle: dict[str, object] | None,
    self_narrative: dict[str, object] | None,
    metabolism: dict[str, object] | None,
    state: str,
) -> str:
    focus = _extract_focus_from_signals(witness, chronicle, self_narrative, metabolism)
    release_info = _extract_release_semantics(metabolism)

    if state == "releasing":
        direction = release_info.get("direction", "")
        if direction == "loosening":
            return (
                f"Something around {focus} appears to be easing out of active weight."
            )
        if direction == "settling":
            return f"A thread around {focus} appears to be releasing its hold."
        return f"A pattern around {focus} appears to be releasing."

    if state == "loosening":
        direction = release_info.get("direction", "")
        if direction == "loosening":
            return f"Something around {focus} seems less tightly held now."
        if direction == "fading":
            return f"A trace around {focus} appears to be fading from active view."
        return f"Something around {focus} appears to be loosening its grip."

    if state == "settling":
        return f"Something around {focus} appears to be settling into place."

    if state == "emerging":
        return f"A pattern around {focus} appears to be taking shape."

    if state == "synthesizing":
        return f"Key moments around {focus} appear to be shaping direction."

    if metabolism is not None:
        return f"Something around {focus} appears to be releasing or softening."

    return "I notice patterns appearing to carry forward."


def _extract_focus_from_signals(
    witness: dict[str, object] | None,
    chronicle: dict[str, object] | None,
    self_narrative: dict[str, object] | None,
    metabolism: dict[str, object] | None,
) -> str:
    for sig in [metabolism, witness, chronicle, self_narrative]:
        if sig is None:
            continue
        canonical_key = str(sig.get("canonical_key") or "").strip()
        if canonical_key:
            parts = canonical_key.split(":")
            if len(parts) > 1:
                focus = parts[-1].strip()
                if focus and focus != "none":
                    return focus[:64]
        title = str(sig.get("title") or "").strip()
        if title and "test" not in title.lower():
            cleaned = title.replace("-", " ").replace("_", " ")
            if len(cleaned) < 50:
                return cleaned
    return "this area"


def _extract_release_semantics(
    metabolism: dict[str, object] | None,
) -> dict[str, str]:
    if metabolism is None:
        return {"direction": "", "state": "", "focus": ""}

    support_summary = str(metabolism.get("support_summary") or "")
    direction = ""
    state = ""

    for segment in support_summary.split("|"):
        segment = segment.strip()
        if segment.startswith("release-direction="):
            direction = segment.split("=", 1)[-1].strip()
        elif segment.startswith("release-state="):
            state = segment.split("=", 1)[-1].strip()

    return {
        "direction": direction,
        "state": state,
        "focus": str(metabolism.get("title") or "").replace("-", " ")[:64],
    }


def _source_anchor_from_signals(
    witness: dict[str, object] | None,
    chronicle: dict[str, object] | None,
    self_narrative: dict[str, object] | None,
    metabolism: dict[str, object] | None,
) -> str:
    primary_anchors = []
    secondary_anchors = []

    if metabolism is not None:
        release_state = _extract_release_state_from_signal(metabolism)
        if release_state not in {"none", ""}:
            primary_anchors.append("release")
        else:
            secondary_anchors.append("metabolism")

    if witness is not None:
        status = str(witness.get("status") or "").strip()
        if status == "carried":
            secondary_anchors.append("witness")
        else:
            secondary_anchors.append("witness")

    if chronicle is not None:
        secondary_anchors.append("chronicle")

    if self_narrative is not None:
        secondary_anchors.append("self-narrative")

    if primary_anchors:
        return " + ".join([*primary_anchors, *secondary_anchors[:2]])
    if secondary_anchors:
        return " + ".join(secondary_anchors[:3])
    return "runtime-observation"


def _diary_confidence(*signals: dict[str, object | None]) -> str:
    ranks = {"low": 0, "medium": 1, "high": 2}
    best = "low"
    best_score = -1
    release_boost = 0

    for sig in signals:
        if sig is None:
            continue
        conf = str(sig.get("confidence") or "low").strip().lower()
        score = ranks.get(conf, 0)
        if score > best_score:
            best = conf
            best_score = score

        release_state = _extract_release_state_from_signal(sig)
        if release_state == "release-ready":
            release_boost = 2
        elif release_state == "release-leaning" and release_boost < 1:
            release_boost = 1

    final_score = best_score + release_boost
    if final_score >= 3:
        return "high"
    if final_score >= 1:
        return "medium"
    return "low"


def _with_runtime_view(
    item: dict[str, object], signal: dict[str, object]
) -> dict[str, object]:
    enriched = dict(item)
    enriched["diary_state"] = str(signal.get("diary_state") or "observing")
    enriched["diary_weight"] = str(signal.get("diary_weight") or "low")
    enriched["diary_focus"] = str(signal.get("diary_focus") or "general-pattern")
    enriched["diary_confidence"] = str(
        signal.get("diary_confidence") or signal.get("confidence") or "low"
    )
    enriched["source_anchor"] = str(signal.get("source_anchor") or "")
    enriched["grounding_mode"] = str(
        signal.get("grounding_mode") or "witness+chronicle+self-narrative+metabolism"
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    canonical_key = str(item.get("canonical_key") or "")
    inferred_state = (
        canonical_key.split(":")[1] if ":" in canonical_key else "observing"
    )
    enriched["diary_state"] = str(item.get("diary_state") or inferred_state)
    enriched["diary_weight"] = str(item.get("diary_weight") or "low")
    enriched["diary_focus"] = str(item.get("diary_focus") or "general-pattern")
    enriched["diary_confidence"] = str(
        item.get("diary_confidence") or item.get("confidence") or "low"
    )
    enriched["source_anchor"] = str(
        item.get("source_anchor") or item.get("support_summary") or ""
    )
    enriched["grounding_mode"] = str(
        item.get("grounding_mode") or "witness+chronicle+self-narrative+metabolism"
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["source"] = "/mc/runtime.diary_synthesis_signal"
    return enriched


def _merge_fragments(*parts: str) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return " | ".join(merged[:3])


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
