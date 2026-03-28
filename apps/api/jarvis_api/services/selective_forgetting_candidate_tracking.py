from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_chronicle_consolidation_signals,
    list_runtime_consolidation_target_signals,
    list_runtime_meaning_significance_signals,
    list_runtime_metabolism_state_signals,
    list_runtime_relation_continuity_signals,
    list_runtime_release_marker_signals,
    list_runtime_selective_forgetting_candidates,
    list_runtime_self_narrative_continuity_signals,
    list_runtime_temperament_tendency_signals,
    list_runtime_witness_signals,
    supersede_runtime_selective_forgetting_candidates_for_domain,
    update_runtime_selective_forgetting_candidate_status,
    upsert_runtime_selective_forgetting_candidate,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_selective_forgetting_candidates_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_selective_forgetting_candidates(
        signals=_extract_selective_forgetting_candidates(run_id=run_id),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded selective-forgetting candidates."
            if items
            else "No bounded selective-forgetting candidate warranted tracking."
        ),
    }


def refresh_runtime_selective_forgetting_candidate_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_selective_forgetting_candidates(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_selective_forgetting_candidate_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded selective-forgetting candidate inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "selective_forgetting_candidate.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_selective_forgetting_candidate_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_selective_forgetting_candidate_statuses()
    items = list_runtime_selective_forgetting_candidates(limit=max(limit, 1))
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
        "canonical_delete_state": "not-deletion",
        "self_erasure_state": "not-self-erasure",
        "selective_forgetting_state": "not-selective-forgetting-execution",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active selective-forgetting candidate"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("forgetting_candidate_state") or "none"),
            "current_reason": str((latest or {}).get("forgetting_candidate_reason") or "none"),
            "current_weight": str((latest or {}).get("forgetting_candidate_weight") or "low"),
            "current_confidence": str((latest or {}).get("forgetting_candidate_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_delete_state": "not-deletion",
            "self_erasure_state": "not-self-erasure",
            "selective_forgetting_state": "not-selective-forgetting-execution",
        },
    }


def _extract_selective_forgetting_candidates(*, run_id: str) -> list[dict[str, object]]:
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
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["release_marker"] = item

    for item in list_runtime_consolidation_target_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["consolidation_target"] = item

    for item in list_runtime_witness_signals(limit=18):
        if str(item.get("status") or "") not in {"fading", "carried"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["witness"] = item

    for item in list_runtime_meaning_significance_signals(limit=18):
        if str(item.get("status") or "") not in {"softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["meaning"] = item

    for item in list_runtime_temperament_tendency_signals(limit=18):
        if str(item.get("status") or "") not in {"softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["temperament"] = item

    for item in list_runtime_self_narrative_continuity_signals(limit=18):
        if str(item.get("status") or "") not in {"softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["self_narrative"] = item

    for item in list_runtime_chronicle_consolidation_signals(limit=18):
        if str(item.get("status") or "") not in {"softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["chronicle"] = item

    for item in list_runtime_relation_continuity_signals(limit=18):
        if str(item.get("status") or "") not in {"softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["relation_continuity"] = item

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        metabolism = snapshot.get("metabolism")
        release_marker = snapshot.get("release_marker")
        consolidation_target = snapshot.get("consolidation_target")
        witness = snapshot.get("witness")
        meaning = snapshot.get("meaning")
        temperament = snapshot.get("temperament")
        self_narrative = snapshot.get("self_narrative")
        chronicle = snapshot.get("chronicle")
        relation_continuity = snapshot.get("relation_continuity")
        if metabolism is None or release_marker is None:
            continue
        if consolidation_target is not None:
            continue
        metabolism_state = _find_support_value(str(metabolism.get("support_summary") or ""), "metabolism-state", "none")
        if metabolism_state not in {"releasing", "metabolizing"}:
            continue
        release_state = _find_support_value(str(release_marker.get("support_summary") or ""), "release-state", "none")
        if release_state not in {"release-leaning", "release-ready"}:
            continue
        lifecycle_items = [
            item for item in [witness, meaning, temperament, self_narrative, chronicle, relation_continuity] if item is not None
        ]
        if not lifecycle_items:
            continue
        if not any(str(item.get("status") or "") in {"fading", "softening", "stale"} for item in lifecycle_items):
            continue
        candidates.append(
            _build_candidate(
                domain_key=domain_key,
                metabolism=metabolism,
                release_marker=release_marker,
                witness=witness,
                meaning=meaning,
                temperament=temperament,
                self_narrative=self_narrative,
                chronicle=chronicle,
                relation_continuity=relation_continuity,
            )
        )
    return candidates[:4]


def _build_candidate(
    *,
    domain_key: str,
    metabolism: dict[str, object],
    release_marker: dict[str, object],
    witness: dict[str, object] | None,
    meaning: dict[str, object] | None,
    temperament: dict[str, object] | None,
    self_narrative: dict[str, object] | None,
    chronicle: dict[str, object] | None,
    relation_continuity: dict[str, object] | None,
) -> dict[str, object]:
    items = [item for item in [metabolism, release_marker, witness, meaning, temperament, self_narrative, chronicle, relation_continuity] if item is not None]
    statuses = [str(item.get("status") or "") for item in items]
    fading_count = sum(1 for status in statuses if status == "fading")
    softening_count = sum(1 for status in statuses if status == "softening")
    stale_count = sum(1 for status in statuses if status == "stale")
    witness_status = str((witness or {}).get("status") or "")
    release_state = _find_support_value(str(release_marker.get("support_summary") or ""), "release-state", "release-emerging")
    forgetting_candidate_state = _derive_candidate_state(
        release_state=release_state,
        witness_status=witness_status,
        fading_count=fading_count,
        softening_count=softening_count,
        stale_count=stale_count,
    )
    forgetting_candidate_reason = _derive_candidate_reason(
        release_state=release_state,
        witness_status=witness_status,
        stale_count=stale_count,
    )
    forgetting_candidate_weight = _derive_candidate_weight(
        fading_count=fading_count,
        softening_count=softening_count,
        stale_count=stale_count,
        release_state=release_state,
    )
    forgetting_candidate_confidence = _stronger_confidence(
        str((metabolism or {}).get("confidence") or "low"),
        str((release_marker or {}).get("release_confidence") or (release_marker or {}).get("confidence") or "low"),
        str((witness or {}).get("witness_confidence") or (witness or {}).get("confidence") or "low"),
        str((meaning or {}).get("meaning_confidence") or (meaning or {}).get("confidence") or "low"),
        str((temperament or {}).get("temperament_confidence") or (temperament or {}).get("confidence") or "low"),
        str((self_narrative or {}).get("narrative_confidence") or (self_narrative or {}).get("confidence") or "low"),
        str((chronicle or {}).get("chronicle_confidence") or (chronicle or {}).get("confidence") or "low"),
        str((relation_continuity or {}).get("continuity_confidence") or (relation_continuity or {}).get("confidence") or "low"),
    )
    source_anchor = _merge_fragments(
        _anchor(metabolism),
        _anchor(release_marker),
        _anchor(witness),
        _anchor(meaning),
        _anchor(temperament),
        _anchor(self_narrative),
        _anchor(chronicle),
        _anchor(relation_continuity),
    )
    evidence_summary = _merge_fragments(
        str((metabolism or {}).get("evidence_summary") or ""),
        str((release_marker or {}).get("evidence_summary") or ""),
        str((witness or {}).get("evidence_summary") or ""),
        str((meaning or {}).get("evidence_summary") or ""),
        str((temperament or {}).get("evidence_summary") or ""),
        str((self_narrative or {}).get("evidence_summary") or ""),
        str((chronicle or {}).get("evidence_summary") or ""),
        str((relation_continuity or {}).get("evidence_summary") or ""),
    )
    focus = domain_key.replace("-", " ")
    status = "active" if forgetting_candidate_state in {"candidate-emerging", "candidate-leaning"} else "softening"
    return {
        "signal_type": "selective-forgetting-candidate",
        "canonical_key": f"selective-forgetting-candidate:{forgetting_candidate_state}:{domain_key}",
        "domain_key": domain_key,
        "status": status,
        "title": f"Forgetting candidate support: {focus}",
        "summary": f"Bounded selective-forgetting runtime support is observing a small candidate around {focus}.",
        "rationale": (
            "A bounded selective-forgetting candidate may return only when metabolism already reads as releasing or metabolizing, release-marker support is already present, and no strong consolidation target remains for the same domain, without becoming forgetting execution, deletion authority, prompt authority, workflow authority, or cleanup automation."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": forgetting_candidate_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded metabolism/release support plus existing witness/chronicle/meaning/temperament/self-narrative/relation lifecycle weakening patterns, with no strong consolidation target for the same domain.",
            f"forgetting-candidate-state={forgetting_candidate_state}",
            f"forgetting-candidate-reason={forgetting_candidate_reason}",
            f"forgetting-candidate-weight={forgetting_candidate_weight}",
            source_anchor,
        ),
        "support_count": max([int(item.get("support_count") or 1) for item in items], default=1),
        "session_count": max([int(item.get("session_count") or 1) for item in items], default=1),
        "status_reason": (
            "Bounded selective-forgetting candidate support remains non-authoritative runtime observation only and is not deletion, self-erasure, or selective-forgetting execution."
        ),
        "forgetting_candidate_state": forgetting_candidate_state,
        "forgetting_candidate_reason": forgetting_candidate_reason,
        "forgetting_candidate_weight": forgetting_candidate_weight,
        "forgetting_candidate_summary": _candidate_summary(
            focus=focus,
            candidate_state=forgetting_candidate_state,
            candidate_reason=forgetting_candidate_reason,
            candidate_weight=forgetting_candidate_weight,
        ),
        "forgetting_candidate_confidence": forgetting_candidate_confidence,
        "source_anchor": source_anchor,
        "metabolism_signal_id": str((metabolism or {}).get("signal_id") or ""),
        "release_marker_signal_id": str((release_marker or {}).get("signal_id") or ""),
        "witness_signal_id": str((witness or {}).get("signal_id") or ""),
        "meaning_signal_id": str((meaning or {}).get("signal_id") or ""),
        "temperament_signal_id": str((temperament or {}).get("signal_id") or ""),
        "self_narrative_signal_id": str((self_narrative or {}).get("signal_id") or ""),
        "chronicle_signal_id": str((chronicle or {}).get("signal_id") or ""),
        "relation_continuity_signal_id": str((relation_continuity or {}).get("signal_id") or ""),
        "run_id": str((metabolism or {}).get("run_id") or ""),
    }


def _persist_selective_forgetting_candidates(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_selective_forgetting_candidate(
            signal_id=f"selective-forgetting-candidate-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "selective-forgetting-candidate"),
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
        superseded_count = supersede_runtime_selective_forgetting_candidates_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded selective-forgetting candidate reading for the same lifecycle domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "selective_forgetting_candidate.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "selective_forgetting_candidate.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "selective_forgetting_candidate.updated",
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
    candidate_state = _find_support_value(support_summary, "forgetting-candidate-state", "none")
    candidate_reason = _find_support_value(support_summary, "forgetting-candidate-reason", "none")
    candidate_weight = _find_support_value(support_summary, "forgetting-candidate-weight", "low")
    return {
        **item,
        "forgetting_candidate_state": candidate_state,
        "forgetting_candidate_reason": candidate_reason,
        "forgetting_candidate_weight": candidate_weight,
        "forgetting_candidate_summary": _candidate_summary(
            focus=_domain_key(str(item.get("canonical_key") or "")).replace("-", " "),
            candidate_state=candidate_state,
            candidate_reason=candidate_reason,
            candidate_weight=candidate_weight,
        ),
        "forgetting_candidate_confidence": str(item.get("confidence") or "low"),
        "source_anchor": _anchor(item),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_delete_state": "not-deletion",
        "self_erasure_state": "not-self-erasure",
        "selective_forgetting_state": "not-selective-forgetting-execution",
        "source": "/mc/runtime.selective_forgetting_candidate",
    }


def _derive_candidate_state(
    *,
    release_state: str,
    witness_status: str,
    fading_count: int,
    softening_count: int,
    stale_count: int,
) -> str:
    if release_state == "release-ready" and (witness_status == "fading" or stale_count >= 2):
        return "candidate-ready"
    if release_state == "release-leaning" or fading_count >= 1 or softening_count >= 2:
        return "candidate-leaning"
    return "candidate-emerging"


def _derive_candidate_reason(
    *,
    release_state: str,
    witness_status: str,
    stale_count: int,
) -> str:
    if witness_status == "fading":
        return "witness-fading"
    if stale_count >= 2:
        return "carried-weight-thinned"
    if release_state == "release-ready":
        return "release-direction-held"
    return "support-softening"


def _derive_candidate_weight(
    *,
    fading_count: int,
    softening_count: int,
    stale_count: int,
    release_state: str,
) -> str:
    score = (2 * fading_count) + softening_count + stale_count + (1 if release_state == "release-ready" else 0)
    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def _candidate_summary(
    *,
    focus: str,
    candidate_state: str,
    candidate_reason: str,
    candidate_weight: str,
) -> str:
    if candidate_state == "candidate-ready":
        return (
            f"The runtime around {focus} appears ready to stop being actively carried, with {candidate_weight} candidate weight."
        )
    if candidate_state == "candidate-leaning":
        return (
            f"The runtime around {focus} shows signs of becoming a selective-forgetting candidate because {candidate_reason}, with {candidate_weight} candidate weight."
        )
    return (
        f"The runtime around {focus} appears to be drifting toward reduced carry-forward because {candidate_reason}, with {candidate_weight} candidate weight."
    )


def _domain_key(canonical_key: str) -> str:
    value = str(canonical_key or "").strip()
    if not value:
        return ""
    return value.rsplit(":", 1)[-1].strip()


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    identifier = item.get("signal_id") or item.get("canonical_key") or item.get("title")
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
