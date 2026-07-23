"""Private inner-interplay signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the inner-interplay-specific candidate derivation (grounded in an active inner-note
plus an active initiative-tension) and the interplay-projection enrichment stay
here — that is the part unique to this signal.

This is a single-candidate ``_for_relation`` S-family variant: supersede grouping
is by ``relation_key``, the refresh window is ``{active}``-only, the surface omits
``recent_history``, and both the read surface and the persist return carry a
bounded interplay projection (``interplay_type`` / ``interplay_summary`` /
``interplay_confidence`` …). The read surface uses ``item_view_fn`` +
``surface_extra_fn``; the persist return applies the 2-arg ``_with_runtime_view``
in the thin ``track`` wrapper.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.runtime.db import (
    list_runtime_private_inner_interplay_signals,
    list_runtime_private_inner_note_signals,
    list_runtime_private_initiative_tension_signals,
    supersede_runtime_private_inner_interplay_signals_for_relation,
    update_runtime_private_inner_interplay_signal_status,
    upsert_runtime_private_inner_interplay_signal,
)

_STALE_AFTER_DAYS = 7


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_private_inner_interplay_signals_for_visible_turn(
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
            "summary": "No bounded private inner interplay grounding was available for this visible turn.",
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
            "Tracked 1 bounded private inner interplay support signal."
            if items
            else "No bounded private inner interplay support signal warranted tracking."
        ),
    }


def refresh_runtime_private_inner_interplay_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_private_inner_interplay_signal_surface(
    *, limit: int = 8
) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    inner_note = _latest_inner_note_support(run_id=run_id)
    initiative_tension = _latest_initiative_tension_support(run_id=run_id)
    if inner_note is None or initiative_tension is None:
        return None

    note_focus = _note_focus(inner_note)
    tension_type = str(
        initiative_tension.get("tension_type") or ""
    ).strip() or _canonical_tension_type(
        str(initiative_tension.get("canonical_key") or "")
    )
    relation_key = _relation_key(note_focus=note_focus, tension=initiative_tension)
    interplay_type = (
        "unresolved-support" if tension_type == "unresolved" else "aligned-support"
    )
    source_anchor = _merge_fragments(
        _support_anchor(inner_note),
        _support_anchor(initiative_tension),
    )
    note_summary = _note_summary(inner_note)
    tension_summary = str(
        initiative_tension.get("tension_summary")
        or initiative_tension.get("summary")
        or ""
    ).strip()
    interplay_summary = _merge_fragments(note_summary, tension_summary)[:220]
    target_label = str(
        initiative_tension.get("tension_target")
        or _title_target(str(initiative_tension.get("title") or ""))
        or note_focus.replace("-", " ")
    ).strip()[:96]
    confidence = _stronger_confidence(
        str(inner_note.get("note_confidence") or inner_note.get("confidence") or "low"),
        str(
            initiative_tension.get("tension_confidence")
            or initiative_tension.get("confidence")
            or "low"
        ),
    )

    return {
        "signal_type": "private-inner-interplay",
        "canonical_key": f"private-inner-interplay:{interplay_type}:{relation_key}",
        "relation_key": relation_key,
        "status": "active",
        "title": f"Private inner interplay: {target_label}",
        "summary": (
            f"I can feel both steadiness and tension gathering around {target_label.lower()}."
        ),
        "rationale": (
            "A private inner interplay may return when active inner-note and initiative-tension are both grounded in current visible/runtime truth, without becoming a planner or hidden self-engine."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": confidence,
        "evidence_summary": _merge_fragments(
            str(inner_note.get("evidence_summary") or ""),
            str(initiative_tension.get("evidence_summary") or ""),
        ),
        "support_summary": _merge_fragments(
            "I notice both inner-note and initiative-tension present.",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "I register this as bounded interplay with no planner authority, execution authority, or canonical-self authority."
        ),
        "interplay_type": interplay_type,
        "interplay_summary": interplay_summary,
        "interplay_confidence": confidence,
        "note_signal_id": str(inner_note.get("signal_id") or ""),
        "tension_signal_id": str(initiative_tension.get("signal_id") or ""),
        "focus": note_focus,
        "source_anchor": source_anchor,
        "grounding_mode": "inner-note+initiative-tension",
    }


def _latest_inner_note_support(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_inner_note_signals(limit=12):
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


def _with_runtime_view(
    item: dict[str, object], signal: dict[str, object]
) -> dict[str, object]:
    enriched = dict(item)
    enriched["interplay_type"] = str(signal.get("interplay_type") or "aligned-support")
    enriched["interplay_summary"] = str(signal.get("interplay_summary") or "")
    enriched["interplay_confidence"] = str(
        signal.get("interplay_confidence") or signal.get("confidence") or "low"
    )
    enriched["note_signal_id"] = str(signal.get("note_signal_id") or "")
    enriched["tension_signal_id"] = str(signal.get("tension_signal_id") or "")
    enriched["focus"] = str(signal.get("focus") or "")
    enriched["source_anchor"] = str(signal.get("source_anchor") or "")
    enriched["grounding_mode"] = str(
        signal.get("grounding_mode") or "inner-note+initiative-tension"
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    canonical_key = str(item.get("canonical_key") or "")
    inferred_type = _canonical_interplay_type(canonical_key) or "aligned-support"
    enriched["interplay_type"] = str(item.get("interplay_type") or inferred_type)
    enriched["interplay_summary"] = str(
        item.get("interplay_summary") or item.get("summary") or ""
    )
    enriched["interplay_confidence"] = str(
        item.get("interplay_confidence") or item.get("confidence") or "low"
    )
    enriched["note_signal_id"] = str(item.get("note_signal_id") or "")
    enriched["tension_signal_id"] = str(item.get("tension_signal_id") or "")
    enriched["focus"] = str(item.get("focus") or "")
    enriched["source_anchor"] = str(
        item.get("source_anchor")
        or item.get("support_summary")
        or item.get("signal_id")
        or ""
    )
    enriched["grounding_mode"] = str(
        item.get("grounding_mode") or "inner-note+initiative-tension"
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["source"] = "/mc/runtime.private_inner_interplay_signal"
    return enriched


def _private_inner_interplay_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "summary_extra": {
            "current_interplay_type": str(current.get("interplay_type") or "none"),
            "current_confidence": str(current.get("interplay_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


def _relation_key(*, note_focus: str, tension: dict[str, object]) -> str:
    canonical_key = str(tension.get("canonical_key") or "").strip()
    if canonical_key:
        parts = canonical_key.split(":")
        if parts:
            tail = parts[-1].strip()
            if tail:
                return tail[:96]
    tension_target = str(
        tension.get("tension_target") or tension.get("title") or ""
    ).strip()
    if tension_target:
        return _slug(tension_target)
    return note_focus[:96]


def _note_focus(item: dict[str, object]) -> str:
    canonical_key = str(item.get("canonical_key") or "").strip()
    parts = [part.strip() for part in canonical_key.split(":") if part.strip()]
    if parts:
        tail = parts[-1]
        if tail:
            return tail[:96]
    return "visible-work"


def _note_summary(item: dict[str, object]) -> str:
    status_reason = str(item.get("status_reason") or "").strip()
    if status_reason:
        return status_reason[:220]
    summary = str(item.get("summary") or "").strip()
    if summary:
        return summary[:220]
    title = str(item.get("title") or "").strip()
    return title[:220]


def _support_anchor(item: dict[str, object]) -> str:
    signal_id = str(item.get("signal_id") or "").strip()
    title = str(item.get("title") or "").strip()
    if signal_id and title:
        return f"{signal_id}:{title}"[:140]
    if signal_id:
        return signal_id[:140]
    return title[:140]


def _title_target(title: str) -> str:
    prefix = "Private initiative tension support:"
    value = str(title or "").strip()
    if value.startswith(prefix):
        return value[len(prefix) :].strip()[:96]
    return value[:96]


def _canonical_tension_type(canonical_key: str) -> str:
    parts = [
        part.strip() for part in str(canonical_key or "").split(":") if part.strip()
    ]
    if len(parts) >= 2:
        return parts[1][:32]
    return ""


def _canonical_interplay_type(canonical_key: str) -> str:
    parts = [
        part.strip() for part in str(canonical_key or "").split(":") if part.strip()
    ]
    if len(parts) >= 2:
        return parts[1][:32]
    return ""


def _stronger_confidence(left: str, right: str) -> str:
    ranks = {"low": 0, "medium": 1, "high": 2}
    left_norm = str(left or "low").strip().lower() or "low"
    right_norm = str(right or "low").strip().lower() or "low"
    return (
        left_norm if ranks.get(left_norm, 0) >= ranks.get(right_norm, 0) else right_norm
    )


def _merge_fragments(*parts: str) -> str:
    items: list[str] = []
    seen: set[str] = set()
    for part in parts:
        value = str(part or "").strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        items.append(value)
    return " | ".join(items)[:240]


def _slug(value: str) -> str:
    normalized = "".join(
        char.lower() if char.isalnum() else "-" for char in str(value or "").strip()
    )
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    return normalized.strip("-")[:96] or "visible-work"


# ── spec: single-candidate _for_relation S-family + surface hooks ──────────────
_SPEC = SignalTrackingSpec(
    name="private-inner-interplay",
    slug="private-inner-interplay",
    signal_id_prefix="private-inner-interplay-signal",
    event_prefix="private_inner_interplay_signal",
    default_signal_type="private-inner-interplay",
    list_fn=list_runtime_private_inner_interplay_signals,
    upsert_fn=upsert_runtime_private_inner_interplay_signal,
    update_status_fn=update_runtime_private_inner_interplay_signal_status,
    supersede_fn=supersede_runtime_private_inner_interplay_signals_for_relation,
    supersede_group_field="relation_key",
    supersede_group_kw="relation_key",
    extract_fn=lambda spec, ctx: (
        [c] if (c := _extract_candidate_for_run(run_id=str(ctx.get("run_id") or ""))) else []
    ),
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active"}),
    stale_status_reason="Marked stale after bounded private inner interplay inactivity window.",
    surface_status_order=("active", "stale", "superseded"),
    surface_active_statuses=frozenset({"active"}),
    empty_current_label="No active private inner interplay support",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_private_inner_interplay_surface_extra,
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)
