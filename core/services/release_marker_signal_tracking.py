from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_chronicle_consolidation_signals,
    list_runtime_meaning_significance_signals,
    list_runtime_metabolism_state_signals,
    list_runtime_relation_continuity_signals,
    list_runtime_release_marker_signals,
    list_runtime_self_narrative_continuity_signals,
    list_runtime_temperament_tendency_signals,
    list_runtime_witness_signals,
    supersede_runtime_release_marker_signals_for_domain,
    update_runtime_release_marker_signal_status,
    upsert_runtime_release_marker_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_release_marker_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_release_marker_signals(
        signals=_extract_release_marker_candidates(run_id=run_id),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded release-marker signals."
            if items
            else "No bounded release-marker signal warranted tracking."
        ),
    }


def refresh_runtime_release_marker_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_release_marker_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_release_marker_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded release-marker inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "release_marker_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_release_marker_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_release_marker_signal_statuses()
    items = list_runtime_release_marker_signals(limit=max(limit, 1))
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
        "canonical_delete_state": "not-canonical-deletion",
        "self_erasure_state": "not-self-erasure",
        "selective_forgetting_state": "not-selective-forgetting-execution",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active release support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("release_state") or "none"),
            "current_direction": str((latest or {}).get("release_direction") or "none"),
            "current_weight": str((latest or {}).get("release_weight") or "low"),
            "current_confidence": str((latest or {}).get("release_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_delete_state": "not-canonical-deletion",
            "self_erasure_state": "not-self-erasure",
            "selective_forgetting_state": "not-selective-forgetting-execution",
        },
    }


