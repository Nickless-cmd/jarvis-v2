from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_cached_runtime_surface,
)


_ROLE_NAMES = ("critic", "witness-helper", "planner-helper")


def build_subagent_ecology_surface() -> dict[str, object]:
    return get_cached_runtime_surface(
        "subagent_ecology_surface",
        _build_subagent_ecology_surface_uncached,
    )


def _build_subagent_ecology_surface_uncached() -> dict[str, object]:
    return build_subagent_ecology_from_sources(
        affective_meta_state=_safe_affective_meta_state(),
        epistemic_runtime_state=_safe_epistemic_runtime_state(),
        conflict_trace=_safe_conflict_trace(),
        loop_runtime=_safe_loop_runtime(),
        prompt_evolution=_safe_prompt_evolution(),
        quiet_initiative=_safe_quiet_initiative(),
    )


def build_subagent_ecology_from_sources(
    *,
    affective_meta_state: dict[str, object] | None,
    epistemic_runtime_state: dict[str, object] | None,
    conflict_trace: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
    prompt_evolution: dict[str, object] | None,
    quiet_initiative: dict[str, object] | None,
) -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()

    affective = affective_meta_state or {}
    epistemic = epistemic_runtime_state or {}
    conflict = conflict_trace or {}
    loops = loop_runtime or {}
    prompt = prompt_evolution or {}
    quiet = quiet_initiative or {}

    loop_summary = loops.get("summary") or {}
    prompt_summary = prompt.get("summary") or {}
    latest_prompt = prompt.get("latest_proposal") or {}

    roles = [
        _build_critic_role(
            epistemic=epistemic,
            conflict=conflict,
            built_at=built_at,
        ),
        _build_witness_helper_role(
            affective=affective,
            quiet=quiet,
            built_at=built_at,
        ),
        _build_planner_helper_role(
            loop_summary=loop_summary,
            prompt_summary=prompt_summary,
            latest_prompt=latest_prompt,
            built_at=built_at,
        ),
    ]

    active_roles = [role for role in roles if role["current_status"] == "active"]
    cooling_roles = [role for role in roles if role["current_status"] == "cooling"]
    blocked_roles = [role for role in roles if role["current_status"] == "blocked"]
    idle_roles = [role for role in roles if role["current_status"] == "idle"]
    last_active_role = active_roles[0] if active_roles else (cooling_roles[0] if cooling_roles else None)

    return {
        "roles": roles,
        "summary": {
            "role_count": len(roles),
            "active_count": len(active_roles),
            "idle_count": len(idle_roles),
            "cooling_count": len(cooling_roles),
            "blocked_count": len(blocked_roles),
            "last_active_role_name": str((last_active_role or {}).get("role_name") or "none"),
            "last_active_role_status": str((last_active_role or {}).get("current_status") or "none"),
            "last_activation_reason": str((last_active_role or {}).get("activation_reason") or "none"),
        },
        "source_contributors": _source_contributors(
            affective=affective,
            epistemic=epistemic,
            conflict=conflict,
            loop_summary=loop_summary,
            prompt_summary=prompt_summary,
            quiet=quiet,
        ),
        "freshness": {
            "built_at": built_at,
            "state": "fresh",
        },
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
        "boundary": "not-memory-not-identity-not-action-not-tool-execution",
        "kind": "subagent-ecology-light",
        "summary_text": _summary_text(active_roles, cooling_roles, blocked_roles),
    }


def build_subagent_ecology_prompt_section(surface: dict[str, object] | None = None) -> str:
    state = surface or build_subagent_ecology_surface()
    summary = state.get("summary") or {}
    roles = state.get("roles") or []
    active = [role for role in roles if role.get("current_status") == "active"]
    role_text = ", ".join(
        (
            f"{role.get('role_name')}={role.get('current_status')}"
            f"({role.get('activation_reason') or 'steady'})"
        )
        for role in (active[:2] or roles[:2])
        if role.get("role_name")
    ) or "none"
    freshness = state.get("freshness") or {}
    return "\n".join(
        [
            "Subagent ecology light (derived runtime truth, internal-only):",
            (
                f"- roles={int(summary.get('role_count') or 0)}"
                f" | active={int(summary.get('active_count') or 0)}"
                f" | cooling={int(summary.get('cooling_count') or 0)}"
                f" | blocked={int(summary.get('blocked_count') or 0)}"
                f" | freshness={freshness.get('state') or 'unknown'}"
            ),
            (
                f"- active_roles={role_text}"
                f" | tool_access={state.get('tool_access') or 'none'}"
                f" | boundary={state.get('boundary') or 'internal-only'}"
            ),
            f"- guidance={_guidance_for_ecology(active_roles=active, roles=roles)}",
        ]
    )


def _build_critic_role(
    *,
    epistemic: dict[str, object],
    conflict: dict[str, object],
    built_at: str,
) -> dict[str, object]:
    wrongness = str(epistemic.get("wrongness_state") or "clear")
    regret = str(epistemic.get("regret_signal") or "none")
    conflict_outcome = str(conflict.get("outcome") or "none")
    conflict_reason = str(conflict.get("reason_code") or "none")

    status = "idle"
    reason = "no-epistemic-friction"
    if wrongness == "strained" or regret == "active":
        status = "active"
        reason = f"epistemic-{wrongness}"
    elif wrongness in {"off", "uneasy"} or conflict_outcome in {"defer", "quiet_hold"}:
        status = "blocked" if conflict_outcome == "defer" else "active"
        reason = conflict_reason if conflict_reason != "none" else f"epistemic-{wrongness}"

    return _role(
        role_name="critic",
        role_kind="epistemic-check",
        current_status=status,
        activation_reason=reason,
        last_activation_at=built_at if status != "idle" else "",
    )


