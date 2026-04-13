from __future__ import annotations

from datetime import UTC, datetime


def _safe_build(
    builder: object,
    system_id: str,
    label: str,
) -> dict[str, object]:
    """Call a builder function, returning a disabled-stub on any error."""
    try:
        return builder()  # type: ignore[operator]
    except Exception:
        return {
            "id": system_id,
            "label": label,
            "enabled": False,
            "active": False,
            "activity_state": "error",
            "core_status": "unknown",
            "carry_capable": False,
            "carry_domain": "unknown",
            "carry_strength": "none",
            "observational_only": False,
            "summary": "error: could not load state",
            "source_summary": {},
        }


def build_cognitive_core_experiments_surface() -> dict[str, object]:
    """Build shared runtime truth for the bounded cognitive-core experiment state.

    This is not a new experiment engine. It is a small integration surface that
    classifies the existing experiment families consistently for shared runtime
    awareness.
    """
    recurrence = _safe_build(_build_recurrence_state, "recurrence", "Recurrence loop")
    global_workspace = _safe_build(_build_global_workspace_state, "global_workspace", "Global workspace")
    hot_meta_cognition = _safe_build(_build_hot_meta_cognition_state, "hot_meta_cognition", "HOT meta-cognition")
    surprise_afterimage = _safe_build(_build_surprise_afterimage_state, "surprise_afterimage", "Surprise persistence / afterimage")
    attention_blink = _safe_build(_build_attention_blink_state, "attention_blink", "Attention blink")

    items = [
        recurrence,
        global_workspace,
        hot_meta_cognition,
        surprise_afterimage,
        attention_blink,
    ]
    active_items = [item for item in items if bool(item.get("active"))]
    enabled_items = [item for item in items if bool(item.get("enabled"))]
    carry_items = [item for item in items if bool(item.get("carry_capable"))]
    active_carry_items = [item for item in carry_items if bool(item.get("active"))]
    observational_items = [item for item in items if bool(item.get("observational_only"))]

    strongest_carry = _strongest_carry_item(active_carry_items or carry_items)
    activity_state = (
        "active"
        if active_items
        else "enabled-idle"
        if enabled_items
        else "disabled"
    )
    carry_state = "present" if active_carry_items else "quiet"

    return {
        "kind": "cognitive-core-experiments",
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "boundary": (
            "bounded-runtime-truth-only; no direct policy/action authority; "
            "attention blink remains observational/core-assay"
        ),
        "systems": {
            item["id"]: item for item in items
        },
        "ordered_systems": items,
        "enabled_count": len(enabled_items),
        "active_count": len(active_items),
        "carry_candidate_count": len(carry_items),
        "active_carry_candidate_count": len(active_carry_items),
        "observational_count": len(observational_items),
        "activity_state": activity_state,
        "carry_state": carry_state,
        "strongest_carry_system": str((strongest_carry or {}).get("id") or "none"),
        "strongest_carry_summary": str((strongest_carry or {}).get("summary") or "none"),
        "active_systems": [str(item.get("id") or "") for item in active_items],
        "carry_candidate_systems": [str(item.get("id") or "") for item in carry_items],
        "observational_systems": [str(item.get("id") or "") for item in observational_items],
        "summary": (
            f"{len(active_items)}/{len(items)} active; "
            f"{len(active_carry_items)}/{len(carry_items)} carry-capable active; "
            f"blink=observational"
        ),
        "built_at": datetime.now(UTC).isoformat(),
    }


def _build_recurrence_state() -> dict[str, object]:
    from apps.api.jarvis_api.services.recurrence_loop_daemon import build_recurrence_surface

    surface = build_recurrence_surface()
    active = bool(surface.get("enabled")) and (
        int(surface.get("iteration_count") or 0) > 0
        or float(surface.get("current_stability_score") or 0.0) > 0.0
    )
    return {
        "id": "recurrence",
        "label": "Recurrence loop",
        "enabled": bool(surface.get("enabled")),
        "active": active,
        "activity_state": _activity_state(enabled=bool(surface.get("enabled")), active=active),
        "core_status": "core-candidate",
        "carry_capable": True,
        "carry_domain": "loop-reentry",
        "carry_strength": "medium",
        "observational_only": False,
        "summary": (
            f"loop/re-entry candidate; trend={surface.get('trend') or 'unknown'}; "
            f"stability={surface.get('current_stability_score') or 0.0:.3f}"
        ),
        "source_summary": surface,
    }