def _extract_release_marker_candidates(*, run_id: str) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for item in list_runtime_metabolism_state_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["metabolism"] = item

    for item in list_runtime_witness_signals(limit=18):
        if str(item.get("status") or "") not in {"carried", "fading"}:
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
        witness = snapshot.get("witness")
        meaning = snapshot.get("meaning")
        temperament = snapshot.get("temperament")
        self_narrative = snapshot.get("self_narrative")
        chronicle = snapshot.get("chronicle")
        relation_continuity = snapshot.get("relation_continuity")
        if metabolism is None:
            continue
        if _find_support_value(str(metabolism.get("support_summary") or ""), "metabolism-state", "none") not in {
            "releasing",
            "metabolizing",
        }:
            continue
        lifecycle_items = [
            item for item in [witness, meaning, temperament, self_narrative, chronicle, relation_continuity] if item is not None
        ]
        if not lifecycle_items:
            continue
        lifecycle_release_count = sum(
            1
            for item in lifecycle_items
            if str(item.get("status") or "") in {"fading", "softening", "stale"}
        )
        if lifecycle_release_count == 0:
            continue
        candidates.append(
            _build_candidate(
                domain_key=domain_key,
                metabolism=metabolism,
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
    witness: dict[str, object] | None,
    meaning: dict[str, object] | None,
    temperament: dict[str, object] | None,
    self_narrative: dict[str, object] | None,
    chronicle: dict[str, object] | None,
    relation_continuity: dict[str, object] | None,
) -> dict[str, object]:
    items = [item for item in [metabolism, witness, meaning, temperament, self_narrative, chronicle, relation_continuity] if item is not None]
    lifecycle_statuses = [str(item.get("status") or "") for item in items]
    fading_count = sum(1 for status in lifecycle_statuses if status == "fading")
    softening_count = sum(1 for status in lifecycle_statuses if status == "softening")
    stale_count = sum(1 for status in lifecycle_statuses if status == "stale")
    release_state = _derive_release_state(
        metabolism_state=_find_support_value(str(metabolism.get("support_summary") or ""), "metabolism-state", "metabolizing"),
        witness_status=str((witness or {}).get("status") or ""),
        fading_count=fading_count,
        softening_count=softening_count,
        stale_count=stale_count,
    )
    release_direction = _derive_release_direction(
        release_state=release_state,
        witness_status=str((witness or {}).get("status") or ""),
        stale_count=stale_count,
    )
    release_weight = _derive_release_weight(
        fading_count=fading_count,
        softening_count=softening_count,
        stale_count=stale_count,
    )
    release_confidence = _stronger_confidence(
        str((metabolism or {}).get("confidence") or "low"),
        str((witness or {}).get("witness_confidence") or (witness or {}).get("confidence") or "low"),
        str((meaning or {}).get("meaning_confidence") or (meaning or {}).get("confidence") or "low"),
        str((temperament or {}).get("temperament_confidence") or (temperament or {}).get("confidence") or "low"),
        str((self_narrative or {}).get("narrative_confidence") or (self_narrative or {}).get("confidence") or "low"),
        str((chronicle or {}).get("chronicle_confidence") or (chronicle or {}).get("confidence") or "low"),
        str((relation_continuity or {}).get("continuity_confidence") or (relation_continuity or {}).get("confidence") or "low"),
    )
    source_anchor = _merge_fragments(
        _anchor(metabolism),
        _anchor(witness),
        _anchor(meaning),
        _anchor(temperament),
        _anchor(self_narrative),
        _anchor(chronicle),
        _anchor(relation_continuity),
    )
    evidence_summary = _merge_fragments(
        str((metabolism or {}).get("evidence_summary") or ""),
        str((witness or {}).get("evidence_summary") or ""),
        str((meaning or {}).get("evidence_summary") or ""),
        str((temperament or {}).get("evidence_summary") or ""),
        str((self_narrative or {}).get("evidence_summary") or ""),
        str((chronicle or {}).get("evidence_summary") or ""),
        str((relation_continuity or {}).get("evidence_summary") or ""),
    )
    focus = domain_key.replace("-", " ")
    status = "active" if release_state in {"release-leaning", "release-ready"} else "softening"
    return {
        "signal_type": "release-marker",
        "canonical_key": f"release-marker:{release_state}:{domain_key}",
        "domain_key": domain_key,
        "status": status,
        "title": f"Release support: {focus}",
        "summary": f"Bounded release runtime support is observing a small letting-go direction around {focus}.",
        "rationale": (
            "A bounded release-marker signal may return only when metabolism support already reads as releasing or metabolizing and existing lifecycle substrate already shows fading, softening, or stale pressure, without becoming release execution, deletion authority, prompt authority, workflow authority, or cleanup automation."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": release_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded metabolism-state support and existing witness/chronicle/meaning/temperament/self-narrative/relation lifecycle softening or fading patterns.",
            f"release-state={release_state}",
            f"release-direction={release_direction}",
            f"release-weight={release_weight}",
            source_anchor,
        ),
        "support_count": max([int(item.get("support_count") or 1) for item in items], default=1),
        "session_count": max([int(item.get("session_count") or 1) for item in items], default=1),
        "status_reason": (
            "Bounded release support remains non-authoritative runtime observation only and is not deletion, self-erasure, or selective-forgetting execution."
        ),
        "release_state": release_state,
        "release_direction": release_direction,
        "release_weight": release_weight,
        "release_summary": _release_summary(
            focus=focus,
            release_state=release_state,
            release_direction=release_direction,
            release_weight=release_weight,
        ),
        "release_confidence": release_confidence,
        "source_anchor": source_anchor,
        "metabolism_signal_id": str(metabolism.get("signal_id") or ""),
        "witness_signal_id": str((witness or {}).get("signal_id") or ""),
        "meaning_signal_id": str((meaning or {}).get("signal_id") or ""),
        "temperament_signal_id": str((temperament or {}).get("signal_id") or ""),
        "self_narrative_signal_id": str((self_narrative or {}).get("signal_id") or ""),
        "chronicle_signal_id": str((chronicle or {}).get("signal_id") or ""),
        "relation_continuity_signal_id": str((relation_continuity or {}).get("signal_id") or ""),
        "run_id": str(metabolism.get("run_id") or ""),
    }


def _persist_release_marker_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_release_marker_signal(
            signal_id=f"release-marker-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "release-marker"),
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
        superseded_count = supersede_runtime_release_marker_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded release-marker reading for the same lifecycle domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "release_marker_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "release_marker_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "release_marker_signal.updated",
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
    release_state = _find_support_value(support_summary, "release-state", "none")
    release_direction = _find_support_value(support_summary, "release-direction", "none")
    release_weight = _find_support_value(support_summary, "release-weight", "low")
    return {
        **item,
        "release_state": release_state,
        "release_direction": release_direction,
        "release_weight": release_weight,
        "release_summary": _release_summary(
            focus=_domain_key(str(item.get("canonical_key") or "")).replace("-", " "),
            release_state=release_state,
            release_direction=release_direction,
            release_weight=release_weight,
        ),
        "release_confidence": str(item.get("confidence") or "low"),
        "source_anchor": _anchor(item),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_delete_state": "not-canonical-deletion",
        "self_erasure_state": "not-self-erasure",
        "selective_forgetting_state": "not-selective-forgetting-execution",
        "source": "/mc/runtime.release_marker_signal",
    }


def _derive_release_state(
    *,
    metabolism_state: str,
    witness_status: str,
    fading_count: int,
    softening_count: int,
    stale_count: int,
) -> str:
    if witness_status == "fading" and (stale_count >= 1 or softening_count >= 1):
        return "release-ready"
    if metabolism_state == "releasing" and (softening_count >= 1 or stale_count >= 1):
        return "release-leaning"
    return "release-emerging"


def _derive_release_direction(
    *,
    release_state: str,
    witness_status: str,
    stale_count: int,
) -> str:
    if release_state == "release-ready" and witness_status == "fading":
        return "slipping-free"
    if release_state == "release-ready":
        return "falling-away"
    if release_state == "release-leaning" and stale_count >= 2:
        return "lightening"
    if release_state == "release-leaning":
        return "loosening"
    return "softening-out"


def _derive_release_weight(
    *,
    fading_count: int,
    softening_count: int,
    stale_count: int,
) -> str:
    score = (2 * fading_count) + softening_count + stale_count
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _release_summary(
    *,
    focus: str,
    release_state: str,
    release_direction: str,
    release_weight: str,
) -> str:
    if release_state == "release-ready":
        return (
            f"The runtime lifecycle around {focus} appears ready to slip free in a bounded way, with {release_weight} release weight."
        )
    if release_state == "release-leaning":
        return (
            f"The runtime lifecycle around {focus} shows signs of loosening toward release, with {release_weight} release weight."
        )
    return (
        f"The runtime lifecycle around {focus} appears to be softening out toward {release_direction}, with {release_weight} release weight."
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
