from __future__ import annotations


def build_operational_preference_alignment(
    *,
    private_operational_preference: dict[str, object] | None,
    lane_targets: dict[str, dict[str, object]] | None,
) -> dict[str, object]:
    preference = private_operational_preference or {}
    targets = lane_targets or {}

    if not preference:
        return {
            "active": False,
            "current": None,
        }

    preferred_lane = str(preference.get("preferred_lane") or "").strip()
    preferred_target = dict(targets.get(preferred_lane) or {})
    configured_lane = preferred_lane if bool(preferred_target.get("active")) else "none"

    return {
        "active": True,
        "current": {
            "alignment_id": (
                "operational-preference-alignment:"
                f"{preference.get('preference_id') or preferred_lane or 'current'}"
            ),
            "preferred_lane": preferred_lane,
            "configured_lane": configured_lane,
            "alignment_status": _alignment_status(
                preferred_lane=preferred_lane,
                preferred_target=preferred_target,
            ),
            "mismatch_reason": _mismatch_reason(
                preferred_lane=preferred_lane,
                preferred_target=preferred_target,
            ),
            "recommended_action": _recommended_action(
                preferred_lane=preferred_lane,
                preferred_target=preferred_target,
            ),
            "confidence": str(preference.get("confidence") or "low")[:32],
            "created_at": preference.get("created_at"),
        },
    }


def _alignment_status(
    *, preferred_lane: str, preferred_target: dict[str, object]
) -> str:
    if not preferred_lane:
        return "missing-preference"
    if not bool(preferred_target.get("active")):
        return "unconfigured"
    if not bool(preferred_target.get("credentials_ready", True)):
        return "configured-not-ready"
    return "aligned"


def _mismatch_reason(
    *, preferred_lane: str, preferred_target: dict[str, object]
) -> str | None:
    if not preferred_lane:
        return "missing-preference"
    if not bool(preferred_target.get("active")):
        return "preferred-lane-not-configured"
    if not bool(preferred_target.get("credentials_ready", True)):
        return "preferred-lane-auth-not-ready"
    return None


def _recommended_action(
    *, preferred_lane: str, preferred_target: dict[str, object]
) -> str:
    if not preferred_lane:
        return "no-preference"
    if not bool(preferred_target.get("active")):
        return "configure-preferred-lane"
    if not bool(preferred_target.get("credentials_ready", True)):
        return "preferred-lane-not-ready"
    return "keep-current"
