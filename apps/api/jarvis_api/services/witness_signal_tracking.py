from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflection_signals,
    list_runtime_temporal_recurrence_signals,
    list_runtime_witness_signals,
    supersede_runtime_witness_signals_for_domain,
    update_runtime_witness_signal_status,
    upsert_runtime_witness_signal,
)

_CARRIED_AFTER_DAYS = 3
_FADING_AFTER_DAYS = 14


def track_runtime_witness_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_witness_signals(
        signals=_extract_witness_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded witness signals."
            if items
            else "No bounded witness signal warranted tracking."
        ),
    }


def refresh_runtime_witness_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    carried = 0
    fading = 0
    for item in list_runtime_witness_signals(limit=40):
        status = str(item.get("status") or "")
        if status not in {"fresh", "carried"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None:
            continue
        next_status = None
        reason = ""
        if status == "fresh" and updated_at <= now - timedelta(days=_CARRIED_AFTER_DAYS):
            next_status = "carried"
            reason = "The witnessed shift remains bounded, but it is now being carried rather than felt as fresh."
        elif status == "carried" and updated_at <= now - timedelta(days=_FADING_AFTER_DAYS):
            next_status = "fading"
            reason = "Marked fading after the bounded witness window aged out."
        if not next_status:
            continue
        refreshed_item = update_runtime_witness_signal_status(
            str(item.get("signal_id") or ""),
            status=next_status,
            updated_at=now.isoformat(),
            status_reason=reason,
        )
        if refreshed_item is None:
            continue
        if next_status == "carried":
            carried += 1
            event_bus.publish(
                "witness_signal.carried",
                {
                    "signal_id": refreshed_item.get("signal_id"),
                    "signal_type": refreshed_item.get("signal_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                },
            )
        else:
            fading += 1
            event_bus.publish(
                "witness_signal.fading",
                {
                    "signal_id": refreshed_item.get("signal_id"),
                    "signal_type": refreshed_item.get("signal_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                },
            )
    return {"carried_marked": carried, "fading_marked": fading}


def build_runtime_witness_signal_surface(*, limit: int = 6) -> dict[str, object]:
    refresh_runtime_witness_signal_statuses()
    items = list_runtime_witness_signals(limit=max(limit, 1))
    fresh = [item for item in items if str(item.get("status") or "") == "fresh"]
    carried = [item for item in items if str(item.get("status") or "") == "carried"]
    fading = [item for item in items if str(item.get("status") or "") == "fading"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered = [*fresh, *carried, *fading, *superseded]
    latest = next(iter(fresh or carried or fading or superseded), None)
    return {
        "active": bool(fresh or carried),
        "items": ordered,
        "summary": {
            "fresh_count": len(fresh),
            "carried_count": len(carried),
            "fading_count": len(fading),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No current witness signal"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
    }


def _extract_witness_candidates() -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for recurrence in list_runtime_temporal_recurrence_signals(limit=18):
        if str(recurrence.get("status") or "") != "softening":
            continue
        domain_key = _temporal_domain_key(str(recurrence.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["softening_recurrence"] = recurrence

    for reflection in list_runtime_reflection_signals(limit=18):
        if str(reflection.get("status") or "") != "settled":
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["settled_reflection"] = reflection

    for focus in list_runtime_development_focuses(limit=18):
        if str(focus.get("status") or "") not in {"active", "completed"}:
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if str(focus.get("status") or "") == "active":
                bucket["active_focus"] = focus
            else:
                bucket["completed_focus"] = focus

    for goal in list_runtime_goal_signals(limit=18):
        if str(goal.get("status") or "") not in {"active", "completed"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if str(goal.get("status") or "") == "active":
                bucket["active_goal"] = goal
            else:
                bucket["completed_goal"] = goal

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        softening_recurrence = snapshot.get("softening_recurrence")
        settled_reflection = snapshot.get("settled_reflection")
        if not softening_recurrence or not settled_reflection:
            continue

        active_focus = snapshot.get("active_focus")
        completed_focus = snapshot.get("completed_focus")
        active_goal = snapshot.get("active_goal")
        completed_goal = snapshot.get("completed_goal")
        title_suffix = _domain_title(domain_key)

        signal_type = "carried-lesson" if active_focus or active_goal or completed_goal or completed_focus else "settled-turn"
        summary = (
            f"A bounded lesson around {title_suffix.lower()} now looks carried forward."
            if signal_type == "carried-lesson"
            else f"A bounded turn around {title_suffix.lower()} now looks witnessed as a settled shift."
        )
        rationale = (
            "A previously recurring thread has softened while its reflection thread is now settled, so the change reads as a small carried development turn rather than fresh friction."
        )
        status_reason = (
            "Recurring pressure has softened and the reflective thread now looks settled enough to witness as a bounded carried shift."
        )
        candidates.append(
            _build_candidate(
                domain_key=domain_key,
                signal_type=signal_type,
                title=(
                    f"Carried lesson: {title_suffix}"
                    if signal_type == "carried-lesson"
                    else f"Witnessed turn: {title_suffix}"
                ),
                summary=summary,
                rationale=rationale,
                status_reason=status_reason,
                source_items=[
                    softening_recurrence,
                    settled_reflection,
                    active_focus,
                    completed_focus,
                    active_goal,
                    completed_goal,
                ],
            )
        )

    return candidates[:4]


def _persist_witness_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_witness_signal(
            signal_id=f"witness-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "witness-signal"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "fresh"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "runtime-derived-support"),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=str(signal.get("support_summary") or ""),
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(signal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        superseded_count = supersede_runtime_witness_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer witnessed development turn for the same bounded domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "witness_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "witness_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "witness_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _build_candidate(
    *,
    domain_key: str,
    signal_type: str,
    title: str,
    summary: str,
    rationale: str,
    status_reason: str,
    source_items: list[dict[str, object] | None],
) -> dict[str, object]:
    items = [item for item in source_items if item]
    support_count = max([int(item.get("support_count") or 1) for item in items], default=1)
    session_count = max([int(item.get("session_count") or 1) for item in items], default=1)
    confidence = "high" if len(items) >= 3 else "medium"
    return {
        "signal_type": signal_type,
        "canonical_key": f"witness-signal:{signal_type}:{domain_key}",
        "domain_key": domain_key,
        "status": "fresh",
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": "derived-runtime-witness",
        "confidence": confidence,
        "evidence_summary": _merge_fragments(*[str(item.get("evidence_summary") or "") for item in items]),
        "support_summary": _merge_fragments(*[str(item.get("support_summary") or "") for item in items]),
        "support_count": support_count,
        "session_count": session_count,
        "status_reason": status_reason,
    }


def _focus_domain_key(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if text.startswith("development-focus:communication:"):
        return text.removeprefix("development-focus:communication:")
    if text.startswith("development-focus:user-directed:"):
        return text.removeprefix("development-focus:user-directed:")
    if text.startswith("development-focus:runtime:"):
        parts = text.removeprefix("development-focus:runtime:").split(":")
        return parts[0] if parts else ""
    return ""


def _goal_domain_key(canonical_key: str) -> str:
    return str(canonical_key or "").removeprefix("goal-signal:")


def _reflection_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _temporal_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Witnessed thread"


def _merge_fragments(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        normalized = " ".join(str(value or "").split()).strip()
        if normalized and normalized not in parts:
            parts.append(normalized)
    return " | ".join(parts[:4])


def _parse_dt(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
