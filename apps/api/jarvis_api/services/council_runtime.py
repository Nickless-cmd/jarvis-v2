from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_cached_runtime_surface,
)


def build_council_runtime_surface() -> dict[str, object]:
    return get_cached_runtime_surface(
        "council_runtime_surface",
        _build_council_runtime_surface_uncached,
    )


def _build_council_runtime_surface_uncached() -> dict[str, object]:
    return build_council_runtime_from_sources(
        subagent_ecology=_safe_subagent_ecology(),
        affective_meta_state=_safe_affective_meta_state(),
        epistemic_runtime_state=_safe_epistemic_runtime_state(),
        conflict_trace=_safe_conflict_trace(),
    )


def build_council_runtime_from_sources(
    *,
    subagent_ecology: dict[str, object] | None,
    affective_meta_state: dict[str, object] | None,
    epistemic_runtime_state: dict[str, object] | None,
    conflict_trace: dict[str, object] | None,
) -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()

    ecology = subagent_ecology or {}
    affective = affective_meta_state or {}
    epistemic = epistemic_runtime_state or {}
    conflict = conflict_trace or {}

    roles = ecology.get("roles") or []
    participating_roles = [str(role.get("role_name") or "") for role in roles if role.get("role_name")]
    role_positions = [
        _role_position(
            role=role,
            affective=affective,
            epistemic=epistemic,
            conflict=conflict,
        )
        for role in roles[:3]
    ]
    divergence_level = _derive_divergence_level(role_positions)
    recommendation = _derive_recommendation(role_positions)
    recommendation_reason = _derive_recommendation_reason(
        recommendation=recommendation,
        divergence_level=divergence_level,
        affective=affective,
        epistemic=epistemic,
        conflict=conflict,
    )
    confidence = _derive_confidence(
        recommendation=recommendation,
        divergence_level=divergence_level,
        role_positions=role_positions,
    )
    council_state = _derive_council_state(
        role_positions=role_positions,
        divergence_level=divergence_level,
    )

    return {
        "council_state": council_state,
        "participating_roles": participating_roles,
        "role_positions": role_positions,
        "divergence_level": divergence_level,
        "recommendation": recommendation,
        "recommendation_reason": recommendation_reason,
        "confidence": confidence,
        "last_council_at": built_at,
        "summary": (
            f"{council_state} council"
            f" with {recommendation} recommendation"
            f" at {divergence_level} divergence"
        ),
        "source_contributors": _source_contributors(
            ecology=ecology,
            affective=affective,
            epistemic=epistemic,
            conflict=conflict,
        ),
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "internal_only": True,
        "tool_access": "none",
        "influence_scope": "bounded",
        "boundary": "not-memory-not-identity-not-action-not-tool-execution",
        "kind": "council-runtime-light",
    }


def build_council_runtime_prompt_section(surface: dict[str, object] | None = None) -> str:
    state = surface or build_council_runtime_surface()
    role_positions = state.get("role_positions") or []
    role_text = ", ".join(
        f"{item.get('role_name')}->{item.get('position')}"
        for item in role_positions[:3]
        if item.get("role_name")
    ) or "none"
    return "\n".join(
        [
            "Council runtime light (derived runtime truth, internal-only):",
            (
                f"- state={state.get('council_state') or 'quiet'}"
                f" | recommendation={state.get('recommendation') or 'none'}"
                f" | divergence={state.get('divergence_level') or 'low'}"
                f" | confidence={state.get('confidence') or 'low'}"
            ),
            (
                f"- roles={role_text}"
                f" | tool_access={state.get('tool_access') or 'none'}"
                f" | boundary={state.get('boundary') or 'internal-only'}"
            ),
            f"- guidance={_guidance_for_council(state=state)}",
        ]
    )


def _role_position(
    *,
    role: dict[str, object],
    affective: dict[str, object],
    epistemic: dict[str, object],
    conflict: dict[str, object],
) -> dict[str, object]:
    role_name = str(role.get("role_name") or "")
    current_status = str(role.get("current_status") or "idle")
    activation_reason = str(role.get("activation_reason") or "none")

    position = "hold"
    if role_name == "critic":
        # "off" = no active assessment (neutral), only "strained" = actual concern
        if str(epistemic.get("wrongness_state") or "clear") == "strained":
            position = "constrain"
        elif current_status == "blocked":
            position = "hold"
    elif role_name == "witness-helper":
        if str(affective.get("state") or "settled") in {"reflective", "tense"}:
            position = "observe"
        elif current_status == "cooling":
            position = "hold"
    elif role_name == "planner-helper":
        if current_status == "active":
            position = "advance"
        elif current_status == "cooling":
            position = "hold"

    if str(conflict.get("outcome") or "none") == "defer" and role_name == "planner-helper":
        position = "hold"

    return {
        "role_name": role_name,
        "role_kind": str(role.get("role_kind") or "internal-role"),
        "status": current_status,
        "position": position,
        "activation_reason": activation_reason,
        "tool_access": "none",
        "internal_only": True,
    }


def _derive_divergence_level(role_positions: list[dict[str, object]]) -> str:
    positions = {str(item.get("position") or "hold") for item in role_positions if item.get("role_name")}
    if not positions or positions == {"hold"}:
        return "low"
    if len(positions) == 1:
        return "low"
    if len(positions) == 2:
        return "medium"
    return "high"


