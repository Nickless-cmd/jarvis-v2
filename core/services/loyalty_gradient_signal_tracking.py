from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_attachment_topology_signals,
    list_runtime_chronicle_consolidation_briefs,
    list_runtime_loyalty_gradient_signals,
    list_runtime_meaning_significance_signals,
    list_runtime_metabolism_state_signals,
    list_runtime_relation_continuity_signals,
    list_runtime_selective_forgetting_candidates,
    list_runtime_witness_signals,
    supersede_runtime_loyalty_gradient_signals_for_domain,
    update_runtime_loyalty_gradient_signal_status,
    upsert_runtime_loyalty_gradient_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}
_WEIGHT_RANKS = {"low": 0, "medium": 1, "high": 2}


def track_runtime_loyalty_gradient_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    items = _persist_loyalty_gradient_signals(
        signals=_extract_loyalty_gradient_candidates(run_id=run_id),
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded loyalty-gradient signals."
            if items
            else "No bounded loyalty-gradient signal warranted tracking."
        ),
    }


def refresh_runtime_loyalty_gradient_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_loyalty_gradient_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_loyalty_gradient_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded loyalty-gradient inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "loyalty_gradient_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_loyalty_gradient_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_loyalty_gradient_signal_statuses()
    items = list_runtime_loyalty_gradient_signals(limit=max(limit, 1))
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
        "planner_priority_state": "not-planner-priority",
        "canonical_preference_state": "not-canonical-preference-truth",
        "prompt_inclusion_state": "not-prompt-included",
        "workflow_bridge_state": "not-workflow-bridge",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active loyalty-gradient support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("gradient_state") or "none"),
            "current_focus": str((latest or {}).get("gradient_focus") or "none"),
            "current_rank": int((latest or {}).get("gradient_rank") or 0),
            "current_weight": str((latest or {}).get("gradient_weight") or "low"),
            "current_confidence": str((latest or {}).get("gradient_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_priority_state": "not-planner-priority",
            "canonical_preference_state": "not-canonical-preference-truth",
            "prompt_inclusion_state": "not-prompt-included",
            "workflow_bridge_state": "not-workflow-bridge",
        },
    }


