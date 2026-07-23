"""Meaning/significance signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the meaning/significance-specific candidate derivation and the value-layer
surface/runtime enrichment stay here — that is the part unique to this signal.

This is a policy-layer ``_for_focus`` S-family variant: supersede grouping is by
``focus_key``, the refresh window is ``{active, softening}``, and both the read
surface and the persist return carry a bounded value projection (``meaning_type``
/ ``meaning_focus`` / ``meaning_weight`` … plus ``authority`` / ``layer_role`` /
``canonical_value_state``). Those are expressed via ``item_view_fn`` +
``surface_extra_fn`` and the 2-arg ``_with_runtime_view`` applied in the thin
``track`` wrapper.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.runtime.db import (
    list_runtime_chronicle_consolidation_briefs,
    list_runtime_chronicle_consolidation_proposals,
    list_runtime_executive_contradiction_signals,
    list_runtime_meaning_significance_signals,
    list_runtime_private_temporal_promotion_signals,
    list_runtime_regulation_homeostasis_signals,
    list_runtime_relation_continuity_signals,
    supersede_runtime_meaning_significance_signals_for_focus,
    update_runtime_meaning_significance_signal_status,
    upsert_runtime_meaning_significance_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_meaning_significance_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    # Delegate the upsert/supersede/event scaffolding to the framework, but keep
    # the original 2-arg runtime-view enrichment (needs the originating candidate)
    # on the returned items — matching the pre-migration output exactly.
    normalized_session_id = str(session_id or "").strip()
    signals = _extract_meaning_significance_candidates(run_id=run_id)
    persisted = _stf.persist_signals(
        _SPEC, signals=signals, session_id=normalized_session_id, run_id=run_id
    )
    items = [_with_runtime_view(item, signal) for item, signal in zip(persisted, signals)]
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded meaning/significance signals."
            if items
            else "No bounded meaning/significance signal warranted tracking."
        ),
    }


def refresh_runtime_meaning_significance_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_meaning_significance_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _extract_meaning_significance_candidates(*, run_id: str) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for relation_continuity in list_runtime_relation_continuity_signals(limit=18):
        if str(relation_continuity.get("status") or "") not in {"active", "softening"}:
            continue
        if str(relation_continuity.get("run_id") or "") != run_id:
            continue
        focus = _focus_key(relation_continuity)
        chronicle_brief = _latest_chronicle_brief(run_id=run_id, focus_key=focus)
        chronicle_proposal = _latest_chronicle_proposal(run_id=run_id, focus_key=focus)
        if chronicle_brief is None and chronicle_proposal is None:
            continue
        executive_contradiction = _latest_executive_contradiction(run_id=run_id, focus_key=focus)
        temporal_promotion = _latest_temporal_promotion(run_id=run_id, focus_key=focus)
        regulation = _latest_regulation(run_id=run_id, focus_key=focus)
        candidates.append(
            _build_candidate(
                run_id=run_id,
                focus=focus,
                relation_continuity=relation_continuity,
                chronicle_brief=chronicle_brief,
                chronicle_proposal=chronicle_proposal,
                executive_contradiction=executive_contradiction,
                temporal_promotion=temporal_promotion,
                regulation=regulation,
            )
        )
    return candidates[:4]


def _build_candidate(
    *,
    run_id: str,
    focus: str,
    relation_continuity: dict[str, object],
    chronicle_brief: dict[str, object] | None,
    chronicle_proposal: dict[str, object] | None,
    executive_contradiction: dict[str, object] | None,
    temporal_promotion: dict[str, object] | None,
    regulation: dict[str, object] | None,
) -> dict[str, object]:
    continuity_state = _value(relation_continuity.get("continuity_state"), default="carried-alignment")
    continuity_alignment = _value(
        relation_continuity.get("continuity_alignment"),
        default="working-alignment",
    )
    continuity_watchfulness = _value(
        relation_continuity.get("continuity_watchfulness"),
        default="low",
    )
    chronicle_weight = _value(
        (chronicle_proposal or {}).get("proposal_weight"),
        _value((chronicle_brief or {}).get("brief_weight"), default="low"),
        default="low",
    )
    contradiction_pressure = _value(
        (executive_contradiction or {}).get("control_pressure"),
        default="low",
    )
    promotion_pull = _value(
        (temporal_promotion or {}).get("promotion_pull"),
        default="low",
    )
    regulation_pressure = _value(
        (regulation or {}).get("regulation_pressure"),
        default="low",
    )

    meaning_weight = _derive_meaning_weight(
        chronicle_weight=chronicle_weight,
        continuity_weight=_value(relation_continuity.get("continuity_weight"), default="low"),
        contradiction_pressure=contradiction_pressure,
        promotion_pull=promotion_pull,
    )
    meaning_type = _derive_meaning_type(
        has_proposal=chronicle_proposal is not None,
        continuity_state=continuity_state,
        contradiction_pressure=contradiction_pressure,
        promotion_pull=promotion_pull,
    )
    meaning_confidence = _stronger_confidence(
        str(relation_continuity.get("continuity_confidence") or relation_continuity.get("confidence") or "low"),
        str((chronicle_brief or {}).get("brief_confidence") or (chronicle_brief or {}).get("confidence") or "low"),
        str((chronicle_proposal or {}).get("proposal_confidence") or (chronicle_proposal or {}).get("confidence") or "low"),
        str((executive_contradiction or {}).get("control_confidence") or (executive_contradiction or {}).get("confidence") or "low"),
        str((temporal_promotion or {}).get("promotion_confidence") or (temporal_promotion or {}).get("confidence") or "low"),
        str((regulation or {}).get("regulation_confidence") or (regulation or {}).get("confidence") or "low"),
    )
    status = _derive_status(
        proposal_status=str((chronicle_proposal or {}).get("status") or ""),
        brief_status=str((chronicle_brief or {}).get("status") or ""),
        continuity_status=str(relation_continuity.get("status") or ""),
    )
    grounding_mode = _grounding_mode(
        has_brief=chronicle_brief is not None,
        has_proposal=chronicle_proposal is not None,
        has_contradiction=executive_contradiction is not None,
        has_promotion=temporal_promotion is not None,
        has_regulation=regulation is not None,
    )
    source_anchor = _merge_fragments(
        _anchor(relation_continuity),
        _anchor(chronicle_brief),
        _anchor(chronicle_proposal),
        _anchor(executive_contradiction),
        _anchor(temporal_promotion),
        _anchor(regulation),
    )
    evidence_summary = _merge_fragments(
        str(relation_continuity.get("evidence_summary") or ""),
        str((chronicle_brief or {}).get("evidence_summary") or ""),
        str((chronicle_proposal or {}).get("evidence_summary") or ""),
        str((executive_contradiction or {}).get("evidence_summary") or ""),
        str((temporal_promotion or {}).get("evidence_summary") or ""),
        str((regulation or {}).get("evidence_summary") or ""),
    )
    meaning_focus = focus.replace("-", " ")

    return {
        "signal_type": "meaning-significance",
        "canonical_key": f"meaning-significance:{meaning_type}:{focus}",
        "focus_key": focus,
        "status": status,
        "title": f"Meaning significance support: {meaning_focus}",
        "summary": (
            f"Bounded meaning/significance runtime support is holding a small significance-weight around {meaning_focus}."
        ),
        "rationale": (
            "A bounded meaning/significance signal may return only when chronicle continuity and relation continuity already indicate a carried thread, with only small sharpening from temporal promotion, executive contradiction, or regulation, without becoming moral authority, conscience authority, prompt authority, workflow authority, or canonical value truth."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": meaning_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded chronicle continuity support, relation continuity support, and small promotion/contradiction/regulation sharpening.",
            f"grounding-mode={grounding_mode}",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "Bounded meaning/significance remains non-authoritative runtime support only and is not canonical value or moral truth."
        ),
        "meaning_type": meaning_type,
        "meaning_focus": meaning_focus,
        "meaning_weight": meaning_weight,
        "meaning_summary": _meaning_summary(
            focus=meaning_focus,
            meaning_type=meaning_type,
            meaning_weight=meaning_weight,
            continuity_alignment=continuity_alignment,
            continuity_watchfulness=continuity_watchfulness,
            regulation_pressure=regulation_pressure,
        ),
        "meaning_confidence": meaning_confidence,
        "source_anchor": source_anchor,
        "grounding_mode": grounding_mode,
        "relation_continuity_signal_id": str(relation_continuity.get("signal_id") or ""),
        "chronicle_brief_id": str((chronicle_brief or {}).get("brief_id") or ""),
        "chronicle_proposal_id": str((chronicle_proposal or {}).get("proposal_id") or ""),
        "executive_contradiction_signal_id": str((executive_contradiction or {}).get("signal_id") or ""),
        "temporal_promotion_signal_id": str((temporal_promotion or {}).get("signal_id") or ""),
        "regulation_signal_id": str((regulation or {}).get("signal_id") or ""),
        "run_id": run_id,
    }


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


def _focus_key(item: dict[str, object] | None) -> str:
    canonical_key = str((item or {}).get("canonical_key") or "")
    if canonical_key.count(":") >= 2:
        return canonical_key.split(":", 2)[2].strip() or "visible-work"
    title = str((item or {}).get("title") or "").strip().lower().replace(" ", "-")
    return title or "visible-work"


def _derive_meaning_type(
    *,
    has_proposal: bool,
    continuity_state: str,
    contradiction_pressure: str,
    promotion_pull: str,
) -> str:
    if contradiction_pressure == "medium":
        return "watchful-significance"
    if has_proposal and promotion_pull == "medium":
        return "development-significance"
    if "trustful" in continuity_state or "alignment" in continuity_state:
        return "relational-significance"
    return "carried-significance"


def _derive_meaning_weight(
    *,
    chronicle_weight: str,
    continuity_weight: str,
    contradiction_pressure: str,
    promotion_pull: str,
) -> str:
    if chronicle_weight == "high" or continuity_weight == "high":
        return "high"
    if (
        chronicle_weight == "medium"
        or continuity_weight == "medium"
        or contradiction_pressure == "medium"
        or promotion_pull == "medium"
    ):
        return "medium"
    return "low"


def _derive_status(*, proposal_status: str, brief_status: str, continuity_status: str) -> str:
    if proposal_status == "active" or brief_status == "active" or continuity_status == "active":
        return "active"
    if proposal_status == "softening" or brief_status == "softening" or continuity_status == "softening":
        return "softening"
    return "active"


def _grounding_mode(
    *,
    has_brief: bool,
    has_proposal: bool,
    has_contradiction: bool,
    has_promotion: bool,
    has_regulation: bool,
) -> str:
    parts = ["relation-continuity"]
    if has_brief:
        parts.append("chronicle-brief")
    if has_proposal:
        parts.append("chronicle-proposal")
    if has_promotion:
        parts.append("temporal-promotion")
    if has_contradiction:
        parts.append("executive-contradiction")
    if has_regulation:
        parts.append("regulation")
    return "+".join(parts)


def _meaning_summary(
    *,
    focus: str,
    meaning_type: str,
    meaning_weight: str,
    continuity_alignment: str,
    continuity_watchfulness: str,
    regulation_pressure: str,
) -> str:
    focus_text = focus.replace("-", " ")
    return (
        f"{focus_text} is carrying {meaning_weight} {meaning_type.replace('-', ' ')} "
        f"through {continuity_alignment.replace('-', ' ')} with {continuity_watchfulness} watchfulness"
        f"{' and ' + regulation_pressure + ' regulation pressure' if regulation_pressure != 'low' else ''}."
    )[:220]


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


# ── value-layer enrichment (unique — persist return + read surface) ───────────
def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    return {
        **item,
        "meaning_type": str(signal.get("meaning_type") or "carried-significance"),
        "meaning_focus": str(signal.get("meaning_focus") or _focus_key(signal).replace("-", " ")),
        "meaning_weight": str(signal.get("meaning_weight") or "low"),
        "meaning_summary": str(signal.get("meaning_summary") or item.get("summary") or ""),
        "meaning_confidence": str(signal.get("meaning_confidence") or item.get("confidence") or "low"),
        "source_anchor": str(signal.get("source_anchor") or ""),
        "grounding_mode": str(signal.get("grounding_mode") or "relation-continuity"),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_value_state": "not-canonical-value-or-moral-truth",
        "source": "/mc/runtime.meaning_significance_signal",
    }


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    canonical_key = str(item.get("canonical_key") or "")
    support_summary = str(item.get("support_summary") or "")
    return {
        **item,
        "meaning_type": _value(
            item.get("meaning_type"),
            _canonical_segment(canonical_key, index=1),
            default="carried-significance",
        ),
        "meaning_focus": _value(
            item.get("meaning_focus"),
            _canonical_segment(canonical_key, index=2).replace("-", " "),
            default="visible work",
        ),
        "meaning_weight": _value(
            item.get("meaning_weight"),
            _weight_from_summary(support_summary, canonical_key=canonical_key),
            default="low",
        ),
        "meaning_summary": _value(
            item.get("meaning_summary"),
            item.get("summary"),
            default="No bounded meaning/significance support",
        ),
        "meaning_confidence": _value(
            item.get("meaning_confidence"),
            item.get("confidence"),
            default="low",
        ),
        "source_anchor": _value(item.get("source_anchor"), _anchor(item)),
        "grounding_mode": _value(
            item.get("grounding_mode"),
            _grounding_mode_from_support_summary(support_summary),
            default="relation-continuity",
        ),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_value_state": "not-canonical-value-or-moral-truth",
        "source": "/mc/runtime.meaning_significance_signal",
    }


def _meaning_significance_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_value_state": "not-canonical-value-or-moral-truth",
        "summary_extra": {
            "current_type": str(current.get("meaning_type") or "none"),
            "current_focus": str(current.get("meaning_focus") or "none"),
            "current_weight": str(current.get("meaning_weight") or "low"),
            "current_confidence": str(current.get("meaning_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_value_state": "not-canonical-value-or-moral-truth",
        },
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
            return normalized.split("=", 1)[1].strip() or "relation-continuity"
    return "relation-continuity"


def _weight_from_summary(value: str, *, canonical_key: str) -> str:
    lowered = str(value or "").lower()
    if "high" in lowered or ":high:" in canonical_key:
        return "high"
    if "medium" in lowered:
        return "medium"
    return "low"


# ── spec: policy-layer S-family knobs + focus-grouped supersede + surface hooks ─
_SPEC = SignalTrackingSpec(
    name="meaning-significance",
    slug="meaning-significance",
    signal_id_prefix="meaning-significance-signal",
    event_prefix="meaning_significance_signal",
    default_signal_type="meaning-significance",
    list_fn=list_runtime_meaning_significance_signals,
    upsert_fn=upsert_runtime_meaning_significance_signal,
    update_status_fn=update_runtime_meaning_significance_signal_status,
    supersede_fn=supersede_runtime_meaning_significance_signals_for_focus,
    supersede_group_field="focus_key",
    supersede_group_kw="focus_key",
    extract_fn=lambda spec, ctx: _extract_meaning_significance_candidates(run_id=str(ctx.get("run_id") or "")),
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active", "softening"}),
    stale_status_reason="Marked stale after bounded meaning/significance inactivity window.",
    surface_status_order=("active", "softening", "stale", "superseded"),
    surface_active_statuses=frozenset({"active", "softening"}),
    empty_current_label="No active meaning/significance support",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_meaning_significance_surface_extra,
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)
