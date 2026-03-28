from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_chronicle_consolidation_briefs,
    list_runtime_chronicle_consolidation_signals,
    list_runtime_consolidation_target_signals,
    list_runtime_meaning_significance_signals,
    list_runtime_metabolism_state_signals,
    list_runtime_relation_continuity_signals,
    list_runtime_release_marker_signals,
    list_runtime_self_narrative_continuity_signals,
    list_runtime_temperament_tendency_signals,
    list_runtime_witness_signals,
    supersede_runtime_consolidation_target_signals_for_domain,
    update_runtime_consolidation_target_signal_status,
    upsert_runtime_consolidation_target_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}
_WEIGHT_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_consolidation_target_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_consolidation_target_signals(
        signals=_extract_consolidation_target_candidates(run_id=run_id),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded consolidation-target signals."
            if items
            else "No bounded consolidation-target signal warranted tracking."
        ),
    }


def refresh_runtime_consolidation_target_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_consolidation_target_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_consolidation_target_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded consolidation-target inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "consolidation_target_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_consolidation_target_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_consolidation_target_signal_statuses()
    items = list_runtime_consolidation_target_signals(limit=max(limit, 1))
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
        "writeback_state": "not-writeback",
        "canonical_mutation_state": "not-canonical-mutation",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active consolidation-target support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("consolidation_state") or "none"),
            "current_focus": str((latest or {}).get("consolidation_focus") or "none"),
            "current_weight": str((latest or {}).get("consolidation_weight") or "low"),
            "current_confidence": str((latest or {}).get("consolidation_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "writeback_state": "not-writeback",
            "canonical_mutation_state": "not-canonical-mutation",
        },
    }