def _derive_recommendation(role_positions: list[dict[str, object]]) -> str:
    positions = {str(item.get("role_name") or ""): str(item.get("position") or "hold") for item in role_positions}
    critic = positions.get("critic", "hold")
    witness = positions.get("witness-helper", "hold")
    planner = positions.get("planner-helper", "hold")

    if critic == "constrain":
        return "bounded-check"
    if planner == "advance" and witness in {"observe", "hold"}:
        return "carry-forward"
    if witness == "observe":
        return "observe-more"
    return "hold"


def _derive_recommendation_reason(
    *,
    recommendation: str,
    divergence_level: str,
    affective: dict[str, object],
    epistemic: dict[str, object],
    conflict: dict[str, object],
) -> str:
    if recommendation == "bounded-check":
        return (
            f"critic-pressure from wrongness={str(epistemic.get('wrongness_state') or 'clear')}"
            f" and conflict={str(conflict.get('outcome') or 'none')}"
        )
    if recommendation == "carry-forward":
        return f"planner pressure stayed live under {str(affective.get('state') or 'settled')} bearing"
    if recommendation == "observe-more":
        return f"witness pressure favored observation under {str(affective.get('state') or 'settled')} state"
    return f"council stayed held at {divergence_level} divergence"


def _derive_confidence(
    *,
    recommendation: str,
    divergence_level: str,
    role_positions: list[dict[str, object]],
) -> str:
    active_positions = [item for item in role_positions if str(item.get("status") or "") in {"active", "blocked"}]
    if recommendation == "bounded-check" and divergence_level in {"low", "medium"}:
        return "high"
    if recommendation in {"carry-forward", "observe-more"} and active_positions:
        return "medium"
    return "low"


def _derive_council_state(
    *,
    role_positions: list[dict[str, object]],
    divergence_level: str,
) -> str:
    if not role_positions:
        return "quiet"
    if divergence_level == "high":
        return "diverging"
    if any(str(item.get("position") or "") == "constrain" for item in role_positions):
        return "checking"
    if any(str(item.get("position") or "") == "advance" for item in role_positions):
        return "aligned"
    if any(str(item.get("position") or "") == "observe" for item in role_positions):
        return "reflecting"
    return "held"


def _source_contributors(
    *,
    ecology: dict[str, object],
    affective: dict[str, object],
    epistemic: dict[str, object],
    conflict: dict[str, object],
) -> list[dict[str, str]]:
    contributors: list[dict[str, str]] = []
    summary = ecology.get("summary") or {}
    contributors.append(
        {
            "source": "subagent-ecology",
            "signal": (
                f"active={int(summary.get('active_count') or 0)}"
                f" / blocked={int(summary.get('blocked_count') or 0)}"
                f" / last={str(summary.get('last_active_role_name') or 'none')}"
            ),
        }
    )
    contributors.append(
        {
            "source": "affective-meta-state",
            "signal": (
                f"{str(affective.get('state') or 'settled')}"
                f" / bearing={str(affective.get('bearing') or 'even')}"
            ),
        }
    )
    contributors.append(
        {
            "source": "epistemic-runtime-state",
            "signal": (
                f"{str(epistemic.get('wrongness_state') or 'clear')}"
                f" / regret={str(epistemic.get('regret_signal') or 'none')}"
            ),
        }
    )
    if str(conflict.get("outcome") or "none") != "none":
        contributors.append(
            {
                "source": "conflict-resolution",
                "signal": (
                    f"{str(conflict.get('outcome') or 'none')}"
                    f" / reason={str(conflict.get('reason_code') or 'none')}"
                ),
            }
        )
    return contributors[:4]


def _guidance_for_council(*, state: dict[str, object]) -> str:
    recommendation = str(state.get("recommendation") or "hold")
    divergence = str(state.get("divergence_level") or "low")
    if recommendation == "bounded-check":
        return "Let council pressure narrow claims before any forward push."
    if recommendation == "carry-forward":
        return "Carry forward carefully, but keep the council bounded and internal."
    if recommendation == "observe-more":
        return "Prefer observation and witness-style settling before stronger movement."
    if divergence == "high":
        return "Keep the council in bounded hold; do not treat divergence as authorization."
    return "Council is held and internal; do not imply delegation or execution."


def _safe_subagent_ecology() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.subagent_ecology import (
            build_subagent_ecology_surface,
        )
        return build_subagent_ecology_surface()
    except Exception:
        return None


def _safe_affective_meta_state() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.affective_meta_state import (
            build_affective_meta_state_surface,
        )
        return build_affective_meta_state_surface()
    except Exception:
        return None


def _safe_epistemic_runtime_state() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.epistemic_runtime_state import (
            build_epistemic_runtime_state_surface,
        )
        return build_epistemic_runtime_state_surface()
    except Exception:
        return None


def _safe_conflict_trace() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.conflict_resolution import (
            get_last_conflict_trace,
        )
        return get_last_conflict_trace()
    except Exception:
        return None


def get_latest_council_conclusion() -> dict[str, object] | None:
    """Return the most recent closed council session summary, or None."""
    try:
        from core.runtime.db import list_council_sessions
        sessions = list_council_sessions(limit=20)
        closed = [s for s in sessions if str(s.get("status") or "") == "closed"]
        if not closed:
            return None
        latest = closed[0]
        return {
            "council_id": str(latest.get("council_id") or ""),
            "topic": str(latest.get("topic") or ""),
            "summary": str(latest.get("summary") or ""),
            "updated_at": str(latest.get("updated_at") or ""),
            "mode": str(latest.get("mode") or "council"),
        }
    except Exception:
        return None