def _extract_loyalty_gradient_candidates(*, run_id: str) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for item in list_runtime_attachment_topology_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["attachment_topology"] = item

    for item in list_runtime_relation_continuity_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["relation_continuity"] = item

    for item in list_runtime_meaning_significance_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["meaning"] = item

    for item in list_runtime_witness_signals(limit=18):
        if str(item.get("status") or "") not in {"fresh", "carried", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["witness"] = item

    for item in list_runtime_chronicle_consolidation_briefs(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["chronicle_brief"] = item

    for item in list_runtime_metabolism_state_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["metabolism"] = item

    for item in list_runtime_selective_forgetting_candidates(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["forgetting_candidate"] = item

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        attachment_topology = snapshot.get("attachment_topology")
        if attachment_topology is None:
            continue
        relation_continuity = snapshot.get("relation_continuity")
        meaning = snapshot.get("meaning")
        witness = snapshot.get("witness")
        chronicle_brief = snapshot.get("chronicle_brief")
        metabolism = snapshot.get("metabolism")
        forgetting_candidate = snapshot.get("forgetting_candidate")
        if relation_continuity is None and meaning is None and witness is None and chronicle_brief is None and metabolism is None:
            continue
        candidates.append(
            _build_candidate(
                domain_key=domain_key,
                attachment_topology=attachment_topology,
                relation_continuity=relation_continuity,
                meaning=meaning,
                witness=witness,
                chronicle_brief=chronicle_brief,
                metabolism=metabolism,
                forgetting_candidate=forgetting_candidate,
            )
        )

    candidates.sort(key=lambda item: int(item.get("_gradient_score") or 0), reverse=True)
    for index, candidate in enumerate(candidates[:4], start=1):
        candidate["gradient_rank"] = index
    return candidates[:4]


def _build_candidate(
    *,
    domain_key: str,
    attachment_topology: dict[str, object],
    relation_continuity: dict[str, object] | None,
    meaning: dict[str, object] | None,
    witness: dict[str, object] | None,
    chronicle_brief: dict[str, object] | None,
    metabolism: dict[str, object] | None,
    forgetting_candidate: dict[str, object] | None,
) -> dict[str, object]:
    attachment_weight = str(
        attachment_topology.get("attachment_weight")
        or _find_support_value(str(attachment_topology.get("support_summary") or ""), "attachment-weight", "low")
    )
    attachment_state = str(
        attachment_topology.get("attachment_state")
        or _find_support_value(str(attachment_topology.get("support_summary") or ""), "attachment-state", "attachment-emerging")
    )
    relation_weight = str(
        (relation_continuity or {}).get("continuity_weight")
        or _find_support_value(str((relation_continuity or {}).get("support_summary") or ""), "continuity-weight", "low")
    )
    meaning_weight = str(
        (meaning or {}).get("meaning_weight")
        or _find_support_value(str((meaning or {}).get("support_summary") or ""), "meaning-weight", "low")
    )
    witness_status = str((witness or {}).get("status") or "")
    witness_persistence = str(
        (witness or {}).get("persistence_state")
        or _find_support_value(str((witness or {}).get("support_summary") or ""), "persistence-state", "none")
    )
    brief_weight = _find_support_value(str((chronicle_brief or {}).get("support_summary") or ""), "brief-weight", "low")
    metabolism_state = str(
        (metabolism or {}).get("metabolism_state")
        or _find_support_value(str((metabolism or {}).get("support_summary") or ""), "metabolism-state", "none")
    )
    metabolism_weight = str(
        (metabolism or {}).get("metabolism_weight")
        or _find_support_value(str((metabolism or {}).get("support_summary") or ""), "metabolism-weight", "low")
    )
    forgetting_state = str(
        (forgetting_candidate or {}).get("forgetting_candidate_state")
        or _find_support_value(str((forgetting_candidate or {}).get("support_summary") or ""), "forgetting-candidate-state", "none")
    )

    gradient_score = _derive_gradient_score(
        attachment_weight=attachment_weight,
        attachment_state=attachment_state,
        relation_weight=relation_weight,
        meaning_weight=meaning_weight,
        witness_status=witness_status,
        witness_persistence=witness_persistence,
        brief_weight=brief_weight,
        metabolism_state=metabolism_state,
        metabolism_weight=metabolism_weight,
        forgetting_state=forgetting_state,
    )
    gradient_weight = _score_to_weight(gradient_score)
    gradient_state = _derive_gradient_state(
        attachment_state=attachment_state,
        gradient_weight=gradient_weight,
        witness_status=witness_status,
        forgetting_state=forgetting_state,
    )
    gradient_focus = _humanize_focus(domain_key)
    gradient_confidence = _stronger_confidence(
        str(attachment_topology.get("attachment_confidence") or attachment_topology.get("confidence") or "low"),
        str((relation_continuity or {}).get("continuity_confidence") or (relation_continuity or {}).get("confidence") or "low"),
        str((meaning or {}).get("meaning_confidence") or (meaning or {}).get("confidence") or "low"),
        str((witness or {}).get("witness_confidence") or (witness or {}).get("confidence") or "low"),
        str((chronicle_brief or {}).get("brief_confidence") or (chronicle_brief or {}).get("confidence") or "low"),
        str((metabolism or {}).get("metabolism_confidence") or (metabolism or {}).get("confidence") or "low"),
    )
    source_anchor = _merge_fragments(
        _anchor(attachment_topology),
        _anchor(relation_continuity),
        _anchor(meaning),
        _anchor(witness),
        _anchor(chronicle_brief),
        _anchor(metabolism),
        _anchor(forgetting_candidate),
    )
    evidence_summary = _merge_fragments(
        str(attachment_topology.get("evidence_summary") or ""),
        str((relation_continuity or {}).get("evidence_summary") or ""),
        str((meaning or {}).get("evidence_summary") or ""),
        str((witness or {}).get("evidence_summary") or ""),
        str((chronicle_brief or {}).get("evidence_summary") or ""),
        str((metabolism or {}).get("evidence_summary") or ""),
        str((forgetting_candidate or {}).get("evidence_summary") or ""),
    )
    gradient_rank = 0
    gradient_summary = _gradient_summary(
        focus=gradient_focus,
        gradient_state=gradient_state,
        gradient_weight=gradient_weight,
        forgetting_candidate=forgetting_candidate,
    )
    support_summary = _merge_fragments(
        f"gradient-state={gradient_state}",
        f"gradient-focus={domain_key}",
        f"gradient-rank={gradient_rank}",
        f"gradient-weight={gradient_weight}",
        f"gradient-confidence={gradient_confidence}",
        f"source-anchor={source_anchor}" if source_anchor else "",
    )
    status = "active" if gradient_weight in {"medium", "high"} and gradient_state != "loyalty-peripheral" else "softening"
    source_items = [
        item
        for item in [
            attachment_topology,
            relation_continuity,
            meaning,
            witness,
            chronicle_brief,
            metabolism,
        ]
        if item is not None
    ]
    support_count = max([int(item.get("support_count") or 1) for item in source_items], default=1)
    session_count = max([int(item.get("session_count") or 1) for item in source_items], default=1)
    return {
        "signal_type": "loyalty-gradient",
        "canonical_key": f"loyalty-gradient:{gradient_state}:{domain_key}",
        "status": status,
        "title": f"Loyalty gradient: {gradient_focus}",
        "summary": gradient_summary,
        "rationale": (
            "Bounded loyalty-gradient support compares existing attachment-topology threads against their already-visible runtime substrate, without becoming planner authority, canonical preference truth, prompt inclusion, or workflow bridge."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": gradient_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": support_summary,
        "status_reason": (
            "Bounded loyalty-gradient support remains descriptive runtime weighting only and is not planner priority, canonical preference truth, prompt inclusion, or workflow authority."
        ),
        "run_id": str((metabolism or {}).get("run_id") or attachment_topology.get("run_id") or ""),
        "session_id": str((attachment_topology or {}).get("session_id") or ""),
        "support_count": support_count,
        "session_count": session_count,
        "gradient_rank": gradient_rank,
        "_gradient_score": gradient_score,
    }


def _persist_loyalty_gradient_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        rank = int(signal.get("gradient_rank") or 0)
        support_summary = _merge_fragments(
            f"gradient-state={_find_support_value(str(signal.get('support_summary') or ''), 'gradient-state', 'loyalty-emerging')}",
            f"gradient-focus={_find_support_value(str(signal.get('support_summary') or ''), 'gradient-focus', '')}",
            f"gradient-rank={rank}",
            f"gradient-weight={_find_support_value(str(signal.get('support_summary') or ''), 'gradient-weight', 'low')}",
            f"gradient-confidence={_find_support_value(str(signal.get('support_summary') or ''), 'gradient-confidence', str(signal.get('confidence') or 'low'))}",
            f"source-anchor={_find_support_value(str(signal.get('support_summary') or ''), 'source-anchor', '')}",
        )
        created = upsert_runtime_loyalty_gradient_signal(
            signal_id=f"loyalty-gradient-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "loyalty-gradient"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
            title=str(signal.get("title") or "Loyalty gradient"),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "runtime-derived-support"),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=support_summary,
            status_reason=str(signal.get("status_reason") or ""),
            run_id=str(signal.get("run_id") or run_id),
            session_id=str(signal.get("session_id") or session_id),
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
        )
        superseded = supersede_runtime_loyalty_gradient_signals_for_domain(
            domain_key=_domain_key(str(created.get("canonical_key") or "")),
            exclude_signal_id=str(created.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded loyalty-gradient signal for the same domain.",
        )
        created["superseded_count"] = superseded
        if created.get("was_created"):
            event_bus.publish(
                "loyalty_gradient_signal.created",
                {
                    "signal_id": created.get("signal_id"),
                    "signal_type": created.get("signal_type"),
                    "status": created.get("status"),
                    "summary": created.get("summary"),
                },
            )
        elif created.get("was_updated"):
            event_bus.publish(
                "loyalty_gradient_signal.updated",
                {
                    "signal_id": created.get("signal_id"),
                    "signal_type": created.get("signal_type"),
                    "status": created.get("status"),
                    "summary": created.get("summary"),
                },
            )
        persisted.append(created)
    return [_with_surface_view(item) for item in persisted]


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    support_summary = str(item.get("support_summary") or "")
    focus = _find_support_value(support_summary, "gradient-focus", _domain_key(str(item.get("canonical_key") or "")))
    summary = dict(item)
    summary["gradient_state"] = _find_support_value(support_summary, "gradient-state", "loyalty-emerging")
    summary["gradient_focus"] = _humanize_focus(focus)
    summary["gradient_rank"] = int(_find_support_value(support_summary, "gradient-rank", "0") or 0)
    summary["gradient_weight"] = _find_support_value(support_summary, "gradient-weight", "low")
    summary["gradient_confidence"] = _find_support_value(
        support_summary,
        "gradient-confidence",
        str(item.get("confidence") or "low"),
    )
    summary["gradient_summary"] = str(item.get("summary") or "")
    summary["source_anchor"] = _find_support_value(support_summary, "source-anchor", "")
    summary["authority"] = "non-authoritative"
    summary["layer_role"] = "runtime-support"
    summary["planner_priority_state"] = "not-planner-priority"
    summary["canonical_preference_state"] = "not-canonical-preference-truth"
    summary["prompt_inclusion_state"] = "not-prompt-included"
    summary["workflow_bridge_state"] = "not-workflow-bridge"
    summary["source"] = f"/mc/runtime.loyalty_gradient_signal/{item.get('signal_id') or ''}"
    return summary


def _derive_gradient_score(
    *,
    attachment_weight: str,
    attachment_state: str,
    relation_weight: str,
    meaning_weight: str,
    witness_status: str,
    witness_persistence: str,
    brief_weight: str,
    metabolism_state: str,
    metabolism_weight: str,
    forgetting_state: str,
) -> int:
    score = (_WEIGHT_RANKS.get(attachment_weight, 0) + 1) * 2
    score += _WEIGHT_RANKS.get(relation_weight, 0)
    score += _WEIGHT_RANKS.get(meaning_weight, 0)
    score += _WEIGHT_RANKS.get(brief_weight, 0)
    score += _WEIGHT_RANKS.get(metabolism_weight, 0)
    if attachment_state == "attachment-central":
        score += 2
    elif attachment_state == "attachment-held":
        score += 1
    if witness_status == "carried":
        score += 2
    elif witness_status == "fresh":
        score += 1
    if witness_persistence in {"persistent", "carried-forward"}:
        score += 1
    if metabolism_state in {"releasing", "metabolizing"}:
        score -= 1
    if forgetting_state in {"candidate-ready", "candidate-leaning"}:
        score -= 2
    return score


def _score_to_weight(score: int) -> str:
    if score >= 10:
        return "high"
    if score >= 6:
        return "medium"
    return "low"


def _derive_gradient_state(
    *,
    attachment_state: str,
    gradient_weight: str,
    witness_status: str,
    forgetting_state: str,
) -> str:
    if forgetting_state in {"candidate-ready", "candidate-leaning"} and gradient_weight == "low":
        return "loyalty-peripheral"
    if attachment_state == "attachment-central" and gradient_weight == "high" and witness_status == "carried":
        return "loyalty-central"
    if gradient_weight in {"medium", "high"}:
        return "loyalty-held"
    return "loyalty-emerging"


def _gradient_summary(
    *,
    focus: str,
    gradient_state: str,
    gradient_weight: str,
    forgetting_candidate: dict[str, object] | None,
) -> str:
    if forgetting_candidate is not None:
        return (
            f"Bounded loyalty-gradient runtime support still appears to carry {focus} with {gradient_weight} weight, "
            "but nearby release pressure keeps the thread descriptive and provisional. This is not planner priority, canonical preference truth, prompt inclusion, or workflow bridge."
        )
    if gradient_state == "loyalty-central":
        return (
            f"Bounded loyalty-gradient runtime support currently places {focus} near the center of the visible attachment gradient. "
            "This remains comparative runtime weighting only, not planner priority or canonical preference truth."
        )
    if gradient_state == "loyalty-held":
        return (
            f"Bounded loyalty-gradient runtime support appears to hold {focus} more loyally than weaker surrounding threads. "
            "This remains descriptive runtime weighting only, not prompt inclusion or workflow authority."
        )
    if gradient_state == "loyalty-peripheral":
        return (
            f"Bounded loyalty-gradient runtime support currently shows {focus} as a weaker peripheral thread. "
            "This is comparative runtime observation only, not canonical preference truth."
        )
    return (
        f"Bounded loyalty-gradient runtime support shows signs of {focus} carrying some comparative loyalty weight. "
        "This remains descriptive runtime support only, not planner priority."
    )


def _domain_key(canonical_key: str) -> str:
    normalized = canonical_key.strip()
    if not normalized:
        return ""
    return normalized.split(":")[-1].strip()


def _humanize_focus(value: str) -> str:
    return value.replace("-", " ").strip() or "unknown focus"


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    return str(item.get("source_anchor") or _find_support_value(str(item.get("support_summary") or ""), "source-anchor", ""))


def _merge_fragments(*fragments: str) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        for piece in str(fragment or "").split(" | "):
            normalized = " ".join(piece.split()).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            parts.append(normalized)
    return " | ".join(parts)


def _find_support_value(summary: str, key: str, default: str) -> str:
    prefix = f"{key}="
    for fragment in str(summary or "").split(" | "):
        normalized = fragment.strip()
        if normalized.startswith(prefix):
            return normalized[len(prefix):].strip() or default
    return default


def _stronger_confidence(*values: str) -> str:
    best = "low"
    for value in values:
        candidate = str(value or "low").strip().lower() or "low"
        if _CONFIDENCE_RANKS.get(candidate, 0) >= _CONFIDENCE_RANKS.get(best, 0):
            best = candidate
    return best


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
