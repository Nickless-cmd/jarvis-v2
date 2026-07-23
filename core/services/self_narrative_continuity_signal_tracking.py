"""Self-narrative continuity signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the self-narrative-specific candidate derivation and the narrative-projection
enrichment stay here — that is the part unique to this signal.

This is a ``_for_focus`` S-family variant: supersede grouping is by ``focus_key``
and both the read surface and the persist return carry a bounded narrative
projection (``narrative_state`` / ``narrative_direction`` / ``narrative_weight`` …
plus the ``authority`` / ``layer_role`` / ``canonical_identity_state`` control keys).
The read-surface hooks are ``item_view_fn`` + ``surface_extra_fn``; the persist
return applies the 1-arg ``_with_runtime_view`` in the thin ``track`` wrapper.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.runtime.db import (
    list_runtime_chronicle_consolidation_briefs,
    list_runtime_chronicle_consolidation_proposals,
    list_runtime_meaning_significance_signals,
    list_runtime_relation_continuity_signals,
    list_runtime_self_narrative_continuity_signals,
    list_runtime_temperament_tendency_signals,
    supersede_runtime_self_narrative_continuity_signals_for_focus,
    update_runtime_self_narrative_continuity_signal_status,
    upsert_runtime_self_narrative_continuity_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}
_WEIGHT_RANKS = {"low": 0, "medium": 1, "high": 2}


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_self_narrative_continuity_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    # Delegate the upsert/supersede/event scaffolding to the framework, but keep
    # the original 1-arg runtime-view enrichment on the returned items — matching
    # the pre-migration output exactly.
    normalized_session_id = str(session_id or "").strip()
    signals = _extract_self_narrative_continuity_candidates(run_id=run_id)
    persisted = _stf.persist_signals(
        _SPEC, signals=signals, session_id=normalized_session_id, run_id=run_id
    )
    items = [_with_runtime_view(item) for item in persisted]
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded self-narrative continuity signals."
            if items
            else "No bounded self-narrative continuity signal warranted tracking."
        ),
    }


def refresh_runtime_self_narrative_continuity_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_self_narrative_continuity_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _extract_self_narrative_continuity_candidates(*, run_id: str) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for meaning_signal in list_runtime_meaning_significance_signals(limit=18):
        if str(meaning_signal.get("status") or "") not in {"active", "softening"}:
            continue
        if str(meaning_signal.get("run_id") or "") != run_id:
            continue
        focus = _focus_key(meaning_signal)
        temperament_signal = _latest_temperament_signal(run_id=run_id, focus_key=focus)
        relation_continuity = _latest_relation_continuity(run_id=run_id, focus_key=focus)
        chronicle_brief = _latest_chronicle_brief(run_id=run_id, focus_key=focus)
        chronicle_proposal = _latest_chronicle_proposal(run_id=run_id, focus_key=focus)
        if (
            temperament_signal is None
            or relation_continuity is None
            or (chronicle_brief is None and chronicle_proposal is None)
        ):
            continue
        candidates.append(
            _build_candidate(
                focus=focus,
                meaning_signal=meaning_signal,
                temperament_signal=temperament_signal,
                relation_continuity=relation_continuity,
                chronicle_brief=chronicle_brief,
                chronicle_proposal=chronicle_proposal,
            )
        )
    return candidates[:4]


def _build_candidate(
    *,
    focus: str,
    meaning_signal: dict[str, object],
    temperament_signal: dict[str, object],
    relation_continuity: dict[str, object],
    chronicle_brief: dict[str, object] | None,
    chronicle_proposal: dict[str, object] | None,
) -> dict[str, object]:
    meaning_type = _value(meaning_signal.get("meaning_type"), default="carried-significance")
    meaning_weight = _value(meaning_signal.get("meaning_weight"), default="low")
    temperament_type = _value(temperament_signal.get("temperament_type"), default="steadiness")
    temperament_weight = _value(temperament_signal.get("temperament_weight"), default="low")
    continuity_state = _value(relation_continuity.get("continuity_state"), default="carried-alignment")
    continuity_weight = _value(relation_continuity.get("continuity_weight"), default="low")
    proposal_weight = _value((chronicle_proposal or {}).get("proposal_weight"), default="low")
    brief_weight = _value((chronicle_brief or {}).get("brief_weight"), default="low")

    narrative_state = _derive_narrative_state(
        meaning_type=meaning_type,
        temperament_type=temperament_type,
        continuity_state=continuity_state,
    )
    narrative_direction = _derive_narrative_direction(
        meaning_type=meaning_type,
        temperament_type=temperament_type,
        has_proposal=chronicle_proposal is not None,
        continuity_state=continuity_state,
    )
    narrative_weight = _derive_narrative_weight(
        meaning_weight=meaning_weight,
        temperament_weight=temperament_weight,
        continuity_weight=continuity_weight,
        brief_weight=brief_weight,
        proposal_weight=proposal_weight,
    )
    narrative_confidence = _stronger_confidence(
        str(meaning_signal.get("meaning_confidence") or meaning_signal.get("confidence") or "low"),
        str(temperament_signal.get("temperament_confidence") or temperament_signal.get("confidence") or "low"),
        str(relation_continuity.get("continuity_confidence") or relation_continuity.get("confidence") or "low"),
        str((chronicle_brief or {}).get("brief_confidence") or (chronicle_brief or {}).get("confidence") or "low"),
        str((chronicle_proposal or {}).get("proposal_confidence") or (chronicle_proposal or {}).get("confidence") or "low"),
    )
    status = _derive_status(
        meaning_status=str(meaning_signal.get("status") or ""),
        temperament_status=str(temperament_signal.get("status") or ""),
        continuity_status=str(relation_continuity.get("status") or ""),
    )
    grounding_mode = _grounding_mode(
        has_brief=chronicle_brief is not None,
        has_proposal=chronicle_proposal is not None,
    )
    source_anchor = _merge_fragments(
        _anchor(meaning_signal),
        _anchor(temperament_signal),
        _anchor(relation_continuity),
        _anchor(chronicle_brief),
        _anchor(chronicle_proposal),
    )
    evidence_summary = _merge_fragments(
        str(meaning_signal.get("evidence_summary") or ""),
        str(temperament_signal.get("evidence_summary") or ""),
        str(relation_continuity.get("evidence_summary") or ""),
        str((chronicle_brief or {}).get("evidence_summary") or ""),
        str((chronicle_proposal or {}).get("evidence_summary") or ""),
    )
    focus_text = focus.replace("-", " ")
    return {
        "signal_type": "self-narrative-continuity",
        "canonical_key": f"self-narrative-continuity:{narrative_state}:{focus}",
        "focus_key": focus,
        "status": status,
        "title": f"Self-narrative support: {focus_text}",
        "summary": f"Bounded self-narrative runtime support is holding a small becoming-line around {focus_text}.",
        "rationale": (
            "A bounded self-narrative continuity signal may return only when chronicle continuity, meaning/significance, temperament, and relation continuity already indicate a carried developmental line, without becoming canonical identity truth, selfhood writeback, prompt authority, workflow authority, or a hidden identity engine."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": narrative_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded chronicle continuity support, meaning/significance support, temperament support, and relation continuity support.",
            f"grounding-mode={grounding_mode}",
            f"narrative-direction={narrative_direction}",
            f"narrative-weight={narrative_weight}",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "Bounded self-narrative continuity remains non-authoritative runtime support only and is not canonical identity truth."
        ),
        "narrative_state": narrative_state,
        "narrative_direction": narrative_direction,
        "narrative_weight": narrative_weight,
        "narrative_summary": _narrative_summary(
            focus=focus_text,
            narrative_state=narrative_state,
            narrative_direction=narrative_direction,
            narrative_weight=narrative_weight,
        ),
        "narrative_confidence": narrative_confidence,
        "source_anchor": source_anchor,
        "grounding_mode": grounding_mode,
        "meaning_signal_id": str(meaning_signal.get("signal_id") or ""),
        "temperament_signal_id": str(temperament_signal.get("signal_id") or ""),
        "relation_continuity_signal_id": str(relation_continuity.get("signal_id") or ""),
        "chronicle_brief_id": str((chronicle_brief or {}).get("brief_id") or ""),
        "chronicle_proposal_id": str((chronicle_proposal or {}).get("proposal_id") or ""),
    }


def _latest_temperament_signal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_temperament_tendency_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


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


def _latest_chronicle_brief(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_chronicle_consolidation_briefs(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_chronicle_proposal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_chronicle_consolidation_proposals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


# ── narrative-projection enrichment (unique — persist return + read surface) ───
def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = _with_runtime_view(item)
    enriched.setdefault("authority", "non-authoritative")
    enriched.setdefault("layer_role", "runtime-support")
    enriched.setdefault("canonical_identity_state", "not-canonical-identity-truth")
    enriched.setdefault("source", "/mc/runtime.self_narrative_continuity_signal")
    return enriched


def _with_runtime_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    canonical_key = str(enriched.get("canonical_key") or "")
    support_summary = str(enriched.get("support_summary") or "")
    focus_text = canonical_key.rsplit(":", 1)[-1].replace("-", " ") if canonical_key else ""
    narrative_state = _canonical_segment(canonical_key, 1, default="becoming-coherent")
    enriched.setdefault("narrative_state", narrative_state)
    enriched.setdefault(
        "narrative_direction",
        _support_value(support_summary, "narrative-direction") or "steadying",
    )
    enriched.setdefault(
        "narrative_weight",
        _support_value(support_summary, "narrative-weight") or "low",
    )
    enriched.setdefault("grounding_mode", _support_value(support_summary, "grounding-mode") or "bounded-runtime-support")
    enriched.setdefault("source_anchor", _anchor_from_support_summary(support_summary))
    enriched.setdefault(
        "narrative_summary",
        _narrative_summary(
            focus=focus_text or str(enriched.get("title") or "visible work"),
            narrative_state=str(enriched.get("narrative_state") or "becoming-coherent"),
            narrative_direction=str(enriched.get("narrative_direction") or "steadying"),
            narrative_weight=str(enriched.get("narrative_weight") or "low"),
        ),
    )
    enriched.setdefault(
        "narrative_confidence",
        str(enriched.get("confidence") or "low"),
    )
    return enriched


def _self_narrative_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_identity_state": "not-canonical-identity-truth",
        "summary_extra": {
            "current_state": str(current.get("narrative_state") or "none"),
            "current_direction": str(current.get("narrative_direction") or "steadying"),
            "current_weight": str(current.get("narrative_weight") or "low"),
            "current_confidence": str(current.get("narrative_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_identity_state": "not-canonical-identity-truth",
        },
    }


def _derive_narrative_state(
    *,
    meaning_type: str,
    temperament_type: str,
    continuity_state: str,
) -> str:
    if temperament_type in {"watchful-restraint", "caution"} or continuity_state in {"watchful-continuity", "careful-continuity"}:
        return "becoming-watchful"
    if temperament_type == "firmness":
        return "becoming-firm"
    if temperament_type == "openness":
        return "becoming-open"
    if meaning_type == "development-significance":
        return "becoming-steady"
    return "becoming-coherent"


def _derive_narrative_direction(
    *,
    meaning_type: str,
    temperament_type: str,
    has_proposal: bool,
    continuity_state: str,
) -> str:
    if temperament_type in {"watchful-restraint", "caution"} or continuity_state in {"watchful-continuity", "careful-continuity"}:
        return "guarding"
    if temperament_type == "firmness":
        return "firming"
    if temperament_type == "openness":
        return "opening"
    if has_proposal or meaning_type == "development-significance":
        return "deepening"
    return "steadying"


def _derive_narrative_weight(
    *,
    meaning_weight: str,
    temperament_weight: str,
    continuity_weight: str,
    brief_weight: str,
    proposal_weight: str,
) -> str:
    strongest = max(
        [
            _WEIGHT_RANKS.get(meaning_weight, 0),
            _WEIGHT_RANKS.get(temperament_weight, 0),
            _WEIGHT_RANKS.get(continuity_weight, 0),
            _WEIGHT_RANKS.get(brief_weight, 0),
            _WEIGHT_RANKS.get(proposal_weight, 0),
        ]
    )
    for label, rank in _WEIGHT_RANKS.items():
        if rank == strongest:
            return label
    return "low"


def _derive_status(
    *,
    meaning_status: str,
    temperament_status: str,
    continuity_status: str,
) -> str:
    if "softening" in {meaning_status, temperament_status, continuity_status}:
        return "softening"
    return "active"


def _grounding_mode(*, has_brief: bool, has_proposal: bool) -> str:
    parts = ["meaning-significance", "temperament-tendency", "relation-continuity"]
    if has_brief:
        parts.append("chronicle-brief")
    if has_proposal:
        parts.append("chronicle-proposal")
    return "+".join(parts)


def _narrative_summary(
    *,
    focus: str,
    narrative_state: str,
    narrative_direction: str,
    narrative_weight: str,
) -> str:
    return (
        f"Bounded self-narrative continuity is carrying {focus.lower()} as a {narrative_weight} "
        f"{narrative_state.replace('-', ' ')} line with a {narrative_direction} direction."
    )


def _focus_key(item: dict[str, object]) -> str:
    canonical_key = str(item.get("canonical_key") or "")
    if not canonical_key:
        return ""
    return canonical_key.rsplit(":", 1)[-1]


def _canonical_segment(canonical_key: str, index: int, *, default: str) -> str:
    parts = [part for part in canonical_key.split(":") if part]
    if len(parts) <= index:
        return default
    return parts[index]


def _support_value(support_summary: str, key: str) -> str:
    for fragment in support_summary.split("|"):
        part = fragment.strip()
        if not part.startswith(f"{key}="):
            continue
        return part.split("=", 1)[1].strip()
    return ""


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    explicit = str(item.get("source_anchor") or "").strip()
    if explicit:
        return explicit
    return _anchor_from_support_summary(str(item.get("support_summary") or ""))


def _anchor_from_support_summary(support_summary: str) -> str:
    fragments: list[str] = []
    for fragment in support_summary.split("|"):
        part = fragment.strip()
        if not part or "=" in part:
            continue
        if part.lower().startswith("derived only from bounded"):
            continue
        fragments.append(part)
    return " | ".join(dict.fromkeys(fragments))


def _merge_fragments(*parts: str) -> str:
    merged: list[str] = []
    for part in parts:
        text = " ".join(str(part or "").split()).strip()
        if not text or text in merged:
            continue
        merged.append(text)
    return " | ".join(merged)


def _value(*values: object, default: str) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return default


def _stronger_confidence(*values: str) -> str:
    strongest = "low"
    strongest_rank = -1
    for value in values:
        rank = _CONFIDENCE_RANKS.get(str(value or "").strip(), -1)
        if rank > strongest_rank:
            strongest = str(value or "").strip() or strongest
            strongest_rank = rank
    return strongest if strongest in _CONFIDENCE_RANKS else "low"


# ── spec: policy-layer S-family knobs + focus-grouped supersede + surface hooks ─
_SPEC = SignalTrackingSpec(
    name="self-narrative-continuity",
    slug="self-narrative-continuity",
    signal_id_prefix="self-narrative-continuity-signal",
    event_prefix="self_narrative_continuity_signal",
    default_signal_type="self-narrative-continuity",
    list_fn=list_runtime_self_narrative_continuity_signals,
    upsert_fn=upsert_runtime_self_narrative_continuity_signal,
    update_status_fn=update_runtime_self_narrative_continuity_signal_status,
    supersede_fn=supersede_runtime_self_narrative_continuity_signals_for_focus,
    supersede_group_field="focus_key",
    supersede_group_kw="focus_key",
    extract_fn=lambda spec, ctx: _extract_self_narrative_continuity_candidates(run_id=str(ctx.get("run_id") or "")),
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active", "softening"}),
    stale_status_reason="Marked stale after bounded self-narrative continuity inactivity window.",
    surface_status_order=("active", "softening", "stale", "superseded"),
    surface_active_statuses=frozenset({"active", "softening"}),
    empty_current_label="No active self-narrative continuity support",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_self_narrative_surface_extra,
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)
