"""Relation-continuity signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the relation-continuity-specific candidate derivation and the continuity-projection
enrichment stay here — that is the part unique to this signal.

This is a ``_for_focus`` S-family variant: supersede grouping is by ``focus_key``,
and both the read surface and the persist return carry a bounded continuity
projection (``continuity_state`` / ``continuity_alignment`` / ``continuity_weight`` …
plus ``authority`` / ``layer_role`` / ``canonical_relation_state``). Those are
expressed via ``item_view_fn`` + ``surface_extra_fn`` and the 2-arg
``_with_runtime_view`` applied (zipped with the originating candidates) in the thin
``track`` wrapper.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.runtime.db import (
    list_runtime_chronicle_consolidation_briefs,
    list_runtime_chronicle_consolidation_signals,
    list_runtime_regulation_homeostasis_signals,
    list_runtime_relation_continuity_signals,
    list_runtime_relation_state_signals,
    list_runtime_user_understanding_signals,
    supersede_runtime_relation_continuity_signals_for_focus,
    update_runtime_relation_continuity_signal_status,
    upsert_runtime_relation_continuity_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_relation_continuity_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    # Delegate the upsert/supersede/event scaffolding to the framework, but keep
    # the original 2-arg runtime-view enrichment (needs the originating candidate)
    # on the returned items — matching the pre-migration output exactly.
    normalized_session_id = str(session_id or "").strip()
    signals = _extract_relation_continuity_candidates(run_id=run_id)
    persisted = _stf.persist_signals(
        _SPEC, signals=signals, session_id=normalized_session_id, run_id=run_id
    )
    items = [_with_runtime_view(item, signal) for item, signal in zip(persisted, signals)]
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded relation-continuity signals."
            if items
            else "No bounded relation-continuity signal warranted tracking."
        ),
    }


def refresh_runtime_relation_continuity_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_relation_continuity_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _extract_relation_continuity_candidates(*, run_id: str) -> list[dict[str, object]]:
    user_understanding = _latest_user_understanding_signal(run_id=run_id)
    if user_understanding is None:
        return []

    candidates: list[dict[str, object]] = []
    for relation_state in list_runtime_relation_state_signals(limit=12):
        if str(relation_state.get("status") or "") != "active":
            continue
        if str(relation_state.get("run_id") or "") != run_id:
            continue
        focus = _focus_key(relation_state)
        chronicle_brief = _latest_chronicle_brief(run_id=run_id, focus_key=focus)
        chronicle_signal = _latest_chronicle_signal(run_id=run_id, focus_key=focus)
        if chronicle_brief is None and chronicle_signal is None:
            continue
        regulation = _latest_regulation_signal(run_id=run_id, focus_key=focus)

        continuity_alignment = _value(
            relation_state.get("relation_alignment"),
            default="working-alignment",
        )
        continuity_watchfulness = _derive_continuity_watchfulness(
            relation_watchfulness=_value(relation_state.get("relation_watchfulness"), default="low"),
            regulation_watchfulness=_value((regulation or {}).get("regulation_watchfulness"), default="low"),
        )
        continuity_weight = _derive_continuity_weight(
            chronicle_weight=_value((chronicle_brief or {}).get("brief_weight"), _value((chronicle_signal or {}).get("chronicle_weight"), default="low"), default="low"),
            relation_confidence=_value(relation_state.get("relation_confidence"), relation_state.get("confidence"), default="low"),
        )
        continuity_state = _derive_continuity_state(
            relation_state=_value(relation_state.get("relation_state"), default="working-alignment"),
            continuity_alignment=continuity_alignment,
            continuity_watchfulness=continuity_watchfulness,
            continuity_weight=continuity_weight,
        )
        continuity_confidence = _stronger_confidence(
            str(relation_state.get("relation_confidence") or relation_state.get("confidence") or "low"),
            str((chronicle_brief or {}).get("brief_confidence") or (chronicle_brief or {}).get("confidence") or "low"),
            str((chronicle_signal or {}).get("chronicle_confidence") or (chronicle_signal or {}).get("confidence") or "low"),
            str(user_understanding.get("signal_confidence") or user_understanding.get("confidence") or "low"),
            str((regulation or {}).get("regulation_confidence") or (regulation or {}).get("confidence") or "low"),
        )
        status = "active" if str((chronicle_brief or chronicle_signal or {}).get("status") or "active") == "active" else "softening"
        source_anchor = _merge_fragments(
            _anchor(relation_state),
            _anchor(chronicle_brief),
            _anchor(chronicle_signal),
            _anchor(user_understanding),
            _anchor(regulation),
        )
        evidence_summary = _merge_fragments(
            str(relation_state.get("evidence_summary") or ""),
            str((chronicle_brief or {}).get("evidence_summary") or ""),
            str((chronicle_signal or {}).get("evidence_summary") or ""),
            str(user_understanding.get("evidence_summary") or ""),
            str((regulation or {}).get("evidence_summary") or ""),
        )
        grounding_mode = _grounding_mode(
            has_chronicle_brief=chronicle_brief is not None,
            has_chronicle_signal=chronicle_signal is not None,
            has_regulation=regulation is not None,
        )
        candidates.append(
            {
                "signal_type": "relation-continuity",
                "canonical_key": f"relation-continuity:{continuity_state}:{focus}",
                "focus_key": focus,
                "status": status,
                "title": f"Relation continuity support: {focus.replace('-', ' ')}",
                "summary": (
                    f"Bounded relation continuity runtime support is holding a small working-relationship continuity thread around {focus.replace('-', ' ')}."
                ),
                "rationale": (
                    "A bounded relation-continuity signal may return only when an existing relation-state signal and chronicle continuity support already indicate a thread that looks relationally persistent, without becoming canonical relationship truth, prompt authority, or hidden social simulation."
                ),
                "source_kind": "runtime-derived-support",
                "confidence": continuity_confidence,
                "evidence_summary": evidence_summary,
                "support_summary": _merge_fragments(
                    "Derived only from bounded relation-state support, chronicle continuity support, user-understanding substrate, and optional regulation sharpening.",
                    f"grounding-mode={grounding_mode}",
                    source_anchor,
                ),
                "support_count": 1,
                "session_count": 1,
                "status_reason": (
                    "Bounded relation continuity remains non-authoritative runtime support only and is not canonical relationship truth."
                ),
                "continuity_state": continuity_state,
                "continuity_alignment": continuity_alignment,
                "continuity_watchfulness": continuity_watchfulness,
                "continuity_weight": continuity_weight,
                "continuity_summary": _continuity_summary(
                    focus=focus,
                    continuity_state=continuity_state,
                    continuity_alignment=continuity_alignment,
                    continuity_watchfulness=continuity_watchfulness,
                    continuity_weight=continuity_weight,
                ),
                "continuity_confidence": continuity_confidence,
                "source_anchor": source_anchor,
                "grounding_mode": grounding_mode,
                "relation_state_signal_id": str(relation_state.get("signal_id") or ""),
                "chronicle_brief_id": str((chronicle_brief or {}).get("brief_id") or ""),
                "chronicle_signal_id": str((chronicle_signal or {}).get("signal_id") or ""),
                "user_understanding_signal_id": str(user_understanding.get("signal_id") or ""),
                "regulation_signal_id": str((regulation or {}).get("signal_id") or ""),
            }
        )
    return candidates[:4]


def _latest_user_understanding_signal(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_user_understanding_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
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


def _latest_chronicle_signal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_chronicle_consolidation_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_regulation_signal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_regulation_homeostasis_signals(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _derive_continuity_watchfulness(*, relation_watchfulness: str, regulation_watchfulness: str) -> str:
    if relation_watchfulness == "medium" or regulation_watchfulness == "medium":
        return "medium"
    return "low"


def _derive_continuity_weight(*, chronicle_weight: str, relation_confidence: str) -> str:
    if chronicle_weight == "high":
        return "high"
    if chronicle_weight == "medium" or relation_confidence in {"medium", "high"}:
        return "medium"
    return "low"


def _derive_continuity_state(
    *,
    relation_state: str,
    continuity_alignment: str,
    continuity_watchfulness: str,
    continuity_weight: str,
) -> str:
    if relation_state == "trustful-flow" and continuity_weight in {"medium", "high"}:
        return "trustful-continuity"
    if continuity_watchfulness == "medium":
        return "watchful-continuity"
    if continuity_alignment in {"aligned", "working-alignment"}:
        return "carried-alignment"
    return "careful-continuity"


def _continuity_summary(
    *,
    focus: str,
    continuity_state: str,
    continuity_alignment: str,
    continuity_watchfulness: str,
    continuity_weight: str,
) -> str:
    label = focus.replace("-", " ")
    return (
        f"{label} is currently held as a bounded {continuity_state} thread, with {continuity_alignment} alignment, "
        f"{continuity_watchfulness} watchfulness, and {continuity_weight} continuity weight."
    )


def _grounding_mode(*, has_chronicle_brief: bool, has_chronicle_signal: bool, has_regulation: bool) -> str:
    parts = ["relation-state", "user-understanding"]
    if has_chronicle_brief:
        parts.append("chronicle-brief")
    elif has_chronicle_signal:
        parts.append("chronicle-signal")
    if has_regulation:
        parts.append("regulation")
    return "+".join(parts)


# ── continuity-projection enrichment (unique — persist return + read surface) ──
def _with_runtime_view(record: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    enriched = dict(record)
    enriched.update(
        {
            "continuity_state": signal.get("continuity_state", "carried-alignment"),
            "continuity_alignment": signal.get("continuity_alignment", "working-alignment"),
            "continuity_watchfulness": signal.get("continuity_watchfulness", "low"),
            "continuity_weight": signal.get("continuity_weight", "low"),
            "continuity_summary": signal.get("continuity_summary", ""),
            "continuity_confidence": signal.get("continuity_confidence", record.get("confidence", "low")),
            "source_anchor": signal.get("source_anchor", ""),
            "grounding_mode": signal.get("grounding_mode", "relation-state+user-understanding"),
            "relation_state_signal_id": signal.get("relation_state_signal_id", ""),
            "chronicle_brief_id": signal.get("chronicle_brief_id", ""),
            "chronicle_signal_id": signal.get("chronicle_signal_id", ""),
            "user_understanding_signal_id": signal.get("user_understanding_signal_id", ""),
            "regulation_signal_id": signal.get("regulation_signal_id", ""),
        }
    )
    return _with_surface_view(enriched)


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched.setdefault("continuity_state", _canonical_segment(str(item.get("canonical_key") or ""), index=1) or "carried-alignment")
    enriched.setdefault("continuity_alignment", "working-alignment")
    enriched.setdefault("continuity_watchfulness", "low")
    enriched.setdefault("continuity_weight", "low")
    enriched.setdefault("continuity_summary", str(item.get("summary") or ""))
    enriched.setdefault("continuity_confidence", str(item.get("confidence") or "low"))
    enriched.setdefault("source_anchor", _source_anchor_from_support_summary(str(item.get("support_summary") or "")))
    enriched.setdefault("grounding_mode", _grounding_mode_from_support_summary(str(item.get("support_summary") or "")) or "relation-state+user-understanding")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["canonical_relation_state"] = "not-canonical-relationship-truth"
    return enriched


def _relation_continuity_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_relation_state": "not-canonical-relationship-truth",
        "summary_extra": {
            "current_state": str(current.get("continuity_state") or "none"),
            "current_alignment": str(current.get("continuity_alignment") or "working-alignment"),
            "current_watchfulness": str(current.get("continuity_watchfulness") or "low"),
            "current_weight": str(current.get("continuity_weight") or "low"),
            "current_confidence": str(current.get("continuity_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_relation_state": "not-canonical-relationship-truth",
        },
    }


def _focus_key(item: dict[str, object] | None) -> str:
    return _canonical_segment(str((item or {}).get("canonical_key") or ""), index=-1) or "current-user"


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    title = str(item.get("title") or "").strip()
    canonical_key = str(item.get("canonical_key") or "").strip()
    if title and canonical_key:
        return f"{title} [{canonical_key}]"
    return title or canonical_key


def _canonical_segment(value: str, *, index: int) -> str:
    if not value:
        return ""
    parts = [part.strip() for part in value.split(":") if part.strip()]
    if not parts:
        return ""
    try:
        return parts[index]
    except IndexError:
        return ""


def _merge_fragments(*values: str) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return " | ".join(ordered)


def _stronger_confidence(*values: str) -> str:
    best = "low"
    best_rank = _CONFIDENCE_RANKS[best]
    for raw_value in values:
        value = _value(raw_value, default="low")
        rank = _CONFIDENCE_RANKS.get(value, 0)
        if rank > best_rank:
            best = value
            best_rank = rank
    return best


def _value(*values: object, default: str) -> str:
    for raw_value in values:
        value = str(raw_value or "").strip().lower()
        if value:
            return value
    return default


def _grounding_mode_from_support_summary(value: str) -> str:
    for piece in str(value or "").split(" | "):
        normalized = piece.strip()
        if normalized.startswith("grounding-mode="):
            return normalized.split("=", 1)[1].strip()
    return ""


def _source_anchor_from_support_summary(value: str) -> str:
    anchors: list[str] = []
    for piece in str(value or "").split(" | "):
        normalized = piece.strip()
        if not normalized:
            continue
        if normalized.startswith("Derived only from "):
            continue
        if normalized.startswith("grounding-mode="):
            continue
        anchors.append(normalized)
    return " | ".join(anchors)


# ── spec: policy-layer S-family knobs + focus-grouped supersede + surface hooks ─
_SPEC = SignalTrackingSpec(
    name="relation-continuity",
    slug="relation-continuity",
    signal_id_prefix="relation-continuity-signal",
    event_prefix="relation_continuity_signal",
    default_signal_type="relation-continuity",
    list_fn=list_runtime_relation_continuity_signals,
    upsert_fn=upsert_runtime_relation_continuity_signal,
    update_status_fn=update_runtime_relation_continuity_signal_status,
    supersede_fn=supersede_runtime_relation_continuity_signals_for_focus,
    supersede_group_field="focus_key",
    supersede_group_kw="focus_key",
    extract_fn=lambda spec, ctx: _extract_relation_continuity_candidates(run_id=str(ctx.get("run_id") or "")),
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active", "softening"}),
    stale_status_reason="Marked stale after bounded relation-continuity inactivity window.",
    surface_status_order=("active", "softening", "stale", "superseded"),
    surface_active_statuses=frozenset({"active", "softening"}),
    empty_current_label="No active relation-continuity support",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_relation_continuity_surface_extra,
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)
