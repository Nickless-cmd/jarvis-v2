"""Attachment-topology signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the attachment-topology-specific candidate derivation, weight/state scoring, and
the control-layer surface projection stay here — that is the part unique to this
signal.

This is a multi-candidate ``_for_domain`` S-family variant. Two knobs are
atypical and made explicit on the spec: the supersede is **silent** (the original
marked same-domain siblings superseded but published **no** ``.superseded`` event,
so ``publish_superseded=False``), and each candidate carries its own
``run_id``/``session_id`` (derived from the source substrate), so the thin
``track`` wrapper persists per candidate with the candidate's own attribution
rather than the turn's. The read surface uses ``item_view_fn`` +
``surface_extra_fn`` and omits ``recent_history``.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.runtime.db import (
    list_runtime_attachment_topology_signals,
    list_runtime_chronicle_consolidation_briefs,
    list_runtime_meaning_significance_signals,
    list_runtime_metabolism_state_signals,
    list_runtime_relation_continuity_signals,
    list_runtime_selective_forgetting_candidates,
    list_runtime_self_narrative_continuity_signals,
    list_runtime_temperament_tendency_signals,
    list_runtime_witness_signals,
    supersede_runtime_attachment_topology_signals_for_domain,
    update_runtime_attachment_topology_signal_status,
    upsert_runtime_attachment_topology_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}
_WEIGHT_RANKS = {"low": 0, "medium": 1, "high": 2}


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_attachment_topology_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    # Delegate upsert/supersede/event scaffolding to the framework, but persist
    # each candidate under its own run_id/session_id (the original derived those
    # from the source substrate, not the turn) and re-apply the surface view on
    # the returned items — matching the pre-migration output exactly.
    normalized_session_id = str(session_id or "").strip()
    persisted: list[dict[str, object]] = []
    for candidate in _extract_attachment_topology_candidates(run_id=run_id):
        grouped = {
            **candidate,
            "domain_key": _domain_key(str(candidate.get("canonical_key") or "")),
        }
        persisted.extend(
            _stf.persist_signals(
                _SPEC,
                signals=[grouped],
                session_id=str(candidate.get("session_id") or normalized_session_id),
                run_id=str(candidate.get("run_id") or run_id),
            )
        )
    items = [_with_surface_view(item) for item in persisted]
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded attachment-topology signals."
            if items
            else "No bounded attachment-topology signal warranted tracking."
        ),
    }


def refresh_runtime_attachment_topology_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_attachment_topology_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _extract_attachment_topology_candidates(*, run_id: str) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

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

    for item in list_runtime_self_narrative_continuity_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["self_narrative"] = item

    for item in list_runtime_temperament_tendency_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening", "stale"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["temperament"] = item

    for item in list_runtime_selective_forgetting_candidates(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["forgetting_candidate"] = item

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        relation_continuity = snapshot.get("relation_continuity")
        meaning = snapshot.get("meaning")
        witness = snapshot.get("witness")
        chronicle_brief = snapshot.get("chronicle_brief")
        metabolism = snapshot.get("metabolism")
        self_narrative = snapshot.get("self_narrative")
        temperament = snapshot.get("temperament")
        forgetting_candidate = snapshot.get("forgetting_candidate")
        if relation_continuity is None or meaning is None:
            continue
        if witness is None and chronicle_brief is None and metabolism is None:
            continue
        candidates.append(
            _build_candidate(
                domain_key=domain_key,
                relation_continuity=relation_continuity,
                meaning=meaning,
                witness=witness,
                chronicle_brief=chronicle_brief,
                metabolism=metabolism,
                self_narrative=self_narrative,
                temperament=temperament,
                forgetting_candidate=forgetting_candidate,
            )
        )
    candidates.sort(key=lambda item: _WEIGHT_RANKS.get(str(item.get("attachment_weight") or "low"), 0), reverse=True)
    return candidates[:4]


def _build_candidate(
    *,
    domain_key: str,
    relation_continuity: dict[str, object],
    meaning: dict[str, object],
    witness: dict[str, object] | None,
    chronicle_brief: dict[str, object] | None,
    metabolism: dict[str, object] | None,
    self_narrative: dict[str, object] | None,
    temperament: dict[str, object] | None,
    forgetting_candidate: dict[str, object] | None,
) -> dict[str, object]:
    items = [
        item
        for item in [
            relation_continuity,
            meaning,
            witness,
            chronicle_brief,
            metabolism,
            self_narrative,
            temperament,
        ]
        if item is not None
    ]
    support_count = max([int(item.get("support_count") or 1) for item in items], default=1)
    session_count = max([int(item.get("session_count") or 1) for item in items], default=1)
    attachment_weight = _derive_attachment_weight(
        relation_weight=str(relation_continuity.get("continuity_weight") or _find_support_value(str(relation_continuity.get("support_summary") or ""), "continuity-weight", "medium")),
        meaning_weight=str(meaning.get("meaning_weight") or _find_support_value(str(meaning.get("support_summary") or ""), "meaning-weight", "medium")),
        witness_status=str((witness or {}).get("status") or ""),
        witness_persistence=str((witness or {}).get("persistence_state") or _find_support_value(str((witness or {}).get("support_summary") or ""), "persistence-state", "none")),
        brief_weight=_find_support_value(str((chronicle_brief or {}).get("support_summary") or ""), "brief-weight", "medium"),
        metabolism_weight=str((metabolism or {}).get("metabolism_weight") or _find_support_value(str((metabolism or {}).get("support_summary") or ""), "metabolism-weight", "medium")),
        narrative_weight=str((self_narrative or {}).get("narrative_weight") or _find_support_value(str((self_narrative or {}).get("support_summary") or ""), "narrative-weight", "medium")),
        temperament_weight=str((temperament or {}).get("temperament_weight") or _find_support_value(str((temperament or {}).get("support_summary") or ""), "temperament-weight", "medium")),
        forgetting_state=str((forgetting_candidate or {}).get("forgetting_candidate_state") or _find_support_value(str((forgetting_candidate or {}).get("support_summary") or ""), "forgetting-candidate-state", "none")),
    )
    attachment_state = _derive_attachment_state(
        weight=attachment_weight,
        witness_status=str((witness or {}).get("status") or ""),
        metabolism_state=str((metabolism or {}).get("metabolism_state") or _find_support_value(str((metabolism or {}).get("support_summary") or ""), "metabolism-state", "none")),
    )
    attachment_focus = _humanize_focus(domain_key)
    attachment_confidence = _stronger_confidence(
        str(relation_continuity.get("continuity_confidence") or relation_continuity.get("confidence") or "low"),
        str(meaning.get("meaning_confidence") or meaning.get("confidence") or "low"),
        str((witness or {}).get("witness_confidence") or (witness or {}).get("confidence") or "low"),
        str((chronicle_brief or {}).get("brief_confidence") or (chronicle_brief or {}).get("confidence") or "low"),
        str((metabolism or {}).get("metabolism_confidence") or (metabolism or {}).get("confidence") or "low"),
        str((self_narrative or {}).get("narrative_confidence") or (self_narrative or {}).get("confidence") or "low"),
    )
    attachment_summary = _attachment_summary(
        focus=attachment_focus,
        attachment_state=attachment_state,
        attachment_weight=attachment_weight,
        forgetting_candidate=forgetting_candidate,
    )
    source_anchor = _merge_fragments(
        _anchor(relation_continuity),
        _anchor(meaning),
        _anchor(witness),
        _anchor(chronicle_brief),
        _anchor(metabolism),
        _anchor(self_narrative),
        _anchor(temperament),
    )
    evidence_summary = _merge_fragments(
        str(relation_continuity.get("evidence_summary") or ""),
        str(meaning.get("evidence_summary") or ""),
        str((witness or {}).get("evidence_summary") or ""),
        str((chronicle_brief or {}).get("evidence_summary") or ""),
        str((metabolism or {}).get("evidence_summary") or ""),
        str((self_narrative or {}).get("evidence_summary") or ""),
        str((temperament or {}).get("evidence_summary") or ""),
    )
    support_summary = _merge_fragments(
        f"attachment-state={attachment_state}",
        f"attachment-focus={domain_key}",
        f"attachment-weight={attachment_weight}",
        f"attachment-confidence={attachment_confidence}",
        f"source-anchor={source_anchor}" if source_anchor else "",
    )
    return {
        "signal_type": "attachment-topology",
        "canonical_key": f"attachment-topology:{attachment_state}:{domain_key}",
        "status": "active" if attachment_state in {"attachment-held", "attachment-central"} else "softening",
        "title": f"Attachment topology: {attachment_focus}",
        "summary": attachment_summary,
        "rationale": "Bounded attachment-topology support synthesized from relation continuity, meaning significance, and carried runtime substrate.",
        "source_kind": "runtime-derived-support",
        "confidence": attachment_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": support_summary,
        "status_reason": "Bounded attachment-topology support remains descriptive runtime weighting only.",
        "run_id": str((metabolism or {}).get("run_id") or relation_continuity.get("run_id") or ""),
        "session_id": str((relation_continuity or {}).get("session_id") or (meaning or {}).get("session_id") or ""),
        "support_count": support_count,
        "session_count": session_count,
    }


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    support_summary = str(item.get("support_summary") or "")
    focus = _find_support_value(support_summary, "attachment-focus", _domain_key(str(item.get("canonical_key") or "")))
    summary = dict(item)
    summary["attachment_state"] = _find_support_value(support_summary, "attachment-state", "attachment-emerging")
    summary["attachment_focus"] = _humanize_focus(focus)
    summary["attachment_weight"] = _find_support_value(support_summary, "attachment-weight", "low")
    summary["attachment_confidence"] = _find_support_value(
        support_summary,
        "attachment-confidence",
        str(item.get("confidence") or "low"),
    )
    summary["attachment_summary"] = str(item.get("summary") or "")
    summary["source_anchor"] = _find_support_value(support_summary, "source-anchor", "")
    summary["authority"] = "non-authoritative"
    summary["layer_role"] = "runtime-support"
    summary["planner_priority_state"] = "not-planner-priority"
    summary["canonical_preference_state"] = "not-canonical-preference-truth"
    summary["source"] = f"/mc/runtime.attachment_topology_signal/{item.get('signal_id') or ''}"
    return summary


def _attachment_topology_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "planner_priority_state": "not-planner-priority",
        "canonical_preference_state": "not-canonical-preference-truth",
        "summary_extra": {
            "current_state": str(current.get("attachment_state") or "none"),
            "current_focus": str(current.get("attachment_focus") or "none"),
            "current_weight": str(current.get("attachment_weight") or "low"),
            "current_confidence": str(current.get("attachment_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_priority_state": "not-planner-priority",
            "canonical_preference_state": "not-canonical-preference-truth",
        },
    }


def _derive_attachment_weight(
    *,
    relation_weight: str,
    meaning_weight: str,
    witness_status: str,
    witness_persistence: str,
    brief_weight: str,
    metabolism_weight: str,
    narrative_weight: str,
    temperament_weight: str,
    forgetting_state: str,
) -> str:
    score = 0
    score += _WEIGHT_RANKS.get(relation_weight, 0) + 1
    score += _WEIGHT_RANKS.get(meaning_weight, 0) + 1
    score += _WEIGHT_RANKS.get(brief_weight, 0)
    score += _WEIGHT_RANKS.get(metabolism_weight, 0)
    score += _WEIGHT_RANKS.get(narrative_weight, 0)
    score += _WEIGHT_RANKS.get(temperament_weight, 0)
    if witness_status == "carried":
        score += 2
    elif witness_status == "fresh":
        score += 1
    if witness_persistence in {"persistent", "carried-forward"}:
        score += 2
    elif witness_persistence in {"stabilizing-over-time", "recurring"}:
        score += 1
    if forgetting_state in {"candidate-ready", "candidate-leaning"}:
        score -= 2
    if score >= 9:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def _derive_attachment_state(*, weight: str, witness_status: str, metabolism_state: str) -> str:
    if weight == "high" and witness_status == "carried" and metabolism_state in {"active-retaining", "consolidating"}:
        return "attachment-central"
    if weight in {"medium", "high"}:
        return "attachment-held"
    return "attachment-emerging"


def _attachment_summary(
    *,
    focus: str,
    attachment_state: str,
    attachment_weight: str,
    forgetting_candidate: dict[str, object] | None,
) -> str:
    if forgetting_candidate is not None:
        return (
            f"Bounded attachment-topology runtime support still appears to hold {focus} with {attachment_weight} weight, "
            "but the thread also shows nearby release pressure. This remains descriptive runtime support, not planner priority."
        )
    if attachment_state == "attachment-central":
        return (
            f"Bounded attachment-topology runtime support appears to hold {focus} as a more central carried thread. "
            "This is weighting support only, not canonical preference truth."
        )
    if attachment_state == "attachment-held":
        return (
            f"Bounded attachment-topology runtime support appears to keep {focus} more strongly held than surrounding threads. "
            "This remains descriptive runtime support, not planner priority."
        )
    return (
        f"Bounded attachment-topology runtime support shows signs of {focus} carrying some relational weight. "
        "This remains descriptive runtime support, not canonical preference truth."
    )


def _domain_key(canonical_key: str) -> str:
    normalized = canonical_key.strip()
    if not normalized:
        return ""
    return normalized.split(":")[-1].strip()


def _humanize_focus(value: str) -> str:
    normalized = str(value or "").strip().replace("-", " ")
    return normalized or "unnamed thread"


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    canonical_key = str(item.get("canonical_key") or "").strip()
    title = str(item.get("title") or "").strip()
    return canonical_key or title


def _find_support_value(summary: str, key: str, default: str = "") -> str:
    for part in summary.split("|"):
        chunk = part.strip()
        if not chunk or "=" not in chunk:
            continue
        left, right = chunk.split("=", 1)
        if left.strip() == key:
            value = right.strip()
            return value or default
    return default


def _merge_fragments(*parts: str) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for part in parts:
        normalized = str(part or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return " | ".join(merged[:4])


def _stronger_confidence(*values: str) -> str:
    best = "low"
    for value in values:
        normalized = str(value or "").strip().lower() or "low"
        if _CONFIDENCE_RANKS.get(normalized, 0) > _CONFIDENCE_RANKS.get(best, 0):
            best = normalized
    return best


# ── spec: multi-candidate _for_domain S-family + silent supersede + surface ────
_SPEC = SignalTrackingSpec(
    name="attachment-topology",
    slug="attachment-topology",
    signal_id_prefix="attachment-topology",
    event_prefix="attachment_topology_signal",
    default_signal_type="attachment-topology",
    list_fn=list_runtime_attachment_topology_signals,
    upsert_fn=upsert_runtime_attachment_topology_signal,
    update_status_fn=update_runtime_attachment_topology_signal_status,
    supersede_fn=supersede_runtime_attachment_topology_signals_for_domain,
    supersede_group_field="domain_key",
    supersede_group_kw="domain_key",
    extract_fn=lambda spec, ctx: _extract_attachment_topology_candidates(run_id=str(ctx.get("run_id") or "")),
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active", "softening"}),
    stale_status_reason="Marked stale after bounded attachment-topology inactivity window.",
    surface_status_order=("active", "softening", "stale", "superseded"),
    surface_active_statuses=frozenset({"active", "softening"}),
    empty_current_label="No active attachment-topology support",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_attachment_topology_surface_extra,
    omit_recent_history=True,
    publish_superseded=False,
    stale_payload_extra=("status_reason",),
)
