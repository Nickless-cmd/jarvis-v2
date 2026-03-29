from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_private_inner_interplay_signals,
    list_runtime_private_inner_note_signals,
    list_runtime_private_initiative_tension_signals,
    supersede_runtime_private_inner_interplay_signals_for_relation,
    update_runtime_private_inner_interplay_signal_status,
    upsert_runtime_private_inner_interplay_signal,
)

_STALE_AFTER_DAYS = 7


def track_runtime_private_inner_interplay_signals_for_visible_turn(
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
            "summary": "No bounded private inner interplay grounding was available for this visible turn.",
        }

    persisted = _persist_private_inner_interplay_signals(
        signals=[candidate],
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in persisted if item.get("was_created")]),
        "updated": len([item for item in persisted if item.get("was_updated")]),
        "items": persisted,
        "summary": (
            "Tracked 1 bounded private inner interplay support signal."
            if persisted
            else "No bounded private inner interplay support signal warranted tracking."
        ),
    }


def refresh_runtime_private_inner_interplay_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_private_inner_interplay_signals(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(
            str(item.get("updated_at") or item.get("created_at") or "")
        )
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_private_inner_interplay_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded private inner interplay inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "private_inner_interplay_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_private_inner_interplay_signal_surface(
    *, limit: int = 8
) -> dict[str, object]:
    refresh_runtime_private_inner_interplay_signal_statuses()
    items = list_runtime_private_inner_interplay_signals(limit=max(limit, 1))
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
                (latest or {}).get("title")
                or "No active private inner interplay support"
            ),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_interplay_type": str(
                (latest or {}).get("interplay_type") or "none"
            ),
            "current_confidence": str(
                (latest or {}).get("interplay_confidence") or "low"
            ),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


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


def _persist_private_inner_interplay_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_private_inner_interplay_signal(
            signal_id=f"private-inner-interplay-signal-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "private-inner-interplay"),
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
        superseded_count = supersede_runtime_private_inner_interplay_signals_for_relation(
            relation_key=str(signal.get("relation_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded private inner interplay support signal for the same visible-work relation.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "private_inner_interplay_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "private_inner_interplay_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "private_inner_interplay_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, signal))
    return persisted


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


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
