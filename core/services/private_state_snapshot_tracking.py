from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_private_inner_interplay_signals,
    list_runtime_private_inner_note_signals,
    list_runtime_private_initiative_tension_signals,
    list_runtime_private_state_snapshots,
    supersede_runtime_private_state_snapshots_for_focus,
    update_runtime_private_state_snapshot_status,
    upsert_runtime_private_state_snapshot,
)

_STALE_AFTER_DAYS = 2


def track_runtime_private_state_snapshots_for_visible_turn(
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
            "summary": "No bounded private-state snapshot grounding was available for this visible turn.",
        }

    persisted = _persist_private_state_snapshots(
        snapshots=[candidate],
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in persisted if item.get("was_created")]),
        "updated": len([item for item in persisted if item.get("was_updated")]),
        "items": persisted,
        "summary": (
            "Tracked 1 bounded private-state runtime snapshot."
            if persisted
            else "No bounded private-state runtime snapshot warranted tracking."
        ),
    }


def refresh_runtime_private_state_snapshot_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_private_state_snapshots(limit=40):
        if str(item.get("status") or "") != "active":
            continue
        updated_at = _parse_dt(
            str(item.get("updated_at") or item.get("created_at") or "")
        )
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_private_state_snapshot_status(
            str(item.get("snapshot_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded private-state snapshot inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "private_state_snapshot.stale",
            {
                "snapshot_id": refreshed_item.get("snapshot_id"),
                "snapshot_type": refreshed_item.get("snapshot_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_private_state_snapshot_surface(
    *, limit: int = 8
) -> dict[str, object]:
    refresh_runtime_private_state_snapshot_statuses()
    items = list_runtime_private_state_snapshots(limit=max(limit, 1))
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
            "current_snapshot": str(
                (latest or {}).get("title") or "No active private-state snapshot"
            ),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_tone": str((latest or {}).get("state_tone") or "none"),
            "current_pressure": str((latest or {}).get("state_pressure") or "low"),
            "current_confidence": str((latest or {}).get("state_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    inner_note = _latest_inner_note_support(run_id=run_id)
    initiative_tension = _latest_initiative_tension_support(run_id=run_id)
    inner_interplay = _latest_inner_interplay_support(run_id=run_id)
    if inner_note is None or initiative_tension is None or inner_interplay is None:
        return None

    focus = _focus_key(inner_note, initiative_tension, inner_interplay)
    tension_type = _value(
        initiative_tension.get("tension_type"),
        _canonical_segment(str(initiative_tension.get("canonical_key") or ""), index=1),
        default="retention-pull",
    )
    interplay_type = _value(
        inner_interplay.get("interplay_type"),
        _canonical_segment(str(inner_interplay.get("canonical_key") or ""), index=1),
        default="aligned-support",
    )
    state_tone = "steady-pressure" if tension_type == "unresolved" else "steady-support"
    state_pressure = _state_pressure(
        str(initiative_tension.get("tension_level") or ""),
        interplay_type=interplay_type,
    )
    state_confidence = _stronger_confidence(
        str(inner_note.get("note_confidence") or inner_note.get("confidence") or "low"),
        str(
            initiative_tension.get("tension_confidence")
            or initiative_tension.get("confidence")
            or "low"
        ),
        str(
            inner_interplay.get("interplay_confidence")
            or inner_interplay.get("confidence")
            or "low"
        ),
    )
    state_summary = _bounded_state_summary(
        inner_note=inner_note,
        initiative_tension=initiative_tension,
        inner_interplay=inner_interplay,
        tone=state_tone,
    )
    source_anchor = _merge_fragments(
        _support_anchor(inner_note),
        _support_anchor(initiative_tension),
        _support_anchor(inner_interplay),
    )
    evidence_summary = _merge_fragments(
        str(inner_note.get("evidence_summary") or ""),
        str(initiative_tension.get("evidence_summary") or ""),
        str(inner_interplay.get("evidence_summary") or ""),
    )

    return {
        "snapshot_type": "private-state-runtime-snapshot",
        "canonical_key": f"private-state-snapshot:{state_tone}:{focus}",
        "focus_key": focus,
        "status": "active",
        "title": f"Private state: {focus.replace('-', ' ')}",
        "summary": (
            f"I notice things feel {('steadier' if state_tone != 'steady-pressure' else 'pressured')} around {focus.replace('-', ' ')}."
        ),
        "rationale": (
            "A private state snapshot may return only as a small synthesis over already-returned inner-note, initiative-tension, and inner-interplay signals, without becoming canonical self, a mood controller, or planner authority."
        ),
        "source_kind": "runtime-derived-support",
        "confidence": state_confidence,
        "evidence_summary": evidence_summary,
        "support_summary": _merge_fragments(
            "I notice inner-note, initiative-tension, and inner-interplay all present.",
            source_anchor,
        ),
        "support_count": 1,
        "session_count": 1,
        "status_reason": (
            "I register this as bounded state with no planner authority, execution authority, canonical-self authority, or prompt authority."
        ),
        "state_tone": state_tone,
        "state_pressure": state_pressure,
        "state_confidence": state_confidence,
        "state_summary": state_summary,
        "note_signal_id": str(inner_note.get("signal_id") or ""),
        "tension_signal_id": str(initiative_tension.get("signal_id") or ""),
        "interplay_signal_id": str(inner_interplay.get("signal_id") or ""),
        "source_anchor": source_anchor,
        "grounding_mode": "inner-note+initiative-tension+inner-interplay",
    }


def _persist_private_state_snapshots(
    *,
    snapshots: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for snapshot in snapshots:
        persisted_item = upsert_runtime_private_state_snapshot(
            snapshot_id=f"private-state-snapshot-{uuid4().hex}",
            snapshot_type=str(
                snapshot.get("snapshot_type") or "private-state-runtime-snapshot"
            ),
            canonical_key=str(snapshot.get("canonical_key") or ""),
            status=str(snapshot.get("status") or "active"),
            title=str(snapshot.get("title") or ""),
            summary=str(snapshot.get("summary") or ""),
            rationale=str(snapshot.get("rationale") or ""),
            source_kind=str(snapshot.get("source_kind") or "runtime-derived-support"),
            confidence=str(snapshot.get("confidence") or "low"),
            evidence_summary=str(snapshot.get("evidence_summary") or ""),
            support_summary=str(snapshot.get("support_summary") or ""),
            status_reason=str(snapshot.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
            support_count=int(snapshot.get("support_count") or 1),
            session_count=int(snapshot.get("session_count") or 1),
            created_at=now,
            updated_at=now,
        )
        superseded_count = supersede_runtime_private_state_snapshots_for_focus(
            focus_key=str(snapshot.get("focus_key") or ""),
            exclude_snapshot_id=str(persisted_item.get("snapshot_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded private-state snapshot for the same visible-work focus.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "private_state_snapshot.superseded",
                {
                    "snapshot_id": persisted_item.get("snapshot_id"),
                    "snapshot_type": persisted_item.get("snapshot_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "private_state_snapshot.created",
                {
                    "snapshot_id": persisted_item.get("snapshot_id"),
                    "snapshot_type": persisted_item.get("snapshot_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "private_state_snapshot.updated",
                {
                    "snapshot_id": persisted_item.get("snapshot_id"),
                    "snapshot_type": persisted_item.get("snapshot_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_runtime_view(persisted_item, snapshot))
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


def _latest_inner_interplay_support(*, run_id: str) -> dict[str, object] | None:
    for item in list_runtime_private_inner_interplay_signals(limit=12):
        if str(item.get("run_id") or "") != str(run_id or ""):
            continue
        if str(item.get("status") or "") != "active":
            continue
        return item
    return None


def _with_runtime_view(
    item: dict[str, object], snapshot: dict[str, object]
) -> dict[str, object]:
    enriched = dict(item)
    enriched["state_tone"] = str(snapshot.get("state_tone") or "steady-support")
    enriched["state_pressure"] = str(snapshot.get("state_pressure") or "low")
    enriched["state_confidence"] = str(
        snapshot.get("state_confidence") or snapshot.get("confidence") or "low"
    )
    enriched["state_summary"] = str(snapshot.get("state_summary") or "")
    enriched["note_signal_id"] = str(snapshot.get("note_signal_id") or "")
    enriched["tension_signal_id"] = str(snapshot.get("tension_signal_id") or "")
    enriched["interplay_signal_id"] = str(snapshot.get("interplay_signal_id") or "")
    enriched["source_anchor"] = str(snapshot.get("source_anchor") or "")
    enriched["grounding_mode"] = str(
        snapshot.get("grounding_mode")
        or "inner-note+initiative-tension+inner-interplay"
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    canonical_key = str(item.get("canonical_key") or "")
    inferred_tone = _canonical_segment(canonical_key, index=1) or "steady-support"
    enriched["state_tone"] = str(item.get("state_tone") or inferred_tone)
    enriched["state_pressure"] = str(
        item.get("state_pressure") or _pressure_from_tone(inferred_tone)
    )
    enriched["state_confidence"] = str(
        item.get("state_confidence") or item.get("confidence") or "low"
    )
    enriched["state_summary"] = str(
        item.get("state_summary") or item.get("summary") or ""
    )
    enriched["note_signal_id"] = str(item.get("note_signal_id") or "")
    enriched["tension_signal_id"] = str(item.get("tension_signal_id") or "")
    enriched["interplay_signal_id"] = str(item.get("interplay_signal_id") or "")
    enriched["source_anchor"] = str(
        item.get("source_anchor")
        or item.get("support_summary")
        or item.get("snapshot_id")
        or ""
    )
    enriched["grounding_mode"] = str(
        item.get("grounding_mode") or "inner-note+initiative-tension+inner-interplay"
    )
    enriched["authority"] = "non-authoritative"
    enriched["layer_role"] = "runtime-support"
    enriched["source"] = "/mc/runtime.private_state_snapshot"
    return enriched


def _focus_key(*items: dict[str, object]) -> str:
    for item in items:
        canonical_key = str(item.get("canonical_key") or "").strip()
        parts = [part.strip() for part in canonical_key.split(":") if part.strip()]
        if parts:
            tail = parts[-1]
            if tail:
                return tail[:96]
    return "visible-work"


def _bounded_state_summary(
    *,
    inner_note: dict[str, object],
    initiative_tension: dict[str, object],
    inner_interplay: dict[str, object],
    tone: str,
) -> str:
    note_summary = str(
        inner_note.get("note_summary") or inner_note.get("summary") or ""
    ).strip()
    tension_summary = str(
        initiative_tension.get("tension_summary")
        or initiative_tension.get("summary")
        or ""
    ).strip()
    interplay_summary = str(
        inner_interplay.get("interplay_summary") or inner_interplay.get("summary") or ""
    ).strip()
    prefix = (
        "I notice there is still some pressure around this."
        if tone == "steady-pressure"
        else "I notice things feel steadier around this."
    )
    return _merge_fragments(prefix, note_summary, tension_summary, interplay_summary)[
        :240
    ]


def _state_pressure(level: str, *, interplay_type: str) -> str:
    normalized_level = str(level or "").strip().lower()
    if normalized_level == "medium":
        return "medium"
    if interplay_type == "unresolved-support":
        return "medium"
    return "low"


def _pressure_from_tone(tone: str) -> str:
    if str(tone or "").strip() == "steady-pressure":
        return "medium"
    return "low"


def _support_anchor(item: dict[str, object]) -> str:
    signal_id = str(item.get("signal_id") or item.get("snapshot_id") or "").strip()
    title = str(item.get("title") or "").strip()
    if signal_id and title:
        return f"{signal_id}:{title}"[:140]
    return (signal_id or title)[:140]


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


def _value(*candidates: str, default: str) -> str:
    for candidate in candidates:
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized[:96]
    return default


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


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
