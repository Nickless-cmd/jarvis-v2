from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_open_loop_signals,
    list_runtime_private_inner_note_signals,
    list_runtime_private_initiative_tension_signals,
    recent_visible_work_notes,
    supersede_runtime_private_initiative_tension_signals_for_domain,
    update_runtime_private_initiative_tension_signal_status,
    upsert_runtime_private_initiative_tension_signal,
)

_STALE_AFTER_DAYS = 7


def track_runtime_private_initiative_tension_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    candidate = _extract_candidate_for_run(run_id=run_id)
    if candidate is None:
        return {
            "created": 0,
            "updated": 0,
            "items": [],
            "summary": "No bounded initiative-tension grounding was available for this visible turn.",
        }

    persisted = _persist_private_initiative_tension_signals(
        signals=[candidate],
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in persisted if item.get("was_created")]),
        "updated": len([item for item in persisted if item.get("was_updated")]),
        "items": persisted,
        "summary": (
            "Tracked 1 bounded private initiative-tension support signal."
            if persisted
            else "No bounded private initiative-tension support signal warranted tracking."
        ),
    }


def refresh_runtime_private_initiative_tension_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_private_initiative_tension_signals(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_private_initiative_tension_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded initiative-tension inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "private_initiative_tension_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_private_initiative_tension_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_private_initiative_tension_signal_statuses()
    items = list_runtime_private_initiative_tension_signals(limit=max(limit, 1))
    enriched_items = [_with_surface_view(item) for item in items]
    active = [item for item in enriched_items if str(item.get("status") or "") == "active"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
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
            "current_signal": str((latest or {}).get("title") or "No active private initiative tension support"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_tension_type": str((latest or {}).get("tension_type") or "none"),
            "current_intensity": str((latest or {}).get("tension_level") or "low"),
            "current_confidence": str((latest or {}).get("tension_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    visible_note = _latest_visible_work_note_for_run(run_id)
    if visible_note is None:
        return None

    active_open_loop = _latest_open_loop_pressure()
    active_focus = _latest_development_focus()
    inner_note_support = _latest_inner_note_support(run_id=run_id)
    if active_open_loop is None and active_focus is None:
        return None

    note_status = str(visible_note.get("status") or "unknown").strip().lower() or "unknown"
    note_focus = str((inner_note_support or {}).get("focus") or visible_note.get("capability_id") or "visible-work").strip() or "visible-work"
    source_anchor = _merge_fragments(
        _source_anchor_from_visible_note(visible_note),
        str((inner_note_support or {}).get("source_anchor") or ""),
        _support_anchor(active_open_loop),
        _support_anchor(active_focus),
    )

    if active_open_loop is not None:
        domain_key = _domain_key(active_open_loop, fallback=note_focus)
        tension_type = "unresolved"
        tension_target = str(active_open_loop.get("title") or active_open_loop.get("summary") or "current bounded loop")[:96]
        tension_level = "medium"
        reason = str(active_open_loop.get("status_reason") or active_open_loop.get("summary") or "A bounded open loop is still carrying visible pressure.")[:160]
        title = f"Private initiative tension support: {tension_target}"
        summary = f"Bounded runtime initiative tension is still carrying unresolved pressure around {tension_target.lower()}."
        rationale = "A bounded initiative-tension support signal may return when visible work and current open-loop pressure still point at unresolved effort, without granting any execution authority."
        confidence = "medium"
    else:
        domain_key = _domain_key(active_focus, fallback=note_focus)
        focus_title = str(active_focus.get("title") or active_focus.get("summary") or "current development focus")[:96]
        tension_type = "curiosity-pull" if note_focus != "visible-work" else "retention-pull"
        tension_target = focus_title
        tension_level = "medium" if note_status in {"failed", "cancelled"} else "low"
        reason = str(active_focus.get("status_reason") or active_focus.get("summary") or "A bounded development focus is still carrying directional pressure.")[:160]
        title = f"Private initiative tension support: {focus_title}"
        summary = f"Bounded runtime initiative tension is still carrying directional pressure around {focus_title.lower()}."
        rationale = "A bounded initiative-tension support signal may return when visible work and a live development focus still point at directional pull, without becoming a planner or executor."
        confidence = "low" if tension_level == "low" else "medium"

    support_summary = _merge_fragments(
        "Derived from visible work plus bounded runtime support layers.",
        source_anchor,
        str((active_open_loop or active_focus or {}).get("support_summary") or ""),
    )
    evidence_summary = _merge_fragments(
        _quote(str(visible_note.get("work_preview") or "") or str(visible_note.get("user_message_preview") or "")),
        str((active_open_loop or active_focus or {}).get("evidence_summary") or ""),
    )
    return {
        "signal_type": "private-initiative-tension",
        "canonical_key": f"private-initiative-tension:{tension_type}:{domain_key}",
        "domain_key": domain_key,
        "status": "active",
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": "runtime-derived-support",
        "confidence": confidence,
        "evidence_summary": evidence_summary,
        "support_summary": support_summary,
        "support_count": 1,
        "session_count": 1,
        "status_reason": f"Bounded initiative tension remains subordinate to visible/runtime truth and carries no execution authority. {reason}",
        "tension_type": tension_type,
        "tension_target": tension_target,
        "tension_level": tension_level,
        "tension_summary": reason,
        "tension_confidence": confidence,
        "source_anchor": source_anchor,
        "focus": note_focus,
        "grounding_mode": "visible-work+runtime-support",
    }


def _persist_private_initiative_tension_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_private_initiative_tension_signal(
            signal_id=f"private-initiative-tension-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "private-initiative-tension"),
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
        superseded_count = supersede_runtime_private_initiative_tension_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded private initiative-tension support signal for the same visible-work domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "private_initiative_tension_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "private_initiative_tension_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "private_initiative_tension_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


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


def _latest_open_loop_pressure() -> dict[str, object] | None:
    for item in list_runtime_open_loop_signals(limit=12):
        if str(item.get("status") or "") not in {"open", "softening"}:
            continue
        return item
    return None


def _latest_development_focus() -> dict[str, object] | None:
    for item in list_runtime_development_focuses(limit=12):
        if str(item.get("status") or "") != "active":
            continue
        return item
    return None


def _latest_inner_note_support(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_inner_note_signals(limit=12):
        if str(item.get("run_id") or "") != str(run_id or ""):
            continue
        if str(item.get("status") or "") != "active":
            continue
        return item
    return None


def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["tension_type"] = str(signal.get("tension_type") or "retention-pull")
    enriched["tension_target"] = str(signal.get("tension_target") or "")
    enriched["tension_level"] = str(signal.get("tension_level") or "low")
    enriched["tension_summary"] = str(signal.get("tension_summary") or "")
    enriched["tension_confidence"] = str(signal.get("tension_confidence") or signal.get("confidence") or "low")
    enriched["source_anchor"] = str(signal.get("source_anchor") or "")
    enriched["focus"] = str(signal.get("focus") or "")
    enriched["grounding_mode"] = str(signal.get("grounding_mode") or "visible-work+runtime-support")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    canonical_key = str(item.get("canonical_key") or "")
    inferred_type = _canonical_tension_type(canonical_key) or "retention-pull"
    inferred_target = _title_target(str(item.get("title") or ""))
    inferred_level = "medium" if inferred_type == "unresolved" else "low"
    enriched["tension_type"] = str(item.get("tension_type") or inferred_type)
    enriched["tension_target"] = str(item.get("tension_target") or inferred_target)
    enriched["tension_level"] = str(item.get("tension_level") or inferred_level)
    enriched["tension_summary"] = str(item.get("tension_summary") or item.get("summary") or "")
    enriched["tension_confidence"] = str(item.get("tension_confidence") or item.get("confidence") or "low")
    enriched["source_anchor"] = str(item.get("source_anchor") or item.get("support_summary") or "")
    enriched["focus"] = str(item.get("focus") or "")
    enriched["grounding_mode"] = str(item.get("grounding_mode") or "visible-work+runtime-support")
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _domain_key(item: dict[str, object] | None, *, fallback: str) -> str:
    text = str((item or {}).get("canonical_key") or "").strip()
    if text:
        return text.split(":")[-1][:72] or fallback
    return fallback[:72]


def _source_anchor_from_visible_note(visible_note: dict[str, object]) -> str:
    note_id = str(visible_note.get("note_id") or "").strip()
    work_id = str(visible_note.get("work_id") or "").strip()
    capability_id = str(visible_note.get("capability_id") or "").strip()
    anchor = f"Visible work note {note_id or 'unknown-note'}"
    if work_id:
        anchor += f" for {work_id}"
    if capability_id:
        anchor += f" via capability {capability_id}"
    return anchor


def _support_anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    title = str(item.get("title") or item.get("summary") or "").strip()
    canonical_key = str(item.get("canonical_key") or "").strip()
    if title and canonical_key:
        return f"{title} ({canonical_key})"
    return title or canonical_key


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


def _quote(text: str) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ""
    bounded = normalized[:157].rstrip()
    if len(normalized) > 157:
        bounded += "..."
    return f'"{bounded}"'


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _canonical_tension_type(canonical_key: str) -> str:
    parts = [part for part in str(canonical_key or "").split(":") if part]
    if len(parts) >= 2 and parts[0] == "private-initiative-tension":
        return parts[1]
    return ""


def _title_target(title: str) -> str:
    normalized = str(title or "").strip()
    marker = ": "
    if marker in normalized:
        return normalized.split(marker, 1)[1][:96]
    return normalized[:96]
