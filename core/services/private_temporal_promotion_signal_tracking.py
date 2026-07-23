"""Private temporal-promotion signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the temporal-promotion-specific candidate derivation (grounded in active
temporal-curiosity plus private-state support) and the promotion-projection
enrichment stay here — that is the part unique to this signal.

This is a single-candidate ``_for_focus`` S-family variant: the refresh window is
``{active}``-only, the surface omits ``recent_history``, and both the read surface
and the persist return carry a bounded promotion projection (``promotion_type`` /
``promotion_target`` / ``promotion_pull`` / ``promotion_confidence`` …). The read
surface uses ``item_view_fn`` + ``surface_extra_fn``; the persist return applies
the 2-arg ``_with_runtime_view`` in the thin ``track`` wrapper.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.runtime.db import (
    list_runtime_private_initiative_tension_signals,
    list_runtime_private_state_snapshots,
    list_runtime_private_temporal_curiosity_states,
    list_runtime_private_temporal_promotion_signals,
    supersede_runtime_private_temporal_promotion_signals_for_focus,
    update_runtime_private_temporal_promotion_signal_status,
    upsert_runtime_private_temporal_promotion_signal,
)

_STALE_AFTER_DAYS = 7


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_private_temporal_promotion_signals_for_visible_turn(
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
            "summary": "No bounded temporal-promotion grounding was available for this visible turn.",
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
            "Tracked 1 bounded temporal-promotion runtime support signal."
            if items
            else "No bounded temporal-promotion runtime support signal warranted tracking."
        ),
    }


def refresh_runtime_private_temporal_promotion_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_private_temporal_promotion_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    curiosity_state = _latest_temporal_curiosity_state(run_id=run_id)
    private_state = _latest_private_state_snapshot(run_id=run_id)
    initiative_tension = _latest_initiative_tension_support(run_id=run_id)
    if curiosity_state is None or private_state is None:
        return None

    curiosity_type = _value(
        curiosity_state.get("curiosity_type"),
        _canonical_segment(str(curiosity_state.get("canonical_key") or ""), index=1),
        default="watchful-followup",
    )
    curiosity_pull = _value(
        curiosity_state.get("curiosity_pull"),
        _pull_from_curiosity_type(curiosity_type),
        default="low",
    )
    state_tone = _value(
        private_state.get("state_tone"),
        _canonical_segment(str(private_state.get("canonical_key") or ""), index=1),
        default="steady-support",
    )
    state_pressure = _value(
        private_state.get("state_pressure"),
        _pressure_from_state_tone(state_tone),
        default="low",
    )
    tension_type = _value(
        (initiative_tension or {}).get("tension_type"),
        _canonical_segment(str((initiative_tension or {}).get("canonical_key") or ""), index=1),
        default="retention-pull",
    )
    if curiosity_pull != "medium" and state_pressure != "medium":
        return None

    focus = _focus_key(curiosity_state, private_state, initiative_tension or {})
    promotion_type = (
        "carry-forward"
        if curiosity_type == "active-observation" or tension_type == "curiosity-pull"
        else "watchful-maturation"
    )
    promotion_pull = "medium" if curiosity_pull == "medium" or state_pressure == "medium" else "low"
    promotion_target = str(
        curiosity_state.get("curiosity_target")
        or (initiative_tension or {}).get("tension_target")
        or focus.replace("-", " ")
    ).strip()[:96]
    promotion_summary = _merge_fragments(
        str(curiosity_state.get("curiosity_summary") or ""),
        str(private_state.get("state_summary") or ""),
        str((initiative_tension or {}).get("tension_summary") or (initiative_tension or {}).get("summary") or ""),
    )[:220]
    promotion_confidence = _stronger_confidence(
        str(curiosity_state.get("curiosity_confidence") or curiosity_state.get("confidence") or "low"),
        str(private_state.get("state_confidence") or private_state.get("confidence") or "low"),
        str((initiative_tension or {}).get("tension_confidence") or (initiative_tension or {}).get("confidence") or "low"),
    )
    source_anchor = _merge_fragments(
        _support_anchor(curiosity_state),
        _support_anchor(private_state),
        _support_anchor(initiative_tension or {}),
    )

    return {
        "signal_type": "private-temporal-promotion",
        "canonical_key": f"private-temporal-promotion:{promotion_type}:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Private temporal promotion support: {promotion_target}",
        "summary": (
            f"Bounded runtime temporal promotion is carrying a small maturation pull around {promotion_target.lower()}."
        ),
        "rationale": (
            "A bounded temporal-promotion support signal may return only when current temporal-curiosity and private-state support already indicate a live pull, without becoming a planner, scheduler, executor, or broad promotion engine."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": promotion_confidence,
        "evidence_summary": _merge_fragments(
            str(curiosity_state.get("evidence_summary") or ""),
            str(private_state.get("evidence_summary") or ""),
            str((initiative_tension or {}).get("evidence_summary") or ""),
        ),
        "support_summary": _merge_fragments(
            "Derived only from active bounded temporal-curiosity and private-state runtime support.",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "Bounded temporal promotion remains subordinate to visible/runtime truth and carries no planner, execution, prompt, or canonical-self authority."
        ),
        "promotion_type": promotion_type,
        "promotion_target": promotion_target,
        "promotion_pull": promotion_pull,
        "promotion_summary": promotion_summary,
        "promotion_confidence": promotion_confidence,
        "source_anchor": source_anchor,
        "curiosity_state_id": str(curiosity_state.get("state_id") or ""),
        "state_snapshot_id": str(private_state.get("snapshot_id") or ""),
        "tension_signal_id": str((initiative_tension or {}).get("signal_id") or ""),
        "grounding_mode": "temporal-curiosity+private-state",
    }


def _latest_temporal_curiosity_state(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_temporal_curiosity_states(limit=12):
        if str(item.get("run_id") or "") != str(run_id or ""):
            continue
        if str(item.get("status") or "") != "active":
            continue
        return item
    return None


def _latest_private_state_snapshot(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_state_snapshots(limit=12):
        if str(item.get("run_id") or "") != str(run_id or ""):
            continue
        if str(item.get("status") or "") != "active":
            continue
        return item
    return None


def _latest_initiative_tension_support(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_initiative_tension_signals(limit=12):
        if str(item.get("run_id") or "") != str(run_id or ""):
            continue
        if str(item.get("status") or "") != "active":
            continue
        return item
    return None


def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["promotion_type"] = str(signal.get("promotion_type") or "watchful-maturation")
    enriched["promotion_target"] = str(signal.get("promotion_target") or "")
    enriched["promotion_pull"] = str(signal.get("promotion_pull") or "low")
    enriched["promotion_summary"] = str(signal.get("promotion_summary") or "")
    enriched["promotion_confidence"] = str(signal.get("promotion_confidence") or signal.get("confidence") or "low")
    enriched["source_anchor"] = str(signal.get("source_anchor") or "")
    enriched["curiosity_state_id"] = str(signal.get("curiosity_state_id") or "")
    enriched["state_snapshot_id"] = str(signal.get("state_snapshot_id") or "")
    enriched["tension_signal_id"] = str(signal.get("tension_signal_id") or "")
    enriched["grounding_mode"] = str(signal.get("grounding_mode") or "temporal-curiosity+private-state")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    canonical_key = str(item.get("canonical_key") or "")
    inferred_type = _canonical_segment(canonical_key, index=1) or "watchful-maturation"
    enriched["promotion_type"] = str(item.get("promotion_type") or inferred_type)
    enriched["promotion_target"] = str(item.get("promotion_target") or _title_target(str(item.get("title") or "")))
    enriched["promotion_pull"] = str(item.get("promotion_pull") or _pull_from_type(inferred_type))
    enriched["promotion_summary"] = str(item.get("promotion_summary") or item.get("summary") or "")
    enriched["promotion_confidence"] = str(item.get("promotion_confidence") or item.get("confidence") or "low")
    enriched["source_anchor"] = str(item.get("source_anchor") or item.get("support_summary") or item.get("signal_id") or "")
    enriched["curiosity_state_id"] = str(item.get("curiosity_state_id") or "")
    enriched["state_snapshot_id"] = str(item.get("state_snapshot_id") or "")
    enriched["tension_signal_id"] = str(item.get("tension_signal_id") or "")
    enriched["grounding_mode"] = str(item.get("grounding_mode") or "temporal-curiosity+private-state")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["source"] = "/mc/runtime.private_temporal_promotion_signal"
    return enriched


def _private_temporal_promotion_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "summary_extra": {
            "current_promotion_type": str(current.get("promotion_type") or "none"),
            "current_pull": str(current.get("promotion_pull") or "low"),
            "current_confidence": str(current.get("promotion_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


def _support_anchor(item: dict[str, object]) -> str:
    item_id = str(
        item.get("signal_id")
        or item.get("state_id")
        or item.get("snapshot_id")
        or ""
    ).strip()
    title = str(item.get("title") or "").strip()
    if item_id and title:
        return f"{item_id}:{title}"[:140]
    return (item_id or title)[:140]


def _focus_key(*items: dict[str, object]) -> str:
    for item in items:
        canonical_key = str(item.get("canonical_key") or "").strip()
        parts = [part.strip() for part in canonical_key.split(":") if part.strip()]
        if parts:
            tail = parts[-1]
            if tail:
                return tail[:96]
    return "visible-work"


def _stronger_confidence(*values: str) -> str:
    ordered = {"low": 0, "medium": 1, "high": 2}
    best = "low"
    best_score = -1
    for value in values:
        normalized = str(value or "").strip().lower()
        if normalized not in ordered:
            continue
        score = ordered[normalized]
        if score > best_score:
            best = normalized
            best_score = score
    return best


def _canonical_segment(value: str, *, index: int) -> str:
    parts = [part.strip() for part in str(value or "").split(":") if part.strip()]
    if len(parts) <= index:
        return ""
    return parts[index][:96]


def _value(*candidates: object, default: str) -> str:
    for candidate in candidates:
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized[:96]
    return default


def _pull_from_type(promotion_type: str) -> str:
    if str(promotion_type or "").strip() == "carry-forward":
        return "medium"
    return "low"


def _pull_from_curiosity_type(curiosity_type: str) -> str:
    if str(curiosity_type or "").strip() == "active-observation":
        return "medium"
    return "low"


def _pressure_from_state_tone(state_tone: str) -> str:
    if str(state_tone or "").strip() == "steady-pressure":
        return "medium"
    return "low"


def _title_target(title: str) -> str:
    normalized = str(title or "").strip()
    prefix = "Private temporal promotion support:"
    if normalized.startswith(prefix):
        return normalized[len(prefix) :].strip()
    return normalized[:96]


def _merge_fragments(*parts: str) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return " | ".join(merged[:4])


# ── spec: single-candidate _for_focus S-family + surface hooks ─────────────────
_SPEC = SignalTrackingSpec(
    name="private-temporal-promotion",
    slug="private-temporal-promotion",
    signal_id_prefix="private-temporal-promotion-signal",
    event_prefix="private_temporal_promotion_signal",
    default_signal_type="private-temporal-promotion",
    list_fn=list_runtime_private_temporal_promotion_signals,
    upsert_fn=upsert_runtime_private_temporal_promotion_signal,
    update_status_fn=update_runtime_private_temporal_promotion_signal_status,
    supersede_fn=supersede_runtime_private_temporal_promotion_signals_for_focus,
    supersede_group_field="focus_key",
    supersede_group_kw="focus_key",
    extract_fn=lambda spec, ctx: (
        [c] if (c := _extract_candidate_for_run(run_id=str(ctx.get("run_id") or ""))) else []
    ),
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active"}),
    stale_status_reason="Marked stale after bounded temporal-promotion inactivity window.",
    surface_status_order=("active", "stale", "superseded"),
    surface_active_statuses=frozenset({"active"}),
    empty_current_label="No active temporal-promotion support",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_private_temporal_promotion_surface_extra,
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)
