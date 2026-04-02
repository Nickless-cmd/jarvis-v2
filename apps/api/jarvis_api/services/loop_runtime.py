from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_cached_runtime_surface,
)

_LAST_LOOP_RUNTIME: dict[str, object] | None = None
_RECENTLY_CLOSED_WINDOW = timedelta(minutes=20)


def build_loop_runtime_surface() -> dict[str, object]:
    return get_cached_runtime_surface(
        "loop_runtime_surface",
        _build_loop_runtime_surface_uncached,
    )


def _build_loop_runtime_surface_uncached() -> dict[str, object]:
    global _LAST_LOOP_RUNTIME

    from apps.api.jarvis_api.services.open_loop_signal_tracking import (
        build_runtime_open_loop_signal_surface,
    )
    from apps.api.jarvis_api.services.proactive_loop_lifecycle_tracking import (
        build_runtime_proactive_loop_lifecycle_surface,
    )
    from apps.api.jarvis_api.services.conflict_resolution import (
        get_quiet_initiative,
    )

    surface = build_loop_runtime_from_sources(
        open_loop_surface=build_runtime_open_loop_signal_surface(limit=8),
        proactive_loop_surface=build_runtime_proactive_loop_lifecycle_surface(limit=8),
        quiet_initiative=get_quiet_initiative(),
        previous=_LAST_LOOP_RUNTIME,
    )
    _LAST_LOOP_RUNTIME = surface
    return surface


