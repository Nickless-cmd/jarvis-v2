from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.internal_opposition_signal_tracking import (
    build_runtime_internal_opposition_signal_surface,
)
from core.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from core.services.self_review_record_tracking import (
    build_runtime_self_review_record_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_self_review_runs,
    list_runtime_witness_signals,
    supersede_runtime_self_review_runs_for_domain,
    update_runtime_self_review_run_status,
    upsert_runtime_self_review_run,
)

_STALE_AFTER_DAYS = 14


def track_runtime_self_review_runs_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_self_review_runs(
        runs=_extract_self_review_run_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded self-review runs."
            if items
            else "No bounded self-review run warranted tracking."
        ),
    }


def refresh_runtime_self_review_run_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_self_review_runs(limit=40):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_self_review_run_status(
            str(item.get("run_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded self-review run inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "self_review_run.stale",
            {
                "run_id": refreshed_item.get("run_id"),
                "run_type": refreshed_item.get("run_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_self_review_run_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_self_review_run_statuses()
    items = list_runtime_self_review_runs(limit=max(limit, 1))
    snapshots = _build_review_run_snapshots()
    enriched_items = [_with_surface_run_view(item, snapshots=snapshots) for item in items]
    fresh = [item for item in enriched_items if str(item.get("status") or "") == "fresh"]
    active = [item for item in enriched_items if str(item.get("status") or "") == "active"]
    fading = [item for item in enriched_items if str(item.get("status") or "") == "fading"]
    stale = [item for item in enriched_items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in enriched_items if str(item.get("status") or "") == "superseded"]
    ordered = [*fresh, *active, *fading, *stale, *superseded]
    latest = next(iter(fresh or active or fading or stale or superseded), None)
    return {
        "active": bool(fresh or active or fading),
        "items": ordered,
        "summary": {
            "fresh_count": len(fresh),
            "active_count": len(active),
            "fading_count": len(fading),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_run": str((latest or {}).get("title") or "No active self-review run"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_review_type": str((latest or {}).get("run_type") or "none"),
            "current_review_focus": str((latest or {}).get("review_focus") or "none"),
        },
    }


def _extract_self_review_run_candidates() -> list[dict[str, object]]:
    snapshots = _build_review_run_snapshots()
    candidates: list[dict[str, object]] = []

    for item in build_runtime_self_review_record_surface(limit=12).get("items", []):
        record_status = str(item.get("status") or "")
        if record_status not in {"fresh", "active", "fading"}:
            continue
        domain_key = _self_review_run_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        snapshot = snapshots.get(domain_key) or {}
        if not any(
            snapshot.get(key)
            for key in ("open_loop", "softening_loop", "active_opposition", "softening_opposition", "active_focus", "active_goal", "blocked_goal", "witness")
        ):
            continue
        title_suffix = _domain_title(domain_key)
        review_focus = _build_review_focus(snapshot=snapshot)
        short_note = _build_short_review_note(title_suffix=title_suffix, snapshot=snapshot)
        source_items = [
            item,
            snapshot.get("open_loop"),
            snapshot.get("softening_loop"),
            snapshot.get("active_opposition"),
            snapshot.get("softening_opposition"),
            snapshot.get("active_focus"),
            snapshot.get("active_goal"),
            snapshot.get("blocked_goal"),
            snapshot.get("witness"),
        ]
        candidates.append(
            {
                "run_type": str(item.get("record_type") or "self-review-run"),
                "canonical_key": f"self-review-run:{str(item.get('record_type') or 'self-review-run')}:{domain_key}",
                "domain_key": domain_key,
                "status": record_status,
                "title": f"Self-review snapshot: {title_suffix}",
                "summary": short_note,
                "rationale": str(item.get("summary") or "") or "A bounded self-review brief now materializes as a small review snapshot.",
                "source_kind": "runtime-derived-support",
                "confidence": _stronger_confidence(
                    str(item.get("confidence") or "low"),
                    str(item.get("closure_confidence") or ""),
                ),
                "evidence_summary": _merge_fragments(
                    *[str(source.get("evidence_summary") or "") for source in source_items if source]
                ),
                "support_summary": _merge_fragments(
                    *[str(source.get("support_summary") or "") for source in source_items if source]
                ),
                "support_count": max([int(source.get("support_count") or 1) for source in source_items if source], default=1),
                "session_count": max([int(source.get("session_count") or 1) for source in source_items if source], default=1),
                "status_reason": str(item.get("short_reason") or item.get("status_reason") or ""),
                "review_focus": review_focus,
                "open_loop_status": str(item.get("open_loop_status") or "none"),
                "opposition_status": str(item.get("opposition_status") or "none"),
                "closure_confidence": str(item.get("closure_confidence") or "low"),
                "short_outlook": _build_short_outlook(snapshot=snapshot),
                "short_review_note": short_note,
            }
        )

    return candidates[:4]


def _persist_self_review_runs(
    *,
    runs: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    existing_by_key = {
        str(item.get("canonical_key") or ""): item for item in list_runtime_self_review_runs(limit=40)
    }
    persisted: list[dict[str, object]] = []
    for run in runs:
        existing = existing_by_key.get(str(run.get("canonical_key") or ""))
        persisted_item = upsert_runtime_self_review_run(
            run_id=f"self-review-run-{uuid4().hex}",
            run_type=str(run.get("run_type") or "self-review-run"),
            canonical_key=str(run.get("canonical_key") or ""),
            status="active" if existing and str(run.get("status") or "") == "fresh" else str(run.get("status") or "fresh"),
            title=str(run.get("title") or ""),
            summary=_run_summary(run),
            rationale=str(run.get("rationale") or ""),
            source_kind=str(run.get("source_kind") or "runtime-derived-support"),
            confidence=str(run.get("confidence") or "low"),
            evidence_summary=str(run.get("evidence_summary") or ""),
            support_summary=_run_support_summary(run),
            support_count=int(run.get("support_count") or 1),
            session_count=int(run.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(run.get("status_reason") or ""),
            record_run_id=run_id,
            session_id=session_id,
        )
        superseded_count = supersede_runtime_self_review_runs_for_domain(
            domain_key=str(run.get("domain_key") or ""),
            exclude_run_id=str(persisted_item.get("run_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer bounded self-review snapshot for the same domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "self_review_run.superseded",
                {
                    "run_id": persisted_item.get("run_id"),
                    "run_type": persisted_item.get("run_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "self_review_run.created",
                {
                    "run_id": persisted_item.get("run_id"),
                    "run_type": persisted_item.get("run_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
            if str(persisted_item.get("confidence") or "").lower() == "high":
                try:
                    from core.runtime.heartbeat_triggers import (
                        set_trigger_for_default_workspace,
                    )

                    set_trigger_for_default_workspace(
                        reason="self-review-incident",
                        source="self_review_run_tracking",
                        text=str(persisted_item.get("summary") or ""),
                    )
                except Exception:
                    pass
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "self_review_run.updated",
                {
                    "run_id": persisted_item.get("run_id"),
                    "run_type": persisted_item.get("run_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(_with_run_view(persisted_item, run))
    return persisted


def _build_review_run_snapshots() -> dict[str, dict[str, object]]:
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

    for witness in list_runtime_witness_signals(limit=18):
        status = str(witness.get("status") or "")
        if status not in {"fresh", "carried"}:
            continue
        domain_key = _witness_domain_key(str(witness.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["witness"] = witness

    for item in build_runtime_open_loop_signal_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"open", "softening", "closed"}:
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

    return snapshots


def _with_run_view(item: dict[str, object], run: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["domain"] = _self_review_run_domain_key(str(item.get("canonical_key") or ""))
    enriched["review_type"] = str(run.get("run_type") or item.get("run_type") or "self-review-run")
    enriched["review_focus"] = str(run.get("review_focus") or "bounded-self-review")
    enriched["open_loop_status"] = str(run.get("open_loop_status") or "none")
    enriched["opposition_status"] = str(run.get("opposition_status") or "none")
    enriched["closure_confidence"] = str(run.get("closure_confidence") or "low")
    enriched["short_outlook"] = str(run.get("short_outlook") or "")
    enriched["short_review_note"] = str(run.get("short_review_note") or item.get("summary") or "")
    return enriched


def _with_surface_run_view(item: dict[str, object], *, snapshots: dict[str, dict[str, object]]) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _self_review_run_domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key) or {}
    open_loop = snapshot.get("open_loop") or snapshot.get("softening_loop") or {}
    opposition = snapshot.get("active_opposition") or snapshot.get("softening_opposition") or {}
    enriched["domain"] = domain_key
    enriched["review_type"] = str(item.get("run_type") or "self-review-run")
    enriched["review_focus"] = _build_review_focus(snapshot=snapshot)
    enriched["open_loop_status"] = str(open_loop.get("status") or "none")
    enriched["opposition_status"] = str(opposition.get("status") or "none")
    enriched["closure_confidence"] = str(open_loop.get("closure_confidence") or "low")
    enriched["short_outlook"] = _build_short_outlook(snapshot=snapshot)
    enriched["short_review_note"] = str(item.get("summary") or _build_short_review_note(title_suffix=_domain_title(domain_key), snapshot=snapshot))
    return enriched


def _run_summary(run: dict[str, object]) -> str:
    return str(run.get("short_review_note") or run.get("summary") or "")


def _run_support_summary(run: dict[str, object]) -> str:
    return _merge_fragments(
        str(run.get("support_summary") or ""),
        str(run.get("review_focus") or ""),
        str(run.get("short_outlook") or ""),
    )


def _build_review_focus(*, snapshot: dict[str, object]) -> str:
    parts: list[str] = []
    if snapshot.get("open_loop"):
        parts.append("open-loop pressure")
    elif snapshot.get("softening_loop"):
        parts.append("softening loop")
    if snapshot.get("active_opposition"):
        parts.append("active opposition")
    elif snapshot.get("softening_opposition"):
        parts.append("softening opposition")
    if snapshot.get("blocked_goal"):
        parts.append("blocked direction")
    elif snapshot.get("active_goal"):
        parts.append("active direction")
    if snapshot.get("witness"):
        parts.append("carried lesson")
    return " + ".join(parts[:3]) or "bounded-self-review"


def _build_short_outlook(*, snapshot: dict[str, object]) -> str:
    if snapshot.get("open_loop") and snapshot.get("active_opposition"):
        return "Pressure is still live enough that the review should stay narrow and concrete."
    if snapshot.get("softening_loop") or snapshot.get("softening_opposition"):
        return "Pressure is easing, so the review can stay short and integration-focused."
    if snapshot.get("witness"):
        return "A carried lesson is still visible and should be checked before it drops out."
    return "The bounded review should stay close to visible runtime truth."


def _build_short_review_note(*, title_suffix: str, snapshot: dict[str, object]) -> str:
    focus = _build_review_focus(snapshot=snapshot)
    outlook = _build_short_outlook(snapshot=snapshot)
    return f"Review {title_suffix.lower()} through {focus}. {outlook}"


def _stronger_confidence(*values: str) -> str:
    ordered = [str(value or "").strip() for value in values if str(value or "").strip()]
    if "high" in ordered:
        return "high"
    if "medium" in ordered:
        return "medium"
    return ordered[0] if ordered else "low"


def _focus_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _goal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 2 else ""


def _witness_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _open_loop_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _internal_opposition_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _self_review_run_domain_key(canonical_key: str) -> str:
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