def _extract_consolidation_target_candidates(*, run_id: str) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for item in list_runtime_metabolism_state_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["metabolism"] = item

    for item in list_runtime_release_marker_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["release_marker"] = item

    for item in list_runtime_witness_signals(limit=18):
        if str(item.get("status") or "") not in {"carried", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["witness"] = item

    for item in list_runtime_chronicle_consolidation_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["chronicle"] = item

    for item in list_runtime_chronicle_consolidation_briefs(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["chronicle_brief"] = item

    for item in list_runtime_meaning_significance_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["meaning"] = item

    for item in list_runtime_temperament_tendency_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["temperament"] = item

    for item in list_runtime_self_narrative_continuity_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["self_narrative"] = item

    for item in list_runtime_relation_continuity_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["relation_continuity"] = item

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        metabolism = snapshot.get("metabolism")
        witness = snapshot.get("witness")
        chronicle = snapshot.get("chronicle")
        chronicle_brief = snapshot.get("chronicle_brief")
        release_marker = snapshot.get("release_marker")
        meaning = snapshot.get("meaning")
        temperament = snapshot.get("temperament")
        self_narrative = snapshot.get("self_narrative")
        relation_continuity = snapshot.get("relation_continuity")
        if metabolism is None:
            continue
        metabolism_state = _find_support_value(
            str(metabolism.get("support_summary") or ""),
            "metabolism-state",
            "metabolizing",
        )
        if metabolism_state not in {"consolidating", "active-retaining"}:
            continue
        release_state = _find_support_value(
            str((release_marker or {}).get("support_summary") or ""),
            "release-state",
            "none",
        )
        if release_state in {"release-leaning", "release-ready"}:
            continue
        if witness is None and chronicle is None and chronicle_brief is None:
            continue
        support_items = [
            item
            for item in [witness, chronicle, chronicle_brief, meaning, temperament, self_narrative, relation_continuity]
            if item is not None
        ]
        if len(support_items) < 2:
            continue
        candidates.append(
            _build_candidate(
                domain_key=domain_key,
                metabolism=metabolism,
                witness=witness,
                chronicle=chronicle,
                chronicle_brief=chronicle_brief,
                meaning=meaning,
                temperament=temperament,
                self_narrative=self_narrative,
                relation_continuity=relation_continuity,
            )
        )
    return candidates[:4]


def _build_candidate(
    *,
    domain_key: str,
    metabolism: dict[str, object],
    witness: dict[str, object] | None,
    chronicle: dict[str, object] | None,
    chronicle_brief: dict[str, object] | None,
    meaning: dict[str, object] | None,
    temperament: dict[str, object] | None,
    self_narrative: dict[str, object] | None,
    relation_continuity: dict[str, object] | None,
) -> dict[str, object]:
    items = [
        item
        for item in [metabolism, witness, chronicle, chronicle_brief, meaning, temperament, self_narrative, relation_continuity]
        if item is not None
    ]
    witness_status = str((witness or {}).get("status") or "")
    chronicle_status = str((chronicle or {}).get("status") or "")
    brief_status = str((chronicle_brief or {}).get("status") or "")
    active_like_count = sum(
        1 for item in items if str(item.get("status") or "") in {"active", "carried", "fresh"}
    )
    softening_count = sum(1 for item in items if str(item.get("status") or "") in {"softening", "fading"})
    support_count = max([int(item.get("support_count") or 1) for item in items], default=1)
    session_count = max([int(item.get("session_count") or 1) for item in items], default=1)
    consolidation_state = _derive_consolidation_state(
        witness_status=witness_status,
        chronicle_status=chronicle_status,
        brief_status=brief_status,
        active_like_count=active_like_count,
        session_count=session_count,
    )
    consolidation_focus = _derive_consolidation_focus(
        domain_key=domain_key,
        chronicle=chronicle,
        chronicle_brief=chronicle_brief,
    )
    consolidation_weight = _derive_consolidation_weight(
        active_like_count=active_like_count,
        support_count=support_count,
        session_count=session_count,
        brief_status=brief_status,
    )
    consolidation_confidence = _stronger_confidence(
        str((metabolism or {}).get("confidence") or "low"),
        str((witness or {}).get("witness_confidence") or (witness or {}).get("confidence") or "low"),
        str((chronicle or {}).get("chronicle_confidence") or (chronicle or {}).get("confidence") or "low"),
        str((chronicle_brief or {}).get("brief_confidence") or (chronicle_brief or {}).get("confidence") or "low"),
        str((meaning or {}).get("meaning_confidence") or (meaning or {}).get("confidence") or "low"),
        str((temperament or {}).get("temperament_confidence") or (temperament or {}).get("confidence") or "low"),
        str((self_narrative or {}).get("narrative_confidence") or (self_narrative or {}).get("confidence") or "low"),
        str((relation_continuity or {}).get("continuity_confidence") or (relation_continuity or {}).get("confidence") or "low"),
    )
    source_anchor = _merge_fragments(
        _anchor(metabolism),
        _anchor(witness),
        _anchor(chronicle),
        _anchor(chronicle_brief),
        _anchor(meaning),
        _anchor(temperament),
        _anchor(self_narrative),
        _anchor(relation_continuity),
    )
    evidence_summary = _merge_fragments(
        str((metabolism or {}).get("evidence_summary") or ""),
        str((witness or {}).get("evidence_summary") or ""),
        str((chronicle or {}).get("evidence_summary") or ""),
        str((chronicle_brief or {}).get("evidence_summary") or ""),
        str((meaning or {}).get("evidence_summary") or ""),
        str((temperament or {}).get("evidence_summary") or ""),
        str((self_narrative or {}).get("evidence_summary") or ""),
        str((relation_continuity or {}).get("evidence_summary") or ""),
    )
    status = "active" if consolidation_state in {"consolidation-forming", "consolidation-ready"} else "softening"
    focus_label = consolidation_focus.lower()
    return {
        "signal_type": "consolidation-target",
        "canonical_key": f"consolidation-target:{consolidation_state}:{domain_key}",
        "domain_key": domain_key,
        "status": status,
        "title": f"Consolidation support: {consolidation_focus}",
        "summary": f"Bounded consolidation runtime support is observing a small settling target around {focus_label}.",
        "rationale": (
            "A bounded consolidation-target signal may return only when metabolism already reads as consolidating or active-retaining and existing witness or chronicle support already looks carried enough to settle in compact form, without becoming chronicle writeback, memory writeback, canonical mutation, prompt authority, workflow authority, or compression execution."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": consolidation_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded metabolism-state support plus existing witness/chronicle/meaning/temperament/self-narrative/relation continuity that already appears carried enough to settle in compact form.",
            f"consolidation-state={consolidation_state}",
            f"consolidation-focus={consolidation_focus}",
            f"consolidation-weight={consolidation_weight}",
            source_anchor,
        ),
        "support_count": support_count,
        "session_count": session_count,
        "status_reason": (
            "Bounded consolidation targeting remains non-authoritative runtime support only and is not chronicle writeback, memory writeback, or canonical mutation."
        ),
        "consolidation_state": consolidation_state,
        "consolidation_focus": consolidation_focus,
        "consolidation_weight": consolidation_weight,
        "consolidation_summary": _consolidation_summary(
            focus=consolidation_focus,
            consolidation_state=consolidation_state,
            consolidation_weight=consolidation_weight,
        ),
        "consolidation_confidence": consolidation_confidence,
        "source_anchor": source_anchor,
        "metabolism_signal_id": str((metabolism or {}).get("signal_id") or ""),
        "witness_signal_id": str((witness or {}).get("signal_id") or ""),
        "chronicle_signal_id": str((chronicle or {}).get("signal_id") or ""),
        "chronicle_brief_id": str((chronicle_brief or {}).get("brief_id") or ""),
        "meaning_signal_id": str((meaning or {}).get("signal_id") or ""),
        "temperament_signal_id": str((temperament or {}).get("signal_id") or ""),
        "self_narrative_signal_id": str((self_narrative or {}).get("signal_id") or ""),
        "relation_continuity_signal_id": str((relation_continuity or {}).get("signal_id") or ""),
        "run_id": str((metabolism or {}).get("run_id") or ""),
    }


def _persist_consolidation_target_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_consolidation_target_signal(
            signal_id=f"consolidation-target-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "consolidation-target"),
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
        superseded_count = supersede_runtime_consolidation_target_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded consolidation-target reading for the same lifecycle domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "consolidation_target_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "consolidation_target_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "consolidation_target_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    support_summary = str(item.get("support_summary") or "")
    consolidation_state = _find_support_value(support_summary, "consolidation-state", "consolidation-emerging")
    consolidation_focus = _find_support_value(support_summary, "consolidation-focus", "none")
    consolidation_weight = _find_support_value(support_summary, "consolidation-weight", "low")
    return {
        **item,
        "consolidation_state": consolidation_state,
        "consolidation_focus": consolidation_focus,
        "consolidation_weight": consolidation_weight,
        "consolidation_summary": _consolidation_summary(
            focus=consolidation_focus,
            consolidation_state=consolidation_state,
            consolidation_weight=consolidation_weight,
        ),
        "consolidation_confidence": str(item.get("confidence") or "low"),
        "source_anchor": _anchor(item),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "writeback_state": "not-writeback",
        "canonical_mutation_state": "not-canonical-mutation",
        "source": "/mc/runtime.consolidation_target_signal",
    }


def _derive_consolidation_state(
    *,
    witness_status: str,
    chronicle_status: str,
    brief_status: str,
    active_like_count: int,
    session_count: int,
) -> str:
    if (brief_status == "active" or chronicle_status == "active") and witness_status == "carried" and session_count >= 2:
        return "consolidation-ready"
    if brief_status in {"active", "softening"} or chronicle_status in {"active", "softening"} or active_like_count >= 4:
        return "consolidation-forming"
    return "consolidation-emerging"


def _derive_consolidation_focus(
    *,
    domain_key: str,
    chronicle: dict[str, object] | None,
    chronicle_brief: dict[str, object] | None,
) -> str:
    for value in (
        (chronicle_brief or {}).get("brief_focus"),
        (chronicle or {}).get("chronicle_focus"),
        (chronicle_brief or {}).get("title"),
        (chronicle or {}).get("title"),
    ):
        text = str(value or "").strip()
        if text:
            return text[:96]
    return domain_key.replace("-", " ").strip()[:96]


def _derive_consolidation_weight(
    *,
    active_like_count: int,
    support_count: int,
    session_count: int,
    brief_status: str,
) -> str:
    score = active_like_count + min(support_count, 2) + min(session_count, 2)
    if brief_status == "active":
        score += 1
    if score >= 6:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def _consolidation_summary(
    *,
    focus: str,
    consolidation_state: str,
    consolidation_weight: str,
) -> str:
    focus_text = str(focus or "this thread").strip() or "this thread"
    if consolidation_state == "consolidation-ready":
        return (
            f"The runtime around {focus_text.lower()} appears ready to settle in a more compact carried form, with {consolidation_weight} consolidation weight."
        )
    if consolidation_state == "consolidation-forming":
        return (
            f"The runtime around {focus_text.lower()} shows signs of consolidating toward a more compact carried form, with {consolidation_weight} consolidation weight."
        )
    return (
        f"The runtime around {focus_text.lower()} appears to be gathering toward a bounded consolidation target, with {consolidation_weight} consolidation weight."
    )


def _domain_key(canonical_key: str) -> str:
    value = str(canonical_key or "").strip()
    if not value:
        return ""
    return value.rsplit(":", 1)[-1].strip()


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    identifier = (
        item.get("signal_id")
        or item.get("brief_id")
        or item.get("canonical_key")
        or item.get("title")
    )
    return str(identifier or "").strip()


def _merge_fragments(*parts: str) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for part in parts:
        value = str(part or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
    return " | ".join(values)


def _find_support_value(support_summary: str, key: str, default: str) -> str:
    marker = f"{key}="
    for segment in str(support_summary or "").split("|"):
        value = segment.strip()
        if value.startswith(marker):
            extracted = value[len(marker) :].strip()
            if extracted:
                return extracted
    return default


def _stronger_confidence(*values: str) -> str:
    strongest = "low"
    rank = _CONFIDENCE_RANKS[strongest]
    for value in values:
        candidate = str(value or "").strip().lower()
        if candidate not in _CONFIDENCE_RANKS:
            continue
        candidate_rank = _CONFIDENCE_RANKS[candidate]
        if candidate_rank > rank:
            strongest = candidate
            rank = candidate_rank
    return strongest


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
