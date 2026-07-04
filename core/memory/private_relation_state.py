from __future__ import annotations

_LEVEL_SCALE = {"low": 0.0, "medium": 0.5, "high": 1.0}


def _observe_private_relation_state(*, active: bool, current: dict | None) -> None:
    """Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN aktiv-flag +
    mode/confidence-labels (skalarer), ALDRIG user-preview/retained-focus-teksten.
    record_private = lokal trace + tidsserie, aldrig _emit. Self-safe."""
    try:
        from core.services.central_private_observe import record_private
        cur = current or {}
        confidence = str(cur.get("confidence") or "low")
        record_private(
            "cognition", "private_relation_state",
            value=_LEVEL_SCALE.get(confidence, 0.0) if active else 0.0,
            meta={
                "active": bool(active),
                "continuity_mode": str(cur.get("continuity_mode") or ""),
                "interaction_mode": str(cur.get("interaction_mode") or ""),
                "confidence": confidence,
            },
        )
    except Exception:
        pass


def build_private_relation_state(
    *,
    visible_session_continuity: dict[str, object] | None,
    visible_continuity: dict[str, object] | None,
    visible_selected_work_item: dict[str, object] | None,
    private_retained_memory_projection: dict[str, object] | None,
) -> dict[str, object]:
    session = visible_session_continuity or {}
    continuity = visible_continuity or {}
    work_item = visible_selected_work_item or {}
    retained = private_retained_memory_projection or {}

    if not (session or continuity or work_item):
        _observe_private_relation_state(active=False, current=None)
        return {
            "active": False,
            "current": None,
        }

    latest_run_id = str(
        session.get("latest_run_id") or work_item.get("selected_run_id") or ""
    ).strip()
    relation_id = latest_run_id or "current"
    latest_status = str(
        work_item.get("selected_status") or session.get("latest_status") or ""
    ).strip()
    user_preview = str(work_item.get("selected_user_message_preview") or "").strip()
    retained_focus = str(retained.get("retained_focus") or "").strip()
    created_at = (
        session.get("latest_finished_at")
        or retained.get("created_at")
        or work_item.get("selected_run_id")
    )

    current = {
        "relation_id": f"private-relation-state:{relation_id}",
        "source": (
            "visible-session-continuity+visible-continuity+"
            "visible-selected-work-item+private-retained-memory-projection"
        ),
        "continuity_mode": _continuity_mode(
            latest_status=latest_status,
            session=session,
            continuity=continuity,
        ),
        "interaction_mode": _interaction_mode(
            latest_status=latest_status,
            user_preview=user_preview,
            work_item=work_item,
        ),
        "relation_pull": _relation_pull(
            user_preview=user_preview,
            retained_focus=retained_focus,
            work_item=work_item,
        ),
        "confidence": _confidence(
            session=session,
            continuity=continuity,
            user_preview=user_preview,
        ),
        "created_at": created_at,
    }
    _observe_private_relation_state(active=True, current=current)
    return {
        "active": True,
        "current": current,
    }


def _continuity_mode(
    *,
    latest_status: str,
    session: dict[str, object],
    continuity: dict[str, object],
) -> str:
    normalized = latest_status.lower()
    if normalized == "running":
        return "live"
    if normalized in {"completed", "failed", "cancelled"}:
        return "recent"
    if bool(session.get("active")) or bool(continuity.get("active")):
        return "warm"
    return "thin"


def _interaction_mode(
    *,
    latest_status: str,
    user_preview: str,
    work_item: dict[str, object],
) -> str:
    normalized = latest_status.lower()
    capability_id = str(work_item.get("selected_capability_id") or "").strip()
    if normalized == "running" and user_preview:
        return "active-user-led"
    if user_preview and capability_id:
        return "user-tool-work"
    if user_preview:
        return "user-led"
    return "context-held"


def _relation_pull(
    *,
    user_preview: str,
    retained_focus: str,
    work_item: dict[str, object],
) -> str:
    if user_preview:
        return "respond-current-user"
    if str(work_item.get("selected_work_preview") or "").strip():
        return "hold-current-work"
    if retained_focus:
        return "hold-recent-context"
    return "standby"


def _confidence(
    *,
    session: dict[str, object],
    continuity: dict[str, object],
    user_preview: str,
) -> str:
    if user_preview and bool(session.get("active")):
        return "medium"
    if bool(continuity.get("active")):
        return "medium"
    return "low"
