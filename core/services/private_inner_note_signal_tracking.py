"""Private inner-note signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the inner-note-specific candidate derivation (grounded in the latest visible work
note plus optional cognitive-core signal) and the note-projection enrichment stay
here — that is the part unique to this signal.

This is a single-candidate ``_for_focus`` S-family variant: the refresh window is
``{active}``-only, the surface omits ``recent_history``, and both the read surface
and the persist return carry a bounded note projection (``note_type`` /
``note_confidence`` / ``inner_voice_source_state`` / ``contamination_state`` …).
The read surface uses ``item_view_fn`` + ``surface_extra_fn``; the persist return
applies the 2-arg ``_with_runtime_view`` in the thin ``track`` wrapper.
"""
from __future__ import annotations

from datetime import UTC, datetime

from core.memory.private_inner_note import build_private_inner_note_payload
from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.runtime.db import (
    list_runtime_private_inner_note_signals,
    list_runtime_private_initiative_tension_signals,
    list_runtime_private_inner_interplay_signals,
    recent_visible_work_notes,
    supersede_runtime_private_inner_note_signals_for_focus,
    update_runtime_private_inner_note_signal_status,
    upsert_runtime_private_inner_note_signal,
)

_STALE_AFTER_DAYS = 7


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_private_inner_note_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    # Delegate the upsert/supersede/event scaffolding to the framework, but keep
    # the original 2-arg runtime-view enrichment (needs the originating candidate)
    # on the returned items — matching the pre-migration output exactly.
    normalized_session_id = str(session_id or "").strip()
    visible_note = _latest_visible_work_note_for_run(run_id)
    if visible_note is None:
        return {
            "created": 0,
            "updated": 0,
            "items": [],
            "summary": "No bounded private inner note grounding was available for this visible turn.",
        }

    candidate = _candidate_from_visible_note(visible_note)
    persisted = _stf.persist_signals(
        _SPEC, signals=[candidate], session_id=normalized_session_id, run_id=run_id
    )
    items = [_with_runtime_view(item, candidate) for item in persisted]
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            "Tracked 1 bounded private inner note support signal."
            if items
            else "No bounded private inner note support signal warranted tracking."
        ),
    }


def refresh_runtime_private_inner_note_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_private_inner_note_signal_surface(
    *, limit: int = 8
) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _latest_visible_work_note_for_run(run_id: str) -> dict[str, object] | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    for item in recent_visible_work_notes(limit=8):
        if str(item.get("run_id") or "").strip() != normalized_run_id:
            continue
        if not str(item.get("work_id") or "").strip():
            continue
        return item
    return None


def _latest_cognitive_signal_for_run(run_id: str) -> dict[str, object] | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None

    for item in list_runtime_private_inner_interplay_signals(limit=8):
        if str(item.get("run_id") or "") != normalized_run_id:
            continue
        if str(item.get("status") or "") != "active":
            continue
        return item

    for item in list_runtime_private_initiative_tension_signals(limit=8):
        if str(item.get("run_id") or "") != normalized_run_id:
            continue
        if str(item.get("status") or "") != "active":
            continue
        return item

    return None


def _cognitive_source_label(signal: dict[str, object]) -> str:
    signal_type = str(signal.get("signal_type") or "").strip()
    if signal_type == "private-inner-interplay":
        target = str(signal.get("focus") or signal.get("title") or "something").strip()
        if target.startswith("Private inner interplay support:"):
            target = target[len("Private inner interplay support:") :].strip()
        return f"inner interplay around {target}"
    if signal_type == "private-initiative-tension":
        target = str(
            signal.get("tension_target") or signal.get("title") or "something"
        ).strip()
        if target.startswith("Private initiative tension support:"):
            target = target[len("Private initiative tension support:") :].strip()
        tension_type = str(signal.get("tension_type") or "pull")
        if tension_type == "unresolved":
            return f"unresolved tension around {target}"
        return f"{tension_type} around {target}"
    return "cognitive signal"