def _build_global_workspace_state() -> dict[str, object]:
    from apps.api.jarvis_api.services.broadcast_daemon import build_workspace_surface

    surface = build_workspace_surface()
    active = bool(surface.get("enabled")) and (
        int(surface.get("buffer_size") or 0) > 0
        or float(surface.get("workspace_coherence") or 0.0) > 0.0
        or bool(surface.get("last_broadcast_at"))
    )
    return {
        "id": "global_workspace",
        "label": "Global workspace",
        "enabled": bool(surface.get("enabled")),
        "active": active,
        "activity_state": _activity_state(enabled=bool(surface.get("enabled")), active=active),
        "core_status": "core-candidate",
        "carry_capable": True,
        "carry_domain": "salience-broadcast",
        "carry_strength": "strong",
        "observational_only": False,
        "summary": (
            f"strong salience candidate; coherence={surface.get('workspace_coherence') or 0.0:.3f}; "
            f"buffer={int(surface.get('buffer_size') or 0)}"
        ),
        "source_summary": surface,
    }


def _build_hot_meta_cognition_state() -> dict[str, object]:
    from apps.api.jarvis_api.services.meta_cognition_daemon import build_meta_cognition_surface

    surface = build_meta_cognition_surface()
    active = bool(surface.get("enabled")) and (
        int(surface.get("record_count") or 0) > 0
        or int(surface.get("meta_depth") or 0) > 0
    )
    return {
        "id": "hot_meta_cognition",
        "label": "HOT meta-cognition",
        "enabled": bool(surface.get("enabled")),
        "active": active,
        "activity_state": _activity_state(enabled=bool(surface.get("enabled")), active=active),
        "core_status": "core-candidate",
        "carry_capable": True,
        "carry_domain": "reflective-depth",
        "carry_strength": "medium",
        "observational_only": False,
        "summary": (
            f"reflective-depth candidate; depth={int(surface.get('meta_depth') or 0)}; "
            f"records={int(surface.get('record_count') or 0)}"
        ),
        "source_summary": surface,
    }


def _build_surprise_afterimage_state() -> dict[str, object]:
    from core.runtime.db import get_experiment_enabled
    from apps.api.jarvis_api.services.surprise_daemon import build_surprise_surface

    surface = build_surprise_surface()
    enabled = bool(get_experiment_enabled("surprise_persistence"))
    active = enabled and (
        bool(surface.get("current_afterimage_active"))
        or bool(surface.get("last_surprise"))
        or float(surface.get("affective_persistence_seconds") or 0.0) > 0.0
    )
    return {
        "id": "surprise_afterimage",
        "label": "Surprise persistence / afterimage",
        "enabled": enabled,
        "active": active,
        "activity_state": _activity_state(enabled=enabled, active=active),
        "core_status": "core-candidate",
        "carry_capable": True,
        "carry_domain": "affective-carry",
        "carry_strength": "strong",
        "observational_only": False,
        "summary": (
            f"affective carry candidate; type={surface.get('surprise_type') or 'ingen'}; "
            f"afterimage={bool(surface.get('current_afterimage_active'))}"
        ),
        "source_summary": surface,
    }


def _build_attention_blink_state() -> dict[str, object]:
    from apps.api.jarvis_api.services.attention_blink_test import build_attention_profile_surface

    surface = build_attention_profile_surface()
    active = bool(surface.get("enabled")) and (
        bool(surface.get("currently_running"))
        or int(surface.get("result_count") or 0) > 0
    )
    return {
        "id": "attention_blink",
        "label": "Attention blink",
        "enabled": bool(surface.get("enabled")),
        "active": active,
        "activity_state": _activity_state(enabled=bool(surface.get("enabled")), active=active),
        "core_status": "observational-core-assay",
        "carry_capable": False,
        "carry_domain": "capacity-assay",
        "carry_strength": "none",
        "observational_only": True,
        "summary": (
            f"observational capacity assay; ratio={surface.get('latest_blink_ratio') or 0.0:.3f}; "
            f"state={surface.get('latest_interpretation') or 'none'}"
        ),
        "source_summary": surface,
    }


def _activity_state(*, enabled: bool, active: bool) -> str:
    if not enabled:
        return "disabled"
    if active:
        return "active"
    return "idle"


def _strongest_carry_item(items: list[dict[str, object]]) -> dict[str, object] | None:
    if not items:
        return None
    strength_rank = {"none": 0, "medium": 1, "strong": 2}
    return max(
        items,
        key=lambda item: (
            strength_rank.get(str(item.get("carry_strength") or "none"), 0),
            1 if bool(item.get("active")) else 0,
            str(item.get("id") or ""),
        ),
    )
