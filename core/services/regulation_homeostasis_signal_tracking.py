"""Regulation/homeostasis signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the regulation-specific candidate derivation and the mood-layer surface/runtime
enrichment stay here — that is the part unique to this signal.

This is a policy-layer ``_for_focus`` S-family variant: supersede grouping is by
``focus_key``, the refresh window is ``{active}``-only, and both the read surface
and the persist return carry a bounded regulation projection (``regulation_state``
/ ``regulation_pressure`` / ``regulation_watchfulness`` … plus ``authority`` /
``layer_role`` / ``canonical_mood_state``). Those are expressed via ``item_view_fn``
+ ``surface_extra_fn`` and the 2-arg ``_with_runtime_view`` applied in the thin
``track`` wrapper.

One extra: the original ``build_surface`` fired an egress-free LivingNeuron liveness
observation (``central_private_observe.observe_hub``) after bucketing. That side
effect is reproduced faithfully through the framework's ``summary_fn`` post-surface
hook — same args, same best-effort try/except, surface returned unchanged.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.runtime.db import (
    list_runtime_executive_contradiction_signals,
    list_runtime_inner_visible_support_signals,
    list_runtime_private_initiative_tension_signals,
    list_runtime_private_state_snapshots,
    list_runtime_private_temporal_curiosity_states,
    list_runtime_regulation_homeostasis_signals,
    supersede_runtime_regulation_homeostasis_signals_for_focus,
    update_runtime_regulation_homeostasis_signal_status,
    upsert_runtime_regulation_homeostasis_signal,
)

_STALE_AFTER_DAYS = 7
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_regulation_homeostasis_signals_for_visible_turn(
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
            "summary": "No bounded regulation/homeostasis grounding was available for this visible turn.",
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
            "Tracked 1 bounded regulation/homeostasis runtime signal."
            if items
            else "No bounded regulation/homeostasis runtime signal warranted tracking."
        ),
    }


def refresh_runtime_regulation_homeostasis_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_regulation_homeostasis_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    private_state = _latest_private_state_snapshot(run_id=run_id)
    if private_state is None:
        return None

    focus = _focus_key(private_state)
    initiative_tension = _latest_initiative_tension_signal(run_id=run_id, focus_key=focus)
    temporal_curiosity = _latest_temporal_curiosity_state(run_id=run_id, focus_key=focus)
    executive_contradiction = _latest_executive_contradiction_signal(run_id=run_id, focus_key=focus)
    inner_visible_support = _latest_inner_visible_support_signal(run_id=run_id, focus_key=focus)

    state_tone = _value(private_state.get("state_tone"), default="steady-support")
    state_pressure = _value(private_state.get("state_pressure"), default="low")
    tension_type = _value(
        initiative_tension.get("tension_type") if initiative_tension else "",
        _canonical_segment(str((initiative_tension or {}).get("canonical_key") or ""), index=1),
        default="none",
    )
    curiosity_pull = _value(
        temporal_curiosity.get("curiosity_pull") if temporal_curiosity else "",
        default="low",
    )
    contradiction_pressure = _value(
        executive_contradiction.get("control_pressure") if executive_contradiction else "",
        default="low",
    )
    contradiction_status = _value(
        executive_contradiction.get("status") if executive_contradiction else "",
        default="none",
    )
    visible_watchfulness = _value(
        inner_visible_support.get("support_watchfulness") if inner_visible_support else "",
        default="low",
    )

    regulation_pressure = _derive_regulation_pressure(
        state_pressure=state_pressure,
        tension_type=tension_type,
        contradiction_pressure=contradiction_pressure,
    )
    regulation_watchfulness = _derive_regulation_watchfulness(
        contradiction_status=contradiction_status,
        contradiction_pressure=contradiction_pressure,
        visible_watchfulness=visible_watchfulness,
    )
    regulation_pacing = _derive_regulation_pacing(
        pressure=regulation_pressure,
        watchfulness=regulation_watchfulness,
        curiosity_pull=curiosity_pull,
    )
    regulation_state = _derive_regulation_state(
        state_tone=state_tone,
        pressure=regulation_pressure,
        watchfulness=regulation_watchfulness,
        pacing=regulation_pacing,
    )
    regulation_confidence = _stronger_confidence(
        str(private_state.get("state_confidence") or private_state.get("confidence") or "low"),
        str((initiative_tension or {}).get("tension_confidence") or (initiative_tension or {}).get("confidence") or "low"),
        str((temporal_curiosity or {}).get("curiosity_confidence") or (temporal_curiosity or {}).get("confidence") or "low"),
        str((executive_contradiction or {}).get("control_confidence") or (executive_contradiction or {}).get("confidence") or "low"),
        str((inner_visible_support or {}).get("support_confidence") or (inner_visible_support or {}).get("confidence") or "low"),
    )
    grounding_mode = _grounding_mode(
        has_tension=initiative_tension is not None,
        has_curiosity=temporal_curiosity is not None,
        has_executive_contradiction=executive_contradiction is not None,
        has_inner_visible_support=inner_visible_support is not None,
    )
    source_anchor = _merge_fragments(
        _support_anchor(private_state),
        _support_anchor(initiative_tension) if initiative_tension else "",
        _support_anchor(temporal_curiosity) if temporal_curiosity else "",
        _support_anchor(executive_contradiction) if executive_contradiction else "",
        _support_anchor(inner_visible_support) if inner_visible_support else "",
    )
    evidence_summary = _merge_fragments(
        str(private_state.get("evidence_summary") or ""),
        str((initiative_tension or {}).get("evidence_summary") or ""),
        str((temporal_curiosity or {}).get("evidence_summary") or ""),
        str((executive_contradiction or {}).get("evidence_summary") or ""),
        str((inner_visible_support or {}).get("evidence_summary") or ""),
    )

    return {
        "signal_type": "regulation-homeostasis",
        "canonical_key": f"regulation-homeostasis:{regulation_state}:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Regulation support: {focus.replace('-', ' ')}",
        "summary": (
            f"Bounded regulation/homeostasis runtime support is holding a small regulation state around {focus.replace('-', ' ')}."
        ),
        "rationale": (
            "A bounded regulation/homeostasis signal may be derived only from already-returned private-state runtime support, optional initiative-tension and temporal-curiosity sharpening, optional executive-contradiction watchfulness pressure, and optional inner-visible support sharpening, without becoming canonical mood, personality, workflow authority, or planner authority."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": regulation_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Derived only from bounded private-state runtime support, optional initiative-tension and temporal-curiosity sharpening, and small executive-contradiction or inner-visible watchfulness sharpening.",
            f"grounding-mode={grounding_mode}",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "Bounded regulation/homeostasis remains subordinate to visible/runtime truth, is non-authoritative runtime support only, and is not canonical mood or personality."
        ),
        "regulation_state": regulation_state,
        "regulation_pressure": regulation_pressure,
        "regulation_watchfulness": regulation_watchfulness,
        "regulation_pacing": regulation_pacing,
        "regulation_summary": _bounded_regulation_summary(
            focus=focus,
            regulation_state=regulation_state,
            regulation_pressure=regulation_pressure,
            regulation_watchfulness=regulation_watchfulness,
            regulation_pacing=regulation_pacing,
        ),
        "regulation_confidence": regulation_confidence,
        "source_anchor": source_anchor,
        "state_snapshot_id": str(private_state.get("snapshot_id") or ""),
        "initiative_tension_signal_id": str((initiative_tension or {}).get("signal_id") or ""),
        "temporal_curiosity_state_id": str((temporal_curiosity or {}).get("state_id") or ""),
        "executive_contradiction_signal_id": str((executive_contradiction or {}).get("signal_id") or ""),
        "inner_visible_support_signal_id": str((inner_visible_support or {}).get("signal_id") or ""),
        "grounding_mode": grounding_mode,
    }


def _latest_private_state_snapshot(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_state_snapshots(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        return item
    return None


def _latest_initiative_tension_signal(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_private_initiative_tension_signals(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
            continue
        return item
    return None


def _latest_temporal_curiosity_state(*, run_id: str, focus_key: str) -> dict[str, object] | None:
    for item in list_runtime_private_temporal_curiosity_states(limit=18):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        if _focus_key(item) != focus_key:
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


def _derive_regulation_pressure(
    *,
    state_pressure: str,
    tension_type: str,
    contradiction_pressure: str,
) -> str:
    if state_pressure == "medium" or tension_type == "unresolved" or contradiction_pressure in {"medium", "high"}:
        return "medium"
    return "low"


def _derive_regulation_watchfulness(
    *,
    contradiction_status: str,
    contradiction_pressure: str,
    visible_watchfulness: str,
) -> str:
    if contradiction_status in {"active", "softening"} and contradiction_pressure in {"medium", "high"}:
        return "medium"
    if visible_watchfulness == "medium":
        return "medium"
    return "low"


def _derive_regulation_pacing(
    *,
    pressure: str,
    watchfulness: str,
    curiosity_pull: str,
) -> str:
    if watchfulness == "medium":
        return "slow-and-check"
    if pressure == "medium" and curiosity_pull == "low":
        return "settling-needed"
    if curiosity_pull == "medium":
        return "careful-forward"
    return "steady"


def _derive_regulation_state(
    *,
    state_tone: str,
    pressure: str,
    watchfulness: str,
    pacing: str,
) -> str:
    if watchfulness == "medium" and pressure == "medium":
        return "watchful-pressure"
    if pressure == "medium" or state_tone == "steady-pressure":
        return "steady-pressure"
    if pacing == "settling-needed":
        return "settling-support"
    return "steady-support"


def _bounded_regulation_summary(
    *,
    focus: str,
    regulation_state: str,
    regulation_pressure: str,
    regulation_watchfulness: str,
    regulation_pacing: str,
) -> str:
    label = focus.replace("-", " ")
    return (
        f"{label} is currently held in a bounded {regulation_state} regulation state, with {regulation_pressure} pressure, "
        f"{regulation_watchfulness} watchfulness, and {regulation_pacing} pacing."
    )


def _grounding_mode(
    *,
    has_tension: bool,
    has_curiosity: bool,
    has_executive_contradiction: bool,
    has_inner_visible_support: bool,
) -> str:
    parts = ["private-state"]
    if has_tension:
        parts.append("initiative-tension")
    if has_curiosity:
        parts.append("temporal-curiosity")
    if has_executive_contradiction:
        parts.append("executive-contradiction")
    if has_inner_visible_support:
        parts.append("inner-visible-sharpening")
    return "+".join(parts)


# ── mood-layer enrichment (unique — persist return + read surface) ────────────
def _with_runtime_view(
    record: dict[str, object],
    signal: dict[str, object],
) -> dict[str, object]:
    enriched = dict(record)
    enriched.update(
        {
            "regulation_state": signal.get("regulation_state", "steady-support"),
            "regulation_pressure": signal.get("regulation_pressure", "low"),
            "regulation_watchfulness": signal.get("regulation_watchfulness", "low"),
            "regulation_pacing": signal.get("regulation_pacing", "steady"),
            "regulation_summary": signal.get("regulation_summary", ""),
            "regulation_confidence": signal.get("regulation_confidence", record.get("confidence", "low")),
            "source_anchor": signal.get("source_anchor", ""),
            "grounding_mode": signal.get("grounding_mode", "private-state"),
            "state_snapshot_id": signal.get("state_snapshot_id", ""),
            "initiative_tension_signal_id": signal.get("initiative_tension_signal_id", ""),
            "temporal_curiosity_state_id": signal.get("temporal_curiosity_state_id", ""),
            "executive_contradiction_signal_id": signal.get("executive_contradiction_signal_id", ""),
            "inner_visible_support_signal_id": signal.get("inner_visible_support_signal_id", ""),
        }
    )
    return _with_surface_view(enriched)


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched.setdefault("regulation_state", _canonical_segment(str(item.get("canonical_key") or ""), index=1) or "steady-support")
    enriched.setdefault("regulation_pressure", "low")
    enriched.setdefault("regulation_watchfulness", "low")
    enriched.setdefault("regulation_pacing", "steady")
    enriched.setdefault("regulation_summary", str(item.get("summary") or ""))
    enriched.setdefault("regulation_confidence", str(item.get("confidence") or "low"))
    enriched.setdefault(
        "source_anchor",
        _source_anchor_from_support_summary(str(item.get("support_summary") or "")),
    )
    enriched.setdefault(
        "grounding_mode",
        _grounding_mode_from_support_summary(str(item.get("support_summary") or "")) or "private-state",
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["canonical_mood_state"] = "not-canonical-mood-or-personality"
    return enriched


def _regulation_homeostasis_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "canonical_mood_state": "not-canonical-mood-or-personality",
        "summary_extra": {
            "current_state": str(current.get("regulation_state") or "none"),
            "current_pressure": str(current.get("regulation_pressure") or "low"),
            "current_watchfulness": str(current.get("regulation_watchfulness") or "low"),
            "current_pacing": str(current.get("regulation_pacing") or "steady"),
            "current_confidence": str(current.get("regulation_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "canonical_mood_state": "not-canonical-mood-or-personality",
        },
    }


def _regulation_homeostasis_observe_surface(surface: dict[str, object]) -> dict[str, object]:
    # LivingNeuron Fase A: egress-fri liveness (kun tællere + regulerings-tilstand, ikke privat indhold).
    # Repoets første homeostase-lag — en rule pauser ALLEREDE proaktivitet ved imbalance; nu ser Centralen det.
    summary = surface.get("summary") or {}
    try:
        from core.services.central_private_observe import observe_hub
        observe_hub("regulation_homeostasis", meta={"active": summary.get("active_count", 0), "stale": summary.get("stale_count", 0),
                    "state": str(summary.get("current_state") or "none"),
                    "pressure": str(summary.get("current_pressure") or "low")}, cluster="cognition")
    except Exception:
        pass
    return surface


def _focus_key(item: dict[str, object] | None) -> str:
    return _canonical_segment(str((item or {}).get("canonical_key") or ""), index=-1) or "visible-work"


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


# ── spec: policy-layer S-family knobs + focus-grouped supersede + surface hooks ─
_SPEC = SignalTrackingSpec(
    name="regulation-homeostasis",
    slug="regulation-homeostasis",
    signal_id_prefix="regulation-homeostasis-signal",
    event_prefix="regulation_homeostasis_signal",
    default_signal_type="regulation-homeostasis",
    list_fn=list_runtime_regulation_homeostasis_signals,
    upsert_fn=upsert_runtime_regulation_homeostasis_signal,
    update_status_fn=update_runtime_regulation_homeostasis_signal_status,
    supersede_fn=supersede_runtime_regulation_homeostasis_signals_for_focus,
    supersede_group_field="focus_key",
    supersede_group_kw="focus_key",
    extract_fn=lambda spec, ctx: [c] if (c := _extract_candidate_for_run(run_id=str(ctx.get("run_id") or ""))) else [],
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active"}),
    stale_status_reason="Marked stale after bounded regulation/homeostasis inactivity window.",
    surface_status_order=("active", "stale", "superseded"),
    surface_active_statuses=frozenset({"active"}),
    empty_current_label="No active regulation/homeostasis support",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_regulation_homeostasis_surface_extra,
    summary_fn=_regulation_homeostasis_observe_surface,
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)