def _candidate_from_visible_note(visible_note: dict[str, object]) -> dict[str, object]:
    payload = build_private_inner_note_payload(
        run_id=str(visible_note.get("run_id") or ""),
        work_id=str(visible_note.get("work_id") or ""),
        status=str(visible_note.get("status") or ""),
        user_message_preview=str(visible_note.get("user_message_preview") or "").strip()
        or None,
        work_preview=str(visible_note.get("work_preview") or "").strip() or None,
        capability_id=str(visible_note.get("capability_id") or "").strip() or None,
        created_at=str(visible_note.get("created_at") or datetime.now(UTC).isoformat()),
    )
    run_id = str(visible_note.get("run_id") or "")
    focus = str(payload.get("focus") or "visible-work")
    note_summary = str(payload.get("private_summary") or "").strip()
    work_preview = str(visible_note.get("work_preview") or "").strip()
    user_preview = str(visible_note.get("user_message_preview") or "").strip()
    status = str(visible_note.get("status") or "unknown").strip().lower() or "unknown"
    evidence_summary = _quote(work_preview or user_preview or note_summary)
    source_anchor = _source_anchor(visible_note)

    cognitive_signal = _latest_cognitive_signal_for_run(run_id)
    if cognitive_signal:
        cognitive_source = _cognitive_source_label(cognitive_signal)
        summary = f"I'm drawn back to {focus.replace('-', ' ')} — {cognitive_source}."
        rationale = "A private inner note returns as bounded reflection, informed by cognitive core signals and visible work."
        support_summary = _merge_fragments(
            f"I notice {cognitive_source}.",
            source_anchor,
            "contamination-state=decontaminated-from-visible-summary",
            f"cognitive-connection={cognitive_signal.get('signal_type', 'unknown')}",
        )
        status_reason = f"I register {cognitive_signal.get('signal_type', 'cognitive-signal')} alongside visible work."
        inner_voice_source_state = "cognitive-core-connected"
    else:
        summary = f"I notice a quiet inner thread around {focus.replace('-', ' ')}."
        rationale = "A private inner note may return as bounded reflection when grounded in visible work."
        support_summary = _merge_fragments(
            "I hold this as bounded reflection.",
            source_anchor,
            "contamination-state=decontaminated-from-visible-summary",
            f"source-anchor={source_anchor}",
        )
        status_reason = f"I notice the work around {focus.replace('-', ' ')} has settled into this form."
        inner_voice_source_state = "private-runtime-grounded"

    return {
        "signal_type": "private-inner-note",
        "canonical_key": f"private-inner-note:work-status:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Private inner note: {focus.replace('-', ' ')}",
        "summary": summary,
        "rationale": rationale,
        "source_kind": "runtime-derived-support",
        "confidence": _confidence_from_uncertainty(
            str(payload.get("uncertainty") or "")
        ),
        "evidence_summary": evidence_summary,
        "support_summary": support_summary,
        "support_count": 1,
        "session_count": 1,
        "status_reason": status_reason,
        "note_type": str(payload.get("note_kind") or "work-status-signal"),
        "note_summary": note_summary,
        "signal_confidence": _confidence_from_uncertainty(
            str(payload.get("uncertainty") or "")
        ),
        "source_anchor": source_anchor,
        "identity_alignment": str(
            payload.get("identity_alignment") or "subordinate-to-visible"
        ),
        "inner_voice_source_state": inner_voice_source_state,
        "contamination_state": "decontaminated-from-visible-summary",
        "work_signal": str(payload.get("work_signal") or ""),
        "uncertainty": str(payload.get("uncertainty") or "medium"),
        "focus": focus,
    }


