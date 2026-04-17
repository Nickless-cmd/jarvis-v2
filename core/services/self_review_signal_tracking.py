from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.internal_opposition_signal_tracking import (
    build_runtime_internal_opposition_signal_surface,
)
from core.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflection_signals,
    list_runtime_self_review_signals,
    list_runtime_temporal_recurrence_signals,
    list_runtime_witness_signals,
    supersede_runtime_self_review_signals_for_domain,
    update_runtime_self_review_signal_status,
    upsert_runtime_self_review_signal,
)

_STALE_AFTER_DAYS = 14


def track_runtime_self_review_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_self_review_signals(
        signals=_extract_self_review_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded self-review signals."
            if items
            else "No bounded self-review signal warranted tracking."
        ),
    }


def refresh_runtime_self_review_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_self_review_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_self_review_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded self-review inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "self_review_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_self_review_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_self_review_signal_statuses()
    items = list_runtime_self_review_signals(limit=max(limit, 1))
    active = [item for item in items if str(item.get("status") or "") == "active"]
    softening = [item for item in items if str(item.get("status") or "") == "softening"]
    stale = [item for item in items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered = [*active, *softening, *stale, *superseded]
    latest = next(iter(active or softening or stale or superseded), None)
    return {
        "active": bool(active or softening),
        "items": ordered,
        "summary": {
            "active_count": len(active),
            "softening_count": len(softening),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active self-review signal"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
    }


def _extract_self_review_candidates() -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=18):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["active_focus"] = focus

    for goal in list_runtime_goal_signals(limit=18):
        status = str(goal.get("status") or "")
        if status not in {"active", "blocked"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "blocked":
            bucket["blocked_goal"] = goal
        else:
            bucket["active_goal"] = goal

    for recurrence in list_runtime_temporal_recurrence_signals(limit=18):
        status = str(recurrence.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _temporal_domain_key(str(recurrence.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_recurrence"] = recurrence
        else:
            bucket["softening_recurrence"] = recurrence

    for witness in list_runtime_witness_signals(limit=18):
        status = str(witness.get("status") or "")
        if status not in {"fresh", "carried"}:
            continue
        domain_key = _witness_domain_key(str(witness.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "fresh":
            bucket["fresh_witness"] = witness
        else:
            bucket["carried_witness"] = witness

    for reflection in list_runtime_reflection_signals(limit=18):
        status = str(reflection.get("status") or "")
        if status not in {"integrating", "settled"}:
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "integrating":
            bucket["integrating_reflection"] = reflection
        else:
            bucket["settled_reflection"] = reflection

    for item in build_runtime_open_loop_signal_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"open", "softening"}:
            continue
        domain_key = _open_loop_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "open":
            bucket["open_loop"] = item
        else:
            bucket["softening_loop"] = item

    for item in build_runtime_internal_opposition_signal_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _internal_opposition_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_opposition"] = item
        else:
            bucket["softening_opposition"] = item

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        active_focus = snapshot.get("active_focus")
        active_goal = snapshot.get("active_goal")
        blocked_goal = snapshot.get("blocked_goal")
        active_recurrence = snapshot.get("active_recurrence")
        softening_recurrence = snapshot.get("softening_recurrence")
        fresh_witness = snapshot.get("fresh_witness")
        carried_witness = snapshot.get("carried_witness")
        integrating_reflection = snapshot.get("integrating_reflection")
        settled_reflection = snapshot.get("settled_reflection")
        open_loop = snapshot.get("open_loop")
        softening_loop = snapshot.get("softening_loop")
        active_opposition = snapshot.get("active_opposition")
        softening_opposition = snapshot.get("softening_opposition")
        title_suffix = _domain_title(domain_key)

        if open_loop and active_opposition and (active_recurrence or integrating_reflection):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="review-pressure",
                    status="active",
                    title=f"Self-review needed: {title_suffix}",
                    summary=f"This bounded thread around {title_suffix.lower()} now looks like it should enter explicit self-review.",
                    rationale="An unresolved open loop is now paired with active internal opposition and continuing recurrence or integration pressure.",
                    status_reason="Open-loop pressure and active internal challenge make this domain a bounded self-review candidate.",
                    source_items=[open_loop, active_opposition, active_recurrence, integrating_reflection, active_focus, active_goal, blocked_goal],
                )
            )
            continue

        if active_recurrence and (open_loop or active_opposition) and (active_focus or active_goal or blocked_goal):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="review-due-by-recurrence",
                    status="active",
                    title=f"Review by recurrence: {title_suffix}",
                    summary=f"This bounded thread around {title_suffix.lower()} keeps returning strongly enough that it now looks review-worthy.",
                    rationale="Repeated recurrence is still present while unresolved pressure or internal opposition remains live around the same domain.",
                    status_reason="Recurring tension plus live direction/opposition makes bounded self-review look due.",
                    source_items=[active_recurrence, open_loop, active_opposition, active_focus, active_goal, blocked_goal],
                )
            )
            continue

        if (fresh_witness or carried_witness) and (softening_loop or softening_opposition or softening_recurrence) and (active_focus or active_goal or blocked_goal or settled_reflection):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="review-carried-thread",
                    status="softening",
                    title=f"Review carried thread: {title_suffix}",
                    summary=f"This bounded thread around {title_suffix.lower()} looks calmer, but still seems worth a small self-review before it fully drops out of focus.",
                    rationale="A carried or freshly witnessed lesson is still coupled to softening loop/opposition/recurrence evidence, so the domain looks review-worthy even without sharp pressure.",
                    status_reason="A carried lesson remains visible enough that bounded self-review still looks relevant, though the pressure is softening.",
                    source_items=[fresh_witness, carried_witness, softening_loop, softening_opposition, softening_recurrence, active_focus, active_goal, blocked_goal, settled_reflection],
                )
            )

    return candidates[:4]


def _persist_self_review_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_self_review_signal(
            signal_id=f"self-review-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "self-review-signal"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
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
        superseded_count = supersede_runtime_self_review_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded self-review reading for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "self_review_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "self_review_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "self_review_signal.updated",
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
    status: str,
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
        "canonical_key": f"self-review:{signal_type}:{domain_key}",
        "domain_key": domain_key,
        "status": status,
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": "runtime-derived-support",
        "confidence": confidence,
        "evidence_summary": _merge_fragments(*[str(item.get("evidence_summary") or "") for item in items]),
        "support_summary": _merge_fragments(*[str(item.get("support_summary") or "") for item in items]),
        "support_count": support_count,
        "session_count": session_count,
        "status_reason": status_reason,
    }


def _focus_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _goal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 2 else ""


def _temporal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _witness_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _reflection_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _open_loop_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _internal_opposition_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Self-review"


def _merge_fragments(*parts: str) -> str:
    seen: list[str] = []
    for part in parts:
        text = " ".join(str(part or "").split()).strip()
        if not text or text in seen:
            continue
        seen.append(text)
    return " | ".join(seen[:4])


def _parse_dt(raw: str) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
