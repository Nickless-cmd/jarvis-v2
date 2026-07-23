"""Relation-state signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the relation-state-specific candidate derivation and the control-layer
surface/runtime enrichment stay here — that is the part unique to this signal.

This is a policy-layer ``_for_focus`` S-family variant: supersede grouping is by
``focus_key`` (not domain), the refresh window is ``{active}``-only, and both the
read surface and the persist return carry a bounded relation-state projection
(``relation_state`` / ``relation_alignment`` / ``relation_watchfulness`` … plus
``authority`` / ``layer_role`` / ``canonical_relation_state``). Those are expressed
via ``item_view_fn`` + ``surface_extra_fn`` and the 2-arg ``_with_runtime_view``
applied in the thin ``track`` wrapper.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.runtime.db import (
    list_runtime_executive_contradiction_signals,
    list_runtime_inner_visible_support_signals,
    list_runtime_private_state_snapshots,
    list_runtime_regulation_homeostasis_signals,
    list_runtime_relation_state_signals,
    list_runtime_user_understanding_signals,
    supersede_runtime_relation_state_signals_for_focus,
    update_runtime_relation_state_signal_status,
    upsert_runtime_relation_state_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_relation_state_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    # Delegate the upsert/supersede/event scaffolding to the framework, but keep
    # the original 2-arg runtime-view enrichment (needs the originating candidate)
    # on the returned items — matching the pre-migration output exactly.
    normalized_session_id = str(session_id or "").strip()
    candidate = _extract_candidate_for_run(run_id=run_id)
    if candidate is None:
        return {
            "created": 0,
            "updated": 0,
            "items": [],
            "summary": "No bounded relation-state grounding was available for this visible turn.",
        }

    persisted = _stf.persist_signals(
        _SPEC, signals=[candidate], session_id=normalized_session_id, run_id=run_id
    )
    items = [_with_runtime_view(item, candidate) for item in persisted]
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            "Tracked 1 bounded relation-state runtime signal."
            if items
            else "No bounded relation-state runtime signal warranted tracking."
        ),
    }


def refresh_runtime_relation_state_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_relation_state_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    user_understanding = _latest_user_understanding_signal(run_id=run_id)
    if user_understanding is None:
        return None

    private_state = _latest_private_state_snapshot(run_id=run_id)
    regulation = _latest_regulation_homeostasis_signal(run_id=run_id)
    if private_state is None and regulation is None:
        return None

    focus = _focus_key(private_state, regulation, user_understanding)
    executive_contradiction = _latest_executive_contradiction_signal(run_id=run_id, focus_key=focus)
    inner_visible_support = _latest_inner_visible_support_signal(run_id=run_id, focus_key=focus)

    user_dimension = _value(
        user_understanding.get("user_dimension"),
        _canonical_segment(str(user_understanding.get("canonical_key") or ""), index=-1),
        default="current-user",
    )
    user_confidence = _value(
        user_understanding.get("signal_confidence"),
        user_understanding.get("confidence"),
        default="low",
    )
    relation_alignment = _derive_relation_alignment(
        user_confidence=user_confidence,
        user_signal_type=_value(user_understanding.get("signal_type"), default="preference-signal"),
        regulation_state=_value((regulation or {}).get("regulation_state"), default="steady-support"),
        contradiction_status=_value((executive_contradiction or {}).get("status"), default="none"),
    )
    relation_watchfulness = _derive_relation_watchfulness(
        regulation_watchfulness=_value((regulation or {}).get("regulation_watchfulness"), default="low"),
        contradiction_pressure=_value((executive_contradiction or {}).get("control_pressure"), default="low"),
        visible_watchfulness=_value((inner_visible_support or {}).get("support_watchfulness"), default="low"),
    )
    relation_pressure = _derive_relation_pressure(
        regulation_pressure=_value((regulation or {}).get("regulation_pressure"), default="low"),
        contradiction_pressure=_value((executive_contradiction or {}).get("control_pressure"), default="low"),
    )
    relation_state = _derive_relation_state(
        alignment=relation_alignment,
        watchfulness=relation_watchfulness,
        pressure=relation_pressure,
    )
    relation_confidence = _stronger_confidence(
        str(user_understanding.get("signal_confidence") or user_understanding.get("confidence") or "low"),
        str((private_state or {}).get("state_confidence") or (private_state or {}).get("confidence") or "low"),
        str((regulation or {}).get("regulation_confidence") or (regulation or {}).get("confidence") or "low"),
        str((executive_contradiction or {}).get("control_confidence") or (executive_contradiction or {}).get("confidence") or "low"),
        str((inner_visible_support or {}).get("support_confidence") or (inner_visible_support or {}).get("confidence") or "low"),
    )
    grounding_mode = _grounding_mode(
        has_private_state=private_state is not None,
        has_regulation=regulation is not None,
        has_executive_contradiction=executive_contradiction is not None,
        has_inner_visible_support=inner_visible_support is not None,
    )
    source_anchor = _merge_fragments(
        _support_anchor(user_understanding),
        _support_anchor(private_state) if private_state else "",
        _support_anchor(regulation) if regulation else "",
        _support_anchor(executive_contradiction) if executive_contradiction else "",
        _support_anchor(inner_visible_support) if inner_visible_support else "",
    )
    evidence_summary = _merge_fragments(
        str(user_understanding.get("evidence_summary") or ""),
        str((private_state or {}).get("evidence_summary") or ""),
        str((regulation or {}).get("evidence_summary") or ""),
        str((executive_contradiction or {}).get("evidence_summary") or ""),
        str((inner_visible_support or {}).get("evidence_summary") or ""),
    )

    return {
        "signal_type": "relation-state",
        "canonical_key": f"relation-state:{relation_state}:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Relation state support: {focus.replace('-', ' ')}",
        "summary": (
            f"Bounded relation-state runtime support is holding a small working relationship state around {focus.replace('-', ' ')}."
        ),
        "rationale": (
            "A bounded relation-state signal may be derived only from already-returned user-understanding runtime support plus bounded regulation, private-state, executive-contradiction, and inner-visible support, without becoming canonical relationship truth, hidden emotional authority, workflow authority, or planner authority."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": relation_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded user-understanding runtime support plus bounded regulation, private-state, executive-contradiction, and optional inner-visible sharpening.",
            f"grounding-mode={grounding_mode}",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "Bounded relation-state remains subordinate to visible/runtime truth, is non-authoritative runtime support only, and is not canonical relationship truth."
        ),
        "relation_state": relation_state,
        "relation_alignment": relation_alignment,
        "relation_watchfulness": relation_watchfulness,
        "relation_pressure": relation_pressure,
        "relation_summary": _relation_summary(
            focus=focus,
            relation_state=relation_state,
            relation_alignment=relation_alignment,
            relation_watchfulness=relation_watchfulness,
            relation_pressure=relation_pressure,
        ),
        "relation_confidence": relation_confidence,
        "source_anchor": source_anchor,
        "user_understanding_signal_id": str(user_understanding.get("signal_id") or ""),
        "state_snapshot_id": str((private_state or {}).get("snapshot_id") or ""),
        "regulation_signal_id": str((regulation or {}).get("signal_id") or ""),
        "executive_contradiction_signal_id": str((executive_contradiction or {}).get("signal_id") or ""),
        "inner_visible_support_signal_id": str((inner_visible_support or {}).get("signal_id") or ""),
        "grounding_mode": grounding_mode,
        "relation_dimension": user_dimension,
    }


def _latest_user_understanding_signal(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_user_understanding_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        return item
    return None


def _latest_private_state_snapshot(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_state_snapshots(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        return item
    return None


def _latest_regulation_homeostasis_signal(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_regulation_homeostasis_signals(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        return item
    return None


def _latest_executive_contradiction_signal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_executive_contradiction_signals(limit=18):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_inner_visible_support_signal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_inner_visible_support_signals(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _derive_relation_alignment(
    *,
    user_confidence: str,
    user_signal_type: str,
    regulation_state: str,
    contradiction_status: str,
) -> str:
    if user_confidence == "high" and contradiction_status == "none":
        return "aligned"
    if user_signal_type in {"workstyle-signal", "preference-signal"} and regulation_state in {"steady-support", "settling-support"}:
        return "working-alignment"
    return "cautious-alignment"


def _derive_relation_watchfulness(
    *,
    regulation_watchfulness: str,
    contradiction_pressure: str,
    visible_watchfulness: str,
) -> str:
    if contradiction_pressure in {"medium", "high"}:
        return "medium"
    if regulation_watchfulness == "medium" or visible_watchfulness == "medium":
        return "medium"
    return "low"


def _derive_relation_pressure(
    *,
    regulation_pressure: str,
    contradiction_pressure: str,
) -> str:
    if regulation_pressure == "medium" or contradiction_pressure in {"medium", "high"}:
        return "medium"
    return "low"


def _derive_relation_state(
    *,
    alignment: str,
    watchfulness: str,
    pressure: str,
) -> str:
    if alignment == "aligned" and watchfulness == "low" and pressure == "low":
        return "trustful-flow"
    if watchfulness == "medium" and pressure == "medium":
        return "cautious-distance"
    if watchfulness == "medium":
        return "careful-collaboration"
    return "working-alignment"


def _relation_summary(
    *,
    focus: str,
    relation_state: str,
    relation_alignment: str,
    relation_watchfulness: str,
    relation_pressure: str,
) -> str:
    label = focus.replace("-", " ")
    return (
        f"{label} is currently held in a bounded {relation_state} relation state, with {relation_alignment} alignment, "
        f"{relation_watchfulness} watchfulness, and {relation_pressure} pressure."
    )


def _grounding_mode(
    *,
    has_private_state: bool,
    has_regulation: bool,
    has_executive_contradiction: bool,
    has_inner_visible_support: bool,
) -> str:
    parts = ["user-understanding"]
    if has_private_state:
        parts.append("private-state")
    if has_regulation:
        parts.append("regulation")
    if has_executive_contradiction:
        parts.append("executive-contradiction")
    if has_inner_visible_support:
        parts.append("inner-visible-sharpening")
    return "+".join(parts)


# ── control-layer enrichment (unique — persist return + read surface) ─────────
def _with_runtime_view(
    record: dict[str, object],
    signal: dict[str, object],
) -> dict[str, object]:
    enriched = dict(record)
    enriched.update(
        {
            "relation_state": signal.get("relation_state", "working-alignment"),
            "relation_alignment": signal.get("relation_alignment", "working-alignment"),
            "relation_watchfulness": signal.get("relation_watchfulness", "low"),
            "relation_pressure": signal.get("relation_pressure", "low"),
            "relation_summary": signal.get("relation_summary", ""),
            "relation_confidence": signal.get("relation_confidence", record.get("confidence", "low")),
            "source_anchor": signal.get("source_anchor", ""),
            "grounding_mode": signal.get("grounding_mode", "user-understanding"),
            "relation_dimension": signal.get("relation_dimension", "current-user"),
            "user_understanding_signal_id": signal.get("user_understanding_signal_id", ""),
            "state_snapshot_id": signal.get("state_snapshot_id", ""),
            "regulation_signal_id": signal.get("regulation_signal_id", ""),
            "executive_contradiction_signal_id": signal.get("executive_contradiction_signal_id", ""),
            "inner_visible_support_signal_id": signal.get("inner_visible_support_signal_id", ""),
        }
    )
    return _with_surface_view(enriched)


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched.setdefault("relation_state", _canonical_segment(str(item.get("canonical_key") or ""), index=1) or "working-alignment")
    enriched.setdefault("relation_alignment", "working-alignment")
    enriched.setdefault("relation_watchfulness", "low")
    enriched.setdefault("relation_pressure", "low")
    enriched.setdefault("relation_summary", str(item.get("summary") or ""))
    enriched.setdefault("relation_confidence", str(item.get("confidence") or "low"))
    enriched.setdefault("relation_dimension", "current-user")
    enriched.setdefault(
        "source_anchor",
        _source_anchor_from_support_summary(str(item.get("support_summary") or "")),
    )
    enriched.setdefault(
        "grounding_mode",
        _grounding_mode_from_support_summary(str(item.get("support_summary") or "")) or "user-understanding",
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["canonical_relation_state"] = "not-canonical-relationship-truth"
    return enriched


def _relation_state_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_relation_state": "not-canonical-relationship-truth",
        "summary_extra": {
            "current_state": str(current.get("relation_state") or "none"),
            "current_alignment": str(current.get("relation_alignment") or "working-alignment"),
            "current_watchfulness": str(current.get("relation_watchfulness") or "low"),
            "current_pressure": str(current.get("relation_pressure") or "low"),
            "current_confidence": str(current.get("relation_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_relation_state": "not-canonical-relationship-truth",
        },
    }


def _focus_key(*items: dict[str, object] | None) -> str:
    for item in items:
        value = _canonical_segment(str((item or {}).get("canonical_key") or ""), index=-1)
        if value:
            return value
    return "current-user"


def _support_anchor(item: dict[str, object] | None) -> str:
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
    name="relation-state",
    slug="relation-state",
    signal_id_prefix="relation-state-signal",
    event_prefix="relation_state_signal",
    default_signal_type="relation-state",
    list_fn=list_runtime_relation_state_signals,
    upsert_fn=upsert_runtime_relation_state_signal,
    update_status_fn=update_runtime_relation_state_signal_status,
    supersede_fn=supersede_runtime_relation_state_signals_for_focus,
    supersede_group_field="focus_key",
    supersede_group_kw="focus_key",
    extract_fn=lambda spec, ctx: [c] if (c := _extract_candidate_for_run(run_id=str(ctx.get("run_id") or ""))) else [],
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active"}),
    stale_status_reason="Marked stale after bounded relation-state inactivity window.",
    surface_status_order=("active", "stale", "superseded"),
    surface_active_statuses=frozenset({"active"}),
    empty_current_label="No active relation-state support",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_relation_state_surface_extra,
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)