def _with_runtime_view(
    item: dict[str, object], signal: dict[str, object]
) -> dict[str, object]:
    enriched = dict(item)
    enriched["note_type"] = str(signal.get("note_type") or "work-status-signal")
    enriched["note_summary"] = str(signal.get("note_summary") or "")
    enriched["note_confidence"] = str(
        signal.get("signal_confidence") or signal.get("confidence") or "low"
    )
    enriched["source_anchor"] = str(signal.get("source_anchor") or "")
    enriched["identity_alignment"] = str(
        signal.get("identity_alignment") or "subordinate-to-visible"
    )
    enriched["inner_voice_source_state"] = str(
        signal.get("inner_voice_source_state") or "private-runtime-grounded"
    )
    enriched["contamination_state"] = str(
        signal.get("contamination_state") or "unknown"
    )
    enriched["work_signal"] = str(signal.get("work_signal") or "")
    enriched["uncertainty"] = str(signal.get("uncertainty") or "medium")
    enriched["focus"] = str(signal.get("focus") or "")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    support_summary = str(item.get("support_summary") or "")
    note_summary = str(item.get("note_summary") or item.get("summary") or "").strip()
    enriched["note_type"] = str(item.get("note_type") or "work-status-signal")
    enriched["note_summary"] = note_summary
    enriched["fact_summary"] = note_summary
    enriched["note_confidence"] = str(
        item.get("note_confidence") or item.get("confidence") or "low"
    )
    enriched["signal_confidence"] = str(
        item.get("note_confidence") or item.get("confidence") or "low"
    )
    enriched["source_anchor"] = str(
        item.get("source_anchor")
        or _find_support_value(support_summary, "source-anchor")
        or support_summary
        or ""
    )
    enriched["identity_alignment"] = str(
        item.get("identity_alignment") or "subordinate-to-visible"
    )
    enriched["inner_voice_source_state"] = str(
        item.get("inner_voice_source_state")
        or _find_support_value(support_summary, "inner-voice-source")
        or "private-runtime-grounded"
    )
    enriched["contamination_state"] = str(
        item.get("contamination_state")
        or _find_support_value(support_summary, "contamination-state")
        or "unknown"
    )
    enriched["work_signal"] = str(item.get("work_signal") or "")
    enriched["uncertainty"] = str(item.get("uncertainty") or "medium")
    enriched["focus"] = str(item.get("focus") or "")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["summary"] = note_summary or str(item.get("summary") or "")
    return enriched


def _private_inner_note_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "summary_extra": {
            "current_note_type": str(current.get("note_type") or "none"),
            "current_confidence": str(current.get("note_confidence") or "low"),
            "current_source_state": str(
                current.get("inner_voice_source_state") or "none"
            ),
            "current_contamination_state": str(
                current.get("contamination_state") or "none"
            ),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


def _confidence_from_uncertainty(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "low":
        return "medium"
    return "low"


def _source_anchor(visible_note: dict[str, object]) -> str:
    note_id = str(visible_note.get("note_id") or "").strip()
    work_id = str(visible_note.get("work_id") or "").strip()
    capability_id = str(visible_note.get("capability_id") or "").strip()
    anchor = f"Visible work note {note_id or 'unknown-note'}"
    if work_id:
        anchor += f" for {work_id}"
    if capability_id:
        anchor += f" via capability {capability_id}"
    return anchor


def _merge_fragments(*parts: str) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return " | ".join(merged[:3])


def _quote(text: str) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ""
    bounded = normalized[:157].rstrip()
    if len(normalized) > 157:
        bounded += "..."
    return f'"{bounded}"'


def _find_support_value(summary: str, key: str) -> str:
    needle = f"{key}="
    for part in str(summary or "").split("|"):
        normalized = part.strip()
        if normalized.startswith(needle):
            return normalized[len(needle) :].strip()
    return ""


# ── spec: single-candidate _for_focus S-family + surface hooks ─────────────────
_SPEC = SignalTrackingSpec(
    name="private-inner-note",
    slug="private-inner-note",
    signal_id_prefix="private-inner-note-signal",
    event_prefix="private_inner_note_signal",
    default_signal_type="private-inner-note",
    list_fn=list_runtime_private_inner_note_signals,
    upsert_fn=upsert_runtime_private_inner_note_signal,
    update_status_fn=update_runtime_private_inner_note_signal_status,
    supersede_fn=supersede_runtime_private_inner_note_signals_for_focus,
    supersede_group_field="focus_key",
    supersede_group_kw="focus_key",
    extract_fn=lambda spec, ctx: (
        [_candidate_from_visible_note(vn)]
        if (vn := _latest_visible_work_note_for_run(str(ctx.get("run_id") or "")))
        else []
    ),
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active"}),
    stale_status_reason="Marked stale after bounded private inner note inactivity window.",
    surface_status_order=("active", "stale", "superseded"),
    surface_active_statuses=frozenset({"active"}),
    empty_current_label="No active private inner note support",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_private_inner_note_surface_extra,
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)
