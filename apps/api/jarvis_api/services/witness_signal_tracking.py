from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_meaning_significance_signals,
    list_runtime_relation_continuity_signals,
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflection_signals,
    list_runtime_self_narrative_continuity_signals,
    list_runtime_temperament_tendency_signals,
    list_runtime_temporal_recurrence_signals,
    list_runtime_witness_signals,
    supersede_runtime_witness_signals_for_domain,
    update_runtime_witness_signal_status,
    upsert_runtime_witness_signal,
)

_CARRIED_AFTER_DAYS = 3
_FADING_AFTER_DAYS = 14
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_witness_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_witness_signals(
        signals=_extract_witness_candidates(run_id=run_id),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded witness signals."
            if items
            else "No bounded witness signal warranted tracking."
        ),
    }


def refresh_runtime_witness_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    carried = 0
    fading = 0
    for item in list_runtime_witness_signals(limit=40):
        status = str(item.get("status") or "")
        if status not in {"fresh", "carried"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None:
            continue
        next_status = None
        reason = ""
        if status == "fresh" and updated_at <= now - timedelta(days=_CARRIED_AFTER_DAYS):
            next_status = "carried"
            reason = "The witnessed shift remains bounded, but it is now being carried rather than felt as fresh."
        elif status == "carried" and updated_at <= now - timedelta(days=_FADING_AFTER_DAYS):
            next_status = "fading"
            reason = "Marked fading after the bounded witness window aged out."
        if not next_status:
            continue
        refreshed_item = update_runtime_witness_signal_status(
            str(item.get("signal_id") or ""),
            status=next_status,
            updated_at=now.isoformat(),
            status_reason=reason,
        )
        if refreshed_item is None:
            continue
        if next_status == "carried":
            carried += 1
            event_bus.publish(
                "witness_signal.carried",
                {
                    "signal_id": refreshed_item.get("signal_id"),
                    "signal_type": refreshed_item.get("signal_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                },
            )
        else:
            fading += 1
            event_bus.publish(
                "witness_signal.fading",
                {
                    "signal_id": refreshed_item.get("signal_id"),
                    "signal_type": refreshed_item.get("signal_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                },
            )
    return {"carried_marked": carried, "fading_marked": fading}


def build_runtime_witness_signal_surface(*, limit: int = 6) -> dict[str, object]:
    refresh_runtime_witness_signal_statuses()
    items = [_with_surface_view(item) for item in list_runtime_witness_signals(limit=max(limit, 1))]
    fresh = [item for item in items if str(item.get("status") or "") == "fresh"]
    carried = [item for item in items if str(item.get("status") or "") == "carried"]
    fading = [item for item in items if str(item.get("status") or "") == "fading"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered = [*fresh, *carried, *fading, *superseded]
    latest = next(iter(fresh or carried or fading or superseded), None)
    return {
        "active": bool(fresh or carried),
        "items": ordered,
        "summary": {
            "fresh_count": len(fresh),
            "carried_count": len(carried),
            "fading_count": len(fading),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No current witness signal"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_becoming_direction": str((latest or {}).get("becoming_direction") or "none"),
            "current_becoming_weight": str((latest or {}).get("becoming_weight") or "low"),
            "current_maturation_hint": str((latest or {}).get("maturation_hint") or "none"),
            "current_maturation_state": str((latest or {}).get("maturation_state") or "none"),
            "current_maturation_marker": str((latest or {}).get("maturation_marker") or "none"),
            "current_persistence_state": str((latest or {}).get("persistence_state") or "none"),
            "current_persistence_marker": str((latest or {}).get("persistence_marker") or "none"),
            "current_witness_confidence": str((latest or {}).get("witness_confidence") or str((latest or {}).get("confidence") or "low")),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_identity_state": "not-canonical-identity-truth",
            "proposal_state": "not-selfhood-proposal",
            "moral_authority_state": "not-moral-authority",
        },
    }


def _extract_witness_candidates(*, run_id: str) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for recurrence in list_runtime_temporal_recurrence_signals(limit=18):
        if str(recurrence.get("status") or "") != "softening":
            continue
        domain_key = _temporal_domain_key(str(recurrence.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["softening_recurrence"] = recurrence

    for reflection in list_runtime_reflection_signals(limit=18):
        if str(reflection.get("status") or "") != "settled":
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["settled_reflection"] = reflection

    for focus in list_runtime_development_focuses(limit=18):
        if str(focus.get("status") or "") not in {"active", "completed"}:
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if str(focus.get("status") or "") == "active":
                bucket["active_focus"] = focus
            else:
                bucket["completed_focus"] = focus

    for goal in list_runtime_goal_signals(limit=18):
        if str(goal.get("status") or "") not in {"active", "completed"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if str(goal.get("status") or "") == "active":
                bucket["active_goal"] = goal
            else:
                bucket["completed_goal"] = goal

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        softening_recurrence = snapshot.get("softening_recurrence")
        settled_reflection = snapshot.get("settled_reflection")
        if not softening_recurrence or not settled_reflection:
            continue

        active_focus = snapshot.get("active_focus")
        completed_focus = snapshot.get("completed_focus")
        active_goal = snapshot.get("active_goal")
        completed_goal = snapshot.get("completed_goal")
        title_suffix = _domain_title(domain_key)
        self_narrative = _latest_self_narrative_continuity(run_id=run_id, domain_key=domain_key)
        meaning = _latest_meaning_significance(run_id=run_id, domain_key=domain_key)
        temperament = _latest_temperament_tendency(run_id=run_id, domain_key=domain_key)
        relation_continuity = _latest_relation_continuity(run_id=run_id, domain_key=domain_key)

        signal_type = "carried-lesson" if active_focus or active_goal or completed_goal or completed_focus else "settled-turn"
        summary = (
            f"A bounded lesson around {title_suffix.lower()} now looks carried forward."
            if signal_type == "carried-lesson"
            else f"A bounded turn around {title_suffix.lower()} now looks witnessed as a settled shift."
        )
        rationale = (
            "A previously recurring thread has softened while its reflection thread is now settled, so the change reads as a small carried development turn rather than fresh friction."
        )
        status_reason = (
            "Recurring pressure has softened and the reflective thread now looks settled enough to witness as a bounded carried shift."
        )
        candidates.append(
            _build_candidate(
                domain_key=domain_key,
                signal_type=signal_type,
                title=(
                    f"Carried lesson: {title_suffix}"
                    if signal_type == "carried-lesson"
                    else f"Witnessed turn: {title_suffix}"
                ),
                summary=summary,
                rationale=rationale,
                status_reason=status_reason,
                source_items=[
                    softening_recurrence,
                    settled_reflection,
                    active_focus,
                    completed_focus,
                    active_goal,
                    completed_goal,
                ],
                self_narrative=self_narrative,
                meaning=meaning,
                temperament=temperament,
                relation_continuity=relation_continuity,
            )
        )

    return candidates[:4]


def _persist_witness_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_witness_signal(
            signal_id=f"witness-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "witness-signal"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "fresh"),
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
        superseded_count = supersede_runtime_witness_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer witnessed development turn for the same bounded domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "witness_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "witness_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "witness_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _build_candidate(
    *,
    domain_key: str,
    signal_type: str,
    title: str,
    summary: str,
    rationale: str,
    status_reason: str,
    source_items: list[dict[str, object] | None],
    self_narrative: dict[str, object] | None,
    meaning: dict[str, object] | None,
    temperament: dict[str, object] | None,
    relation_continuity: dict[str, object] | None,
) -> dict[str, object]:
    items = [item for item in source_items if item]
    support_count = max([int(item.get("support_count") or 1) for item in items], default=1)
    session_count = max([int(item.get("session_count") or 1) for item in items], default=1)
    confidence = "high" if len(items) >= 3 else "medium"
    becoming_direction = _derive_becoming_direction(
        signal_type=signal_type,
        self_narrative=self_narrative,
        meaning=meaning,
        temperament=temperament,
        relation_continuity=relation_continuity,
    )
    becoming_weight = _derive_becoming_weight(
        self_narrative=self_narrative,
        meaning=meaning,
        temperament=temperament,
        relation_continuity=relation_continuity,
    )
    maturation_hint = _derive_maturation_hint(
        signal_type=signal_type,
        self_narrative=self_narrative,
        temperament=temperament,
        relation_continuity=relation_continuity,
    )
    maturation_state = _derive_maturation_state(
        signal_type=signal_type,
        status="fresh",
        becoming_direction=becoming_direction,
        becoming_weight=becoming_weight,
        maturation_hint=maturation_hint,
    )
    maturation_marker = _derive_maturation_marker(
        maturation_state=maturation_state,
        maturation_hint=maturation_hint,
    )
    persistence_state = _derive_persistence_state(
        status="fresh",
        becoming_direction=becoming_direction,
        maturation_state=maturation_state,
        support_count=support_count,
        session_count=session_count,
    )
    persistence_marker = _derive_persistence_marker(
        persistence_state=persistence_state,
        maturation_state=maturation_state,
    )
    witness_confidence = _stronger_confidence(
        confidence,
        str((self_narrative or {}).get("narrative_confidence") or (self_narrative or {}).get("confidence") or "low"),
        str((meaning or {}).get("meaning_confidence") or (meaning or {}).get("confidence") or "low"),
        str((temperament or {}).get("temperament_confidence") or (temperament or {}).get("confidence") or "low"),
        str((relation_continuity or {}).get("continuity_confidence") or (relation_continuity or {}).get("confidence") or "low"),
    )
    source_anchor = _merge_fragments(
        _anchor(self_narrative),
        _anchor(meaning),
        _anchor(temperament),
        _anchor(relation_continuity),
    )
    return {
        "signal_type": signal_type,
        "canonical_key": f"witness-signal:{signal_type}:{domain_key}",
        "domain_key": domain_key,
        "status": "fresh",
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": "derived-runtime-witness",
        "confidence": witness_confidence,
        "evidence_summary": _merge_fragments(*[str(item.get("evidence_summary") or "") for item in items]),
        "support_summary": _merge_fragments(
            *[str(item.get("support_summary") or "") for item in items],
            f"becoming-direction={becoming_direction}",
            f"becoming-weight={becoming_weight}",
            f"maturation-hint={maturation_hint}",
            f"maturation-state={maturation_state}",
            f"maturation-marker={maturation_marker}",
            f"persistence-state={persistence_state}",
            f"persistence-marker={persistence_marker}",
            f"witness-confidence={witness_confidence}",
            source_anchor,
        ),
        "support_count": support_count,
        "session_count": session_count,
        "status_reason": (
            status_reason
            + " Inner witness synthesis remains descriptive runtime support only, not canonical identity truth, not selfhood proposal, and not moral authority."
        ),
        "becoming_direction": becoming_direction,
        "becoming_weight": becoming_weight,
        "becoming_summary": _becoming_summary(
            domain_title=_domain_title(domain_key),
            becoming_direction=becoming_direction,
            becoming_weight=becoming_weight,
            signal_type=signal_type,
        ),
        "maturation_hint": maturation_hint,
        "maturation_state": maturation_state,
        "maturation_marker": maturation_marker,
        "maturation_weight": becoming_weight,
        "maturation_summary": _maturation_summary(
            domain_title=_domain_title(domain_key),
            becoming_direction=becoming_direction,
            maturation_state=maturation_state,
            maturation_marker=maturation_marker,
        ),
        "persistence_state": persistence_state,
        "persistence_marker": persistence_marker,
        "persistence_weight": becoming_weight,
        "persistence_summary": _persistence_summary(
            domain_title=_domain_title(domain_key),
            persistence_state=persistence_state,
            persistence_marker=persistence_marker,
            becoming_direction=becoming_direction,
        ),
        "witness_confidence": witness_confidence,
        "source_anchor": source_anchor,
    }


def _focus_domain_key(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if text.startswith("development-focus:communication:"):
        return text.removeprefix("development-focus:communication:")
    if text.startswith("development-focus:user-directed:"):
        return text.removeprefix("development-focus:user-directed:")
    if text.startswith("development-focus:runtime:"):
        parts = text.removeprefix("development-focus:runtime:").split(":")
        return parts[0] if parts else ""
    return ""


def _goal_domain_key(canonical_key: str) -> str:
    return str(canonical_key or "").removeprefix("goal-signal:")


def _reflection_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _temporal_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Witnessed thread"


def _merge_fragments(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        normalized = " ".join(str(value or "").split()).strip()
        if normalized and normalized not in parts:
            parts.append(normalized)
    return " | ".join(parts[:8])


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    support_summary = str(item.get("support_summary") or "")
    becoming_direction = _summary_marker(support_summary, "becoming-direction") or "none"
    becoming_weight = _summary_marker(support_summary, "becoming-weight") or "low"
    maturation_hint = _summary_marker(support_summary, "maturation-hint") or "none"
    maturation_state = _derive_maturation_state(
        signal_type=str(item.get("signal_type") or "witness-signal"),
        status=str(item.get("status") or "fresh"),
        becoming_direction=becoming_direction,
        becoming_weight=becoming_weight,
        maturation_hint=maturation_hint,
    )
    maturation_marker = _derive_maturation_marker(
        maturation_state=maturation_state,
        maturation_hint=maturation_hint,
    )
    persistence_state = _derive_persistence_state(
        status=str(item.get("status") or "fresh"),
        becoming_direction=becoming_direction,
        maturation_state=maturation_state,
        support_count=int(item.get("support_count") or 0),
        session_count=int(item.get("session_count") or 0),
    )
    persistence_marker = _derive_persistence_marker(
        persistence_state=persistence_state,
        maturation_state=maturation_state,
    )
    witness_confidence = _summary_marker(support_summary, "witness-confidence") or str(item.get("confidence") or "low")
    source_anchor = _last_summary_fragment(support_summary)
    becoming_summary = _becoming_summary(
        domain_title=_domain_title(_witness_domain_key(str(item.get("canonical_key") or ""))),
        becoming_direction=becoming_direction,
        becoming_weight=becoming_weight,
        signal_type=str(item.get("signal_type") or "witness-signal"),
    )
    enriched = dict(item)
    enriched.update(
        {
            "becoming_direction": becoming_direction,
            "becoming_weight": becoming_weight,
            "becoming_summary": becoming_summary,
            "maturation_hint": maturation_hint,
            "maturation_state": maturation_state,
            "maturation_marker": maturation_marker,
            "maturation_weight": becoming_weight,
            "maturation_summary": _maturation_summary(
                domain_title=_domain_title(_witness_domain_key(str(item.get("canonical_key") or ""))),
                becoming_direction=becoming_direction,
                maturation_state=maturation_state,
                maturation_marker=maturation_marker,
            ),
            "persistence_state": persistence_state,
            "persistence_marker": persistence_marker,
            "persistence_weight": becoming_weight,
            "persistence_summary": _persistence_summary(
                domain_title=_domain_title(_witness_domain_key(str(item.get("canonical_key") or ""))),
                persistence_state=persistence_state,
                persistence_marker=persistence_marker,
                becoming_direction=becoming_direction,
            ),
            "witness_confidence": witness_confidence,
            "source_anchor": source_anchor,
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_identity_state": "not-canonical-identity-truth",
            "proposal_state": "not-selfhood-proposal",
            "moral_authority_state": "not-moral-authority",
            "source": "/mc/runtime.witness_signals",
        }
    )
    return enriched


def _latest_self_narrative_continuity(*, run_id: str, domain_key: str) -> dict[str, object] | None:
    return _latest_signal_for_domain(
        list_runtime_self_narrative_continuity_signals(limit=18),
        run_id=run_id,
        domain_key=domain_key,
    )


def _latest_meaning_significance(*, run_id: str, domain_key: str) -> dict[str, object] | None:
    return _latest_signal_for_domain(
        list_runtime_meaning_significance_signals(limit=18),
        run_id=run_id,
        domain_key=domain_key,
    )


def _latest_temperament_tendency(*, run_id: str, domain_key: str) -> dict[str, object] | None:
    return _latest_signal_for_domain(
        list_runtime_temperament_tendency_signals(limit=18),
        run_id=run_id,
        domain_key=domain_key,
    )


def _latest_relation_continuity(*, run_id: str, domain_key: str) -> dict[str, object] | None:
    return _latest_signal_for_domain(
        list_runtime_relation_continuity_signals(limit=18),
        run_id=run_id,
        domain_key=domain_key,
    )


def _latest_signal_for_domain(
    items: list[dict[str, object]],
    *,
    run_id: str,
    domain_key: str,
) -> dict[str, object] | None:
    for item in items:
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_from_canonical_key(str(item.get("canonical_key") or "")) != domain_key:
            continue
        return item
    return None


def _focus_from_canonical_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _witness_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _derive_becoming_direction(
    *,
    signal_type: str,
    self_narrative: dict[str, object] | None,
    meaning: dict[str, object] | None,
    temperament: dict[str, object] | None,
    relation_continuity: dict[str, object] | None,
) -> str:
    if not any([self_narrative, meaning, temperament, relation_continuity]):
        return "none"
    narrative_direction = str((self_narrative or {}).get("narrative_direction") or "")
    meaning_type = str((meaning or {}).get("meaning_type") or "")
    temperament_type = str((temperament or {}).get("temperament_type") or "")
    continuity_state = str((relation_continuity or {}).get("continuity_state") or "")
    if narrative_direction in {"deepening", "opening", "firming", "guarding", "steadying"}:
        return narrative_direction
    if temperament_type in {"caution", "watchful-restraint"}:
        return "guarding"
    if temperament_type in {"openness"}:
        return "opening"
    if temperament_type in {"firmness"}:
        return "firming"
    if meaning_type in {"developmental-significance", "carried-significance"}:
        return "deepening"
    if continuity_state in {"trustful-continuity", "carried-alignment"}:
        return "steadying"
    return "steadying" if signal_type == "carried-lesson" else "settling"


def _derive_becoming_weight(
    *,
    self_narrative: dict[str, object] | None,
    meaning: dict[str, object] | None,
    temperament: dict[str, object] | None,
    relation_continuity: dict[str, object] | None,
) -> str:
    weights = [
        str((self_narrative or {}).get("narrative_weight") or "low"),
        str((meaning or {}).get("meaning_weight") or "low"),
        str((temperament or {}).get("temperament_weight") or "low"),
        str((relation_continuity or {}).get("continuity_weight") or "low"),
    ]
    if "high" in weights:
        return "high"
    if "medium" in weights:
        return "medium"
    return "low"


def _derive_maturation_hint(
    *,
    signal_type: str,
    self_narrative: dict[str, object] | None,
    temperament: dict[str, object] | None,
    relation_continuity: dict[str, object] | None,
) -> str:
    if not any([self_narrative, temperament, relation_continuity]):
        return "none"
    narrative_state = str((self_narrative or {}).get("narrative_state") or "")
    temperament_type = str((temperament or {}).get("temperament_type") or "")
    continuity_state = str((relation_continuity or {}).get("continuity_state") or "")
    if narrative_state:
        return narrative_state
    if signal_type == "carried-lesson" and continuity_state:
        return continuity_state
    if temperament_type:
        return temperament_type
    return "witnessed-settling"


def _derive_maturation_state(
    *,
    signal_type: str,
    status: str,
    becoming_direction: str,
    becoming_weight: str,
    maturation_hint: str,
) -> str:
    if becoming_direction == "none":
        return "none"
    if status == "carried":
        return "carried"
    if signal_type == "carried-lesson" and becoming_direction == "deepening":
        return "deepening"
    if becoming_weight == "high":
        return "consolidating"
    if maturation_hint in {"becoming-steady", "steadiness", "carried-alignment", "trustful-continuity"}:
        return "stabilizing"
    return "emerging"


def _derive_maturation_marker(
    *,
    maturation_state: str,
    maturation_hint: str,
) -> str:
    if maturation_state == "none":
        return "none"
    if maturation_state == "carried":
        return "carried-marker"
    if maturation_state == "deepening":
        return "deepening-marker"
    if maturation_state == "consolidating":
        return "consolidating-marker"
    if maturation_state == "stabilizing":
        return "stabilizing-marker"
    if maturation_hint in {"becoming-watchful", "watchful-restraint"}:
        return "watchful-marker"
    return "emerging-marker"


def _derive_persistence_state(
    *,
    status: str,
    becoming_direction: str,
    maturation_state: str,
    support_count: int,
    session_count: int,
) -> str:
    if becoming_direction == "none":
        return "none"
    if status == "carried":
        return "carried-forward"
    if session_count >= 3:
        return "persistent"
    if session_count >= 2:
        return "stabilizing-over-time"
    if support_count >= 3 or maturation_state in {"deepening", "consolidating"}:
        return "recurring"
    return "transient"


def _derive_persistence_marker(
    *,
    persistence_state: str,
    maturation_state: str,
) -> str:
    if persistence_state == "none":
        return "none"
    if persistence_state == "persistent":
        return "persistent-marker"
    if persistence_state == "carried-forward":
        return "carried-forward-marker"
    if persistence_state == "stabilizing-over-time":
        return "stabilizing-over-time-marker"
    if persistence_state == "recurring":
        return "recurring-marker"
    if maturation_state == "emerging":
        return "transient-marker"
    return "transient-marker"


def _becoming_summary(
    *,
    domain_title: str,
    becoming_direction: str,
    becoming_weight: str,
    signal_type: str,
) -> str:
    if becoming_direction == "none":
        return f"Inner witness is holding only a bounded witnessed turn around {domain_title.lower()}, without enough becoming substrate yet."
    witness_frame = "appears to be becoming" if signal_type == "carried-lesson" else "shows signs of becoming"
    return (
        f"Inner witness {witness_frame} more {becoming_direction.replace('-', ' ')} around {domain_title.lower()}, "
        f"with {becoming_weight} bounded witness weight."
    )


def _maturation_summary(
    *,
    domain_title: str,
    becoming_direction: str,
    maturation_state: str,
    maturation_marker: str,
) -> str:
    if maturation_state == "none":
        return f"Inner witness is not surfacing a bounded maturation marker around {domain_title.lower()} yet."
    return (
        f"Inner witness shows signs of {maturation_state.replace('-', ' ')} toward {becoming_direction.replace('-', ' ')} "
        f"around {domain_title.lower()}, via {maturation_marker.replace('-', ' ')}."
    )


def _persistence_summary(
    *,
    domain_title: str,
    persistence_state: str,
    persistence_marker: str,
    becoming_direction: str,
) -> str:
    if persistence_state == "none":
        return f"Inner witness is not surfacing a bounded persistence signal around {domain_title.lower()} yet."
    return (
        f"Inner witness appears to persist {becoming_direction.replace('-', ' ')} around {domain_title.lower()} as "
        f"{persistence_state.replace('-', ' ')}, via {persistence_marker.replace('-', ' ')}."
    )


def _summary_marker(text: str, key: str) -> str:
    prefix = f"{key}="
    for part in str(text or "").split("|"):
        normalized = " ".join(part.split()).strip()
        if normalized.startswith(prefix):
            return normalized.removeprefix(prefix).strip()
    return ""


def _last_summary_fragment(text: str) -> str:
    parts = [" ".join(part.split()).strip() for part in str(text or "").split("|")]
    parts = [part for part in parts if part and "=" not in part]
    return parts[-1] if parts else ""


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    return str(item.get("source_anchor") or item.get("title") or "").strip()


def _parse_dt(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _stronger_confidence(*values: str) -> str:
    strongest = "low"
    strongest_rank = -1
    for value in values:
        normalized = str(value or "").strip()
        rank = _CONFIDENCE_RANKS.get(normalized, -1)
        if rank > strongest_rank:
            strongest = normalized or strongest
            strongest_rank = rank
    return strongest if strongest in _CONFIDENCE_RANKS else "low"


# ---------------------------------------------------------------------------
# Bounded inner witness daemon light
# ---------------------------------------------------------------------------

_DAEMON_COOLDOWN_MINUTES = 10   # Min minutes between daemon runs
_DAEMON_VISIBLE_GRACE_MINUTES = 3  # Don't run if visible activity this recent

# Module-level daemon state (in-memory)
_daemon_last_run_at: str = ""
_daemon_last_result: dict[str, object] | None = None


def run_witness_daemon(
    *,
    trigger: str = "heartbeat-idle",
    last_visible_at: str = "",
) -> dict[str, object]:
    """Bounded inner witness daemon — produces witness signals without visible turn.

    Called from heartbeat tick completion. Respects cadence, cooldown, and
    recency constraints. Returns observable result dict.

    Constraints:
    - Max once per _DAEMON_COOLDOWN_MINUTES
    - Not within _DAEMON_VISIBLE_GRACE_MINUTES of visible activity
    - Only if candidate extraction finds grounded material
    - Non-user-facing, non-canonical
    """
    global _daemon_last_run_at, _daemon_last_result
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    # Cadence gate: cooldown since last run
    if _daemon_last_run_at:
        last_run = _parse_dt(_daemon_last_run_at)
        if last_run and (now - last_run) < timedelta(minutes=_DAEMON_COOLDOWN_MINUTES):
            result = {
                "daemon_ran": False,
                "daemon_blocked_reason": "cooldown-active",
                "daemon_cadence_state": "cooling-down",
                "minutes_since_last": round((now - last_run).total_seconds() / 60, 1),
                "cooldown_minutes": _DAEMON_COOLDOWN_MINUTES,
                "trigger": trigger,
            }
            _daemon_last_result = result
            return result

    # Visible activity grace: don't run too close to visible turns
    if last_visible_at:
        last_visible = _parse_dt(last_visible_at)
        if last_visible and (now - last_visible) < timedelta(minutes=_DAEMON_VISIBLE_GRACE_MINUTES):
            result = {
                "daemon_ran": False,
                "daemon_blocked_reason": "visible-activity-too-recent",
                "daemon_cadence_state": "grace-period",
                "minutes_since_visible": round((now - last_visible).total_seconds() / 60, 1),
                "grace_minutes": _DAEMON_VISIBLE_GRACE_MINUTES,
                "trigger": trigger,
            }
            _daemon_last_result = result
            return result

    # Extract candidates using synthetic run_id
    synthetic_run_id = f"witness-daemon-{uuid4().hex[:12]}"
    candidates = _extract_witness_candidates(run_id=synthetic_run_id)

    if not candidates:
        result = {
            "daemon_ran": True,
            "daemon_blocked_reason": "",
            "daemon_cadence_state": "ran-no-candidates",
            "daemon_created_count": 0,
            "trigger": trigger,
            "daemon_source": "heartbeat-idle",
        }
        _daemon_last_run_at = now_iso
        _daemon_last_result = result
        event_bus.publish(
            "witness_signal.daemon_ran",
            {
                "trigger": trigger,
                "created_count": 0,
                "cadence_state": "ran-no-candidates",
            },
        )
        return result

    # Persist witness signals with synthetic IDs
    persisted = _persist_witness_signals(
        signals=candidates,
        session_id="heartbeat",
        run_id=synthetic_run_id,
    )

    created_count = len([p for p in persisted if p.get("was_created")])
    updated_count = len([p for p in persisted if p.get("was_updated")])
    signal_titles = [str(p.get("title") or "") for p in persisted if p.get("was_created")]

    _daemon_last_run_at = now_iso

    result = {
        "daemon_ran": True,
        "daemon_blocked_reason": "",
        "daemon_cadence_state": "ran-produced",
        "daemon_created_count": created_count,
        "daemon_updated_count": updated_count,
        "daemon_signal_titles": signal_titles[:4],
        "daemon_source": "heartbeat-idle",
        "trigger": trigger,
        "run_id": synthetic_run_id,
    }
    _daemon_last_result = result

    event_bus.publish(
        "witness_signal.daemon_produced",
        {
            "trigger": trigger,
            "created_count": created_count,
            "updated_count": updated_count,
            "signal_titles": signal_titles[:4],
            "cadence_state": "ran-produced",
            "run_id": synthetic_run_id,
        },
    )

    return result


def get_witness_daemon_state() -> dict[str, object]:
    """Return current witness daemon state for MC observability."""
    return {
        "last_run_at": _daemon_last_run_at or None,
        "last_result": _daemon_last_result,
        "cooldown_minutes": _DAEMON_COOLDOWN_MINUTES,
        "visible_grace_minutes": _DAEMON_VISIBLE_GRACE_MINUTES,
    }
