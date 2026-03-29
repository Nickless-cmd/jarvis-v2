from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.memory.private_inner_note import build_private_inner_note_payload
from core.runtime.db import (
    list_runtime_private_inner_note_signals,
    recent_visible_work_notes,
    supersede_runtime_private_inner_note_signals_for_focus,
    update_runtime_private_inner_note_signal_status,
    upsert_runtime_private_inner_note_signal,
)

_STALE_AFTER_DAYS = 7


def track_runtime_private_inner_note_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
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
    persisted = _persist_private_inner_note_signals(
        signals=[candidate],
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in persisted if item.get("was_created")]),
        "updated": len([item for item in persisted if item.get("was_updated")]),
        "items": persisted,
        "summary": (
            "Tracked 1 bounded private inner note support signal."
            if persisted
            else "No bounded private inner note support signal warranted tracking."
        ),
    }


def refresh_runtime_private_inner_note_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_private_inner_note_signals(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(
            str(item.get("updated_at") or item.get("created_at") or "")
        )
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_private_inner_note_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded private inner note inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "private_inner_note_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_private_inner_note_signal_surface(
    *, limit: int = 8
) -> dict[str, object]:
    refresh_runtime_private_inner_note_signal_statuses()
    items = list_runtime_private_inner_note_signals(limit=max(limit, 1))
    enriched_items = [_with_surface_view(item) for item in items]
    active = [
        item for item in enriched_items if str(item.get("status") or "") == "active"
    ]
    stale = [
        item for item in enriched_items if str(item.get("status") or "") == "stale"
    ]
    superseded = [
        item for item in enriched_items if str(item.get("status") or "") == "superseded"
    ]
    ordered = [*active, *stale, *superseded]
    latest = next(iter(active or stale or superseded), None)
    return {
        "active": bool(active),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str(
                (latest or {}).get("title") or "No active private inner note support"
            ),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_note_type": str((latest or {}).get("note_type") or "none"),
            "current_confidence": str((latest or {}).get("note_confidence") or "low"),
            "current_source_state": str(
                (latest or {}).get("inner_voice_source_state") or "none"
            ),
            "current_contamination_state": str(
                (latest or {}).get("contamination_state") or "none"
            ),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


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
    focus = str(payload.get("focus") or "visible-work")
    note_summary = str(payload.get("private_summary") or "").strip()
    work_preview = str(visible_note.get("work_preview") or "").strip()
    user_preview = str(visible_note.get("user_message_preview") or "").strip()
    status = str(visible_note.get("status") or "unknown").strip().lower() or "unknown"
    evidence_summary = _quote(work_preview or user_preview or note_summary)
    source_anchor = _source_anchor(visible_note)
    return {
        "signal_type": "private-inner-note",
        "canonical_key": f"private-inner-note:work-status:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Private inner note: {focus.replace('-', ' ')}",
        "summary": f"I notice a quiet inner thread around {focus.replace('-', ' ')}.",
        "rationale": "A private inner note may return as bounded reflection when grounded in visible work.",
        "source_kind": "runtime-derived-support",
        "confidence": _confidence_from_uncertainty(
            str(payload.get("uncertainty") or "")
        ),
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "Grounded in visible work, kept bounded.",
            source_anchor,
            "contamination-state=decontaminated-from-visible-summary",
            f"source-anchor={source_anchor}",
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": f"Grounded in visible work status {status}.",
        "note_type": str(payload.get("note_kind") or "work-status-signal"),
        "note_summary": note_summary,
        "signal_confidence": _confidence_from_uncertainty(
            str(payload.get("uncertainty") or "")
        ),
        "source_anchor": source_anchor,
        "identity_alignment": str(
            payload.get("identity_alignment") or "subordinate-to-visible"
        ),
        "inner_voice_source_state": "private-runtime-grounded",
        "contamination_state": "decontaminated-from-visible-summary",
        "work_signal": str(payload.get("work_signal") or ""),
        "uncertainty": str(payload.get("uncertainty") or "medium"),
        "focus": focus,
    }


def _persist_private_inner_note_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_private_inner_note_signal(
            signal_id=f"private-inner-note-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "private-inner-note"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "runtime-derived-support"),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=str(signal.get("support_summary") or ""),
            status_reason=str(signal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
        )
        superseded_count = supersede_runtime_private_inner_note_signals_for_focus(
            focus_key=str(signal.get("focus_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded private inner note support signal for the same visible-work focus.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "private_inner_note_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "private_inner_note_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "private_inner_note_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


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


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