def _build_witness_helper_role(
    *,
    affective: dict[str, object],
    quiet: dict[str, object],
    built_at: str,
) -> dict[str, object]:
    affective_state = str(affective.get("state") or "settled")
    reflective_load = str(affective.get("reflective_load") or "low")

    status = "idle"
    reason = "no-reflective-pull"
    if affective_state == "reflective":
        status = "active"
        reason = "reflective-bearing-live"
    elif quiet.get("active") or affective_state == "tense":
        status = "active"
        reason = "holding-pressure-needs-witness"
    elif reflective_load in {"medium", "high"}:
        status = "cooling"
        reason = f"reflective-load-{reflective_load}"

    return _role(
        role_name="witness-helper",
        role_kind="reflective-observer",
        current_status=status,
        activation_reason=reason,
        last_activation_at=built_at if status != "idle" else "",
    )


def _build_planner_helper_role(
    *,
    loop_summary: dict[str, object],
    prompt_summary: dict[str, object],
    latest_prompt: dict[str, object],
    built_at: str,
) -> dict[str, object]:
    active_count = int(loop_summary.get("active_count") or 0)
    standby_count = int(loop_summary.get("standby_count") or 0)
    resumed_count = int(loop_summary.get("resumed_count") or 0)
    proposal_type = str(latest_prompt.get("proposal_type") or "")
    proposal_state = str(prompt_summary.get("last_state") or "idle")

    status = "idle"
    reason = "no-coordination-pull"
    if active_count > 0 or resumed_count > 0:
        status = "active"
        reason = "loop-pressure-live"
    elif proposal_type or proposal_state in {"forming", "pressing", "tentative"}:
        status = "cooling"
        reason = "prompt-proposal-reviewable"
    elif standby_count > 0:
        status = "cooling"
        reason = "standby-loops-held"

    return _role(
        role_name="planner-helper",
        role_kind="bounded-coordination",
        current_status=status,
        activation_reason=reason,
        last_activation_at=built_at if status != "idle" else "",
    )


def _role(
    *,
    role_name: str,
    role_kind: str,
    current_status: str,
    activation_reason: str,
    last_activation_at: str,
) -> dict[str, object]:
    return {
        "role_name": role_name,
        "role_kind": role_kind,
        "current_status": current_status,
        "last_activation_at": last_activation_at,
        "activation_reason": activation_reason,
        "internal_only": True,
        "tool_access": "none",
        "influence_scope": "bounded",
    }


def _source_contributors(
    *,
    affective: dict[str, object],
    epistemic: dict[str, object],
    conflict: dict[str, object],
    loop_summary: dict[str, object],
    prompt_summary: dict[str, object],
    quiet: dict[str, object],
) -> list[dict[str, str]]:
    contributors: list[dict[str, str]] = []
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
    if int(loop_summary.get("loop_count") or 0) > 0:
        contributors.append(
            {
                "source": "loop-runtime",
                "signal": (
                    f"{str(loop_summary.get('current_status') or 'none')}"
                    f" / active={int(loop_summary.get('active_count') or 0)}"
                    f" / standby={int(loop_summary.get('standby_count') or 0)}"
                ),
            }
        )
    if str(prompt_summary.get("last_state") or "idle") != "idle":
        contributors.append(
            {
                "source": "prompt-evolution",
                "signal": (
                    f"{str(prompt_summary.get('last_state') or 'idle')}"
                    f" / target={str(prompt_summary.get('latest_target_asset') or 'none')}"
                ),
            }
        )
    if quiet.get("active"):
        contributors.append(
            {
                "source": "quiet-initiative",
                "signal": (
                    f"{str(quiet.get('state') or 'holding')}"
                    f" / hold_count={int(quiet.get('hold_count') or 0)}"
                ),
            }
        )
    return contributors[:6]


def _summary_text(
    active_roles: list[dict[str, object]],
    cooling_roles: list[dict[str, object]],
    blocked_roles: list[dict[str, object]],
) -> str:
    if active_roles:
        return f"active internal roles: {', '.join(str(role.get('role_name')) for role in active_roles[:3])}"
    if blocked_roles:
        return f"blocked internal roles: {', '.join(str(role.get('role_name')) for role in blocked_roles[:3])}"
    if cooling_roles:
        return f"cooling internal roles: {', '.join(str(role.get('role_name')) for role in cooling_roles[:3])}"
    return "subagent ecology idle"


def _guidance_for_ecology(
    *,
    active_roles: list[dict[str, object]],
    roles: list[dict[str, object]],
) -> str:
    active_names = {str(role.get("role_name") or "") for role in active_roles}
    if "critic" in active_names and "planner-helper" in active_names:
        return "Keep planning bounded and let the critic constrain overclaiming."
    if "critic" in active_names:
        return "Let the critic sharpen claims, not widen them."
    if "witness-helper" in active_names:
        return "Use witness-style observation before adding pressure or closure."
    if "planner-helper" in active_names:
        return "Prefer small bounded coordination, not broad action claims."
    if any(str(role.get("current_status") or "") == "cooling" for role in roles):
        return "Internal helper roles are cooling; keep them available but quiet."
    return "Internal helper roles are idle; do not imply agentic delegation."


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


def _safe_loop_runtime() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.loop_runtime import (
            build_loop_runtime_surface,
        )
        return build_loop_runtime_surface()
    except Exception:
        return None


def _safe_prompt_evolution() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.prompt_evolution_runtime import (
            build_prompt_evolution_runtime_surface,
        )
        return build_prompt_evolution_runtime_surface()
    except Exception:
        return None


def _safe_quiet_initiative() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.conflict_resolution import (
            get_quiet_initiative,
        )
        return get_quiet_initiative()
    except Exception:
        return None