def build_loop_runtime_from_sources(
    *,
    open_loop_surface: dict[str, object] | None,
    proactive_loop_surface: dict[str, object] | None,
    quiet_initiative: dict[str, object] | None,
    previous: dict[str, object] | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    built_at = now or datetime.now(UTC)
    previous_items = {
        str(item.get("loop_id") or ""): item
        for item in (previous or {}).get("items", [])
        if str(item.get("loop_id") or "").strip()
    }

    items: list[dict[str, object]] = []
    items.extend(_open_loop_items(open_loop_surface, previous_items=previous_items))
    items.extend(_proactive_loop_items(proactive_loop_surface, previous_items=previous_items))

    quiet_item = _quiet_initiative_item(
        quiet_initiative,
        previous_items=previous_items,
        built_at=built_at,
    )
    if quiet_item is not None:
        items.append(quiet_item)

    items.sort(key=_loop_item_sort_key)

    active = [item for item in items if item.get("runtime_status") == "active"]
    standby = [item for item in items if item.get("runtime_status") == "standby"]
    resumed = [item for item in items if item.get("runtime_status") == "resumed"]
    closed = [item for item in items if item.get("runtime_status") == "closed"]
    latest = next(iter(resumed or active or standby or closed), None)

    return {
        "active": bool(active or standby or resumed),
        "authority": "authoritative",
        "visibility": "internal-only",
        "kind": "loop-runtime-state",
        "items": items,
        "summary": {
            "active_count": len(active),
            "standby_count": len(standby),
            "resumed_count": len(resumed),
            "closed_count": len(closed),
            "current_loop": str((latest or {}).get("title") or "No active runtime loop"),
            "current_status": str((latest or {}).get("runtime_status") or "none"),
            "current_kind": str((latest or {}).get("loop_kind") or "none"),
            "current_reason": str((latest or {}).get("reason_code") or "none"),
            "loop_count": len(items),
        },
        "freshness": {
            "built_at": built_at.isoformat(),
            "state": "fresh",
        },
        "seam_usage": {
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
        },
    }


def build_loop_runtime_prompt_section(surface: dict[str, object] | None = None) -> str | None:
    runtime = surface or build_loop_runtime_surface()
    summary = runtime.get("summary") or {}
    items = runtime.get("items") or []
    if not items:
        return None

    lead = []
    for item in items[:3]:
        lead.append(
            f"{item.get('title') or 'loop'}={item.get('runtime_status') or 'unknown'}"
        )

    return "\n".join(
        [
            "Loop runtime (authoritative runtime truth, internal-only):",
            (
                f"- active={summary.get('active_count') or 0}"
                f" | standby={summary.get('standby_count') or 0}"
                f" | resumed={summary.get('resumed_count') or 0}"
                f" | closed={summary.get('closed_count') or 0}"
            ),
            (
                f"- current={summary.get('current_loop') or 'none'}"
                f" | status={summary.get('current_status') or 'none'}"
                f" | kind={summary.get('current_kind') or 'none'}"
            ),
            f"- lead={'; '.join(lead)}",
        ]
    )


def _open_loop_items(
    surface: dict[str, object] | None,
    *,
    previous_items: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for raw in (surface or {}).get("items", []):
        status = str(raw.get("status") or "")
        runtime_status = {
            "open": "active",
            "softening": "standby",
            "closed": "closed",
        }.get(status)
        if runtime_status is None:
            continue
        loop_id = f"open-loop:{raw.get('canonical_key') or raw.get('signal_id') or raw.get('title')}"
        previous_status = str((previous_items.get(loop_id) or {}).get("runtime_status") or "")
        if previous_status == "standby" and runtime_status == "active":
            runtime_status = "resumed"
        items.append(
            {
                "loop_id": loop_id,
                "title": str(raw.get("title") or raw.get("summary") or "Open loop"),
                "runtime_status": runtime_status,
                "loop_kind": "open-loop",
                "source_type": "open-loop-signal",
                "source_status": status,
                "canonical_key": str(raw.get("canonical_key") or ""),
                "reason_code": _reason_code_for_open_loop(status),
                "summary": str(raw.get("summary") or raw.get("status_reason") or ""),
                "updated_at": str(raw.get("updated_at") or raw.get("created_at") or ""),
                "boundary": "not-memory-not-identity-not-action",
            }
        )
    return items


def _proactive_loop_items(
    surface: dict[str, object] | None,
    *,
    previous_items: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for raw in (surface or {}).get("items", []):
        status = str(raw.get("status") or "")
        runtime_status = {
            "active": "active",
            "softening": "standby",
        }.get(status)
        if runtime_status is None:
            continue
        loop_kind = str(raw.get("loop_kind") or "proactive-loop")
        loop_focus = str(raw.get("loop_focus") or raw.get("title") or "")
        loop_id = f"proactive-loop:{raw.get('canonical_key') or loop_kind}:{loop_focus}"
        previous_status = str((previous_items.get(loop_id) or {}).get("runtime_status") or "")
        if previous_status == "standby" and runtime_status == "active":
            runtime_status = "resumed"
        items.append(
            {
                "loop_id": loop_id,
                "title": str(raw.get("title") or "Proactive loop"),
                "runtime_status": runtime_status,
                "loop_kind": loop_kind,
                "source_type": "proactive-loop-lifecycle",
                "source_status": status,
                "canonical_key": str(raw.get("canonical_key") or ""),
                "reason_code": _reason_code_for_proactive_loop(status, str(raw.get("loop_state") or "")),
                "summary": str(raw.get("summary") or raw.get("status_reason") or ""),
                "updated_at": str(raw.get("updated_at") or raw.get("created_at") or ""),
                "boundary": "not-memory-not-identity-not-action",
            }
        )
    return items


def _quiet_initiative_item(
    quiet: dict[str, object] | None,
    *,
    previous_items: dict[str, dict[str, object]],
    built_at: datetime,
) -> dict[str, object] | None:
    if not quiet:
        return None
    focus = str(quiet.get("focus") or "").strip()
    state = str(quiet.get("state") or "holding")
    active = bool(quiet.get("active"))
    last_seen = _parse_iso(quiet.get("last_seen_at"))

    if not active and state not in {"promoted", "expired", "released"}:
        return None
    if not active and last_seen is not None and built_at - last_seen > _RECENTLY_CLOSED_WINDOW:
        return None

    loop_id = f"quiet-initiative:{focus or 'quiet-hold'}"
    previous_status = str((previous_items.get(loop_id) or {}).get("runtime_status") or "")
    runtime_status = "standby" if active else "closed"
    if previous_status == "standby" and active:
        runtime_status = "resumed"

    return {
        "loop_id": loop_id,
        "title": focus or "Quiet initiative",
        "runtime_status": runtime_status,
        "loop_kind": "quiet-held-loop",
        "source_type": "quiet-initiative",
        "source_status": state,
        "canonical_key": "",
        "reason_code": (
            "quiet-hold-active"
            if active
            else f"quiet-hold-{state or 'closed'}"
        ),
        "summary": str(quiet.get("reason_code") or "Quiet initiative remains held internally."),
        "updated_at": str(quiet.get("last_seen_at") or quiet.get("created_at") or ""),
        "boundary": "not-memory-not-identity-not-action",
    }


def _loop_item_sort_key(item: dict[str, object]) -> tuple[int, str]:
    rank = {
        "resumed": 0,
        "active": 1,
        "standby": 2,
        "closed": 3,
    }.get(str(item.get("runtime_status") or ""), 9)
    updated_at = str(item.get("updated_at") or "")
    return (rank, updated_at)


def _reason_code_for_open_loop(status: str) -> str:
    return {
        "open": "open-loop-active",
        "softening": "open-loop-standby",
        "closed": "open-loop-closed",
    }.get(status, "open-loop-unknown")


def _reason_code_for_proactive_loop(status: str, loop_state: str) -> str:
    state = loop_state or "none"
    if status == "active":
        return f"proactive-loop-active:{state}"
    if status == "softening":
        return f"proactive-loop-standby:{state}"
    return f"proactive-loop:{state}"


def _parse_iso(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
