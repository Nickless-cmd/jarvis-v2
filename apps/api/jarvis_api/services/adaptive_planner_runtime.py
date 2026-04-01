from __future__ import annotations

from datetime import UTC, datetime


def build_adaptive_planner_runtime_surface() -> dict[str, object]:
    return build_adaptive_planner_runtime_from_sources(
        embodied_state=_safe_embodied_state(),
        affective_meta_state=_safe_affective_meta_state(),
        epistemic_runtime_state=_safe_epistemic_runtime_state(),
        loop_runtime=_safe_loop_runtime(),
        council_runtime=_safe_council_runtime(),
        conflict_trace=_safe_conflict_trace(),
        quiet_initiative=_safe_quiet_initiative(),
    )


def build_adaptive_planner_runtime_from_sources(
    *,
    embodied_state: dict[str, object] | None,
    affective_meta_state: dict[str, object] | None,
    epistemic_runtime_state: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
    council_runtime: dict[str, object] | None,
    conflict_trace: dict[str, object] | None,
    quiet_initiative: dict[str, object] | None,
) -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()

    embodied = embodied_state or {}
    affective = affective_meta_state or {}
    epistemic = epistemic_runtime_state or {}
    loops = loop_runtime or {}
    council = council_runtime or {}
    conflict = conflict_trace or {}
    quiet = quiet_initiative or {}

    loop_summary = loops.get("summary") or {}
    body_state = str(embodied.get("state") or "steady")
    strain_level = str(embodied.get("strain_level") or "low")
    affective_state = str(affective.get("state") or "settled")
    bearing = str(affective.get("bearing") or "even")
    wrongness_state = str(epistemic.get("wrongness_state") or "clear")
    council_recommendation = str(council.get("recommendation") or "hold")
    council_divergence = str(council.get("divergence_level") or "low")
    conflict_outcome = str(conflict.get("outcome") or "none")

    planner_mode = _derive_planner_mode(
        embodied_state=body_state,
        strain_level=strain_level,
        affective_state=affective_state,
        wrongness_state=wrongness_state,
        loop_summary=loop_summary,
        council_recommendation=council_recommendation,
        conflict_outcome=conflict_outcome,
        quiet_initiative=quiet,
    )
    plan_horizon = _derive_plan_horizon(
        planner_mode=planner_mode,
        loop_summary=loop_summary,
        council_divergence=council_divergence,
    )
    planning_posture = _derive_planning_posture(
        planner_mode=planner_mode,
        affective_bearing=bearing,
        quiet_initiative=quiet,
    )
    risk_posture = _derive_risk_posture(
        planner_mode=planner_mode,
        wrongness_state=wrongness_state,
        council_divergence=council_divergence,
    )
    next_planning_bias = _derive_next_planning_bias(
        planner_mode=planner_mode,
        council_recommendation=council_recommendation,
        wrongness_state=wrongness_state,
        quiet_initiative=quiet,
    )
    confidence = _derive_confidence(
        planner_mode=planner_mode,
        wrongness_state=wrongness_state,
        council_divergence=council_divergence,
        loop_summary=loop_summary,
    )

    source_contributors = _source_contributors(
        embodied_state=body_state,
        strain_level=strain_level,
        affective_state=affective_state,
        affective_bearing=bearing,
        epistemic_runtime_state=epistemic,
        loop_summary=loop_summary,
        council_runtime=council,
        conflict_trace=conflict,
        quiet_initiative=quiet,
    )

    return {
        "planner_mode": planner_mode,
        "plan_horizon": plan_horizon,
        "planning_posture": planning_posture,
        "risk_posture": risk_posture,
        "next_planning_bias": next_planning_bias,
        "confidence": confidence,
        "summary": (
            f"{planner_mode} adaptive planner with {plan_horizon} horizon"
            f" and {risk_posture} risk posture"
        ),
        "source_contributors": source_contributors[:6],
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
        "boundary": "not-memory-not-identity-not-action",
        "kind": "adaptive-planner-runtime-state",
    }


def build_adaptive_planner_prompt_section(surface: dict[str, object] | None = None) -> str:
    state = surface or build_adaptive_planner_runtime_surface()
    contributors = state.get("source_contributors") or []
    contributor_text = " | ".join(
        f"{item.get('source')}: {item.get('signal')}"
        for item in contributors[:3]
        if item.get("source") and item.get("signal")
    ) or "none"
    freshness = state.get("freshness") or {}
    return "\n".join(
        [
            "Adaptive planner light (derived runtime truth, internal-only):",
            (
                f"- mode={state.get('planner_mode') or 'incremental'}"
                f" | horizon={state.get('plan_horizon') or 'near'}"
                f" | posture={state.get('planning_posture') or 'staged'}"
                f" | risk={state.get('risk_posture') or 'balanced'}"
                f" | bias={state.get('next_planning_bias') or 'stepwise-progress'}"
                f" | confidence={state.get('confidence') or 'low'}"
                f" | freshness={freshness.get('state') or 'unknown'}"
            ),
            f"- contributors={contributor_text}",
            f"- guidance={_guidance_for_planner(state)}",
        ]
    )


def _derive_planner_mode(
    *,
    embodied_state: str,
    strain_level: str,
    affective_state: str,
    wrongness_state: str,
    loop_summary: dict[str, object],
    council_recommendation: str,
    conflict_outcome: str,
    quiet_initiative: dict[str, object],
) -> str:
    if (
        embodied_state in {"strained", "degraded"}
        or strain_level == "high"
        or conflict_outcome in {"defer", "quiet_hold"}
        or (council_recommendation == "bounded-check" and wrongness_state in {"off", "strained"})
    ):
        return "hold"
    if wrongness_state in {"uneasy", "off"} or council_recommendation == "bounded-check":
        return "cautious-step"
    if affective_state == "reflective" or council_recommendation == "observe-more" or quiet_initiative.get("active"):
        return "reflective-planning"
    if council_recommendation == "carry-forward" and int(loop_summary.get("active_count") or 0) > 0:
        return "forward-push"
    if int(loop_summary.get("active_count") or 0) > 0 or int(loop_summary.get("resumed_count") or 0) > 0:
        return "forward-push"
    return "incremental"


def _derive_plan_horizon(
    *,
    planner_mode: str,
    loop_summary: dict[str, object],
    council_divergence: str,
) -> str:
    if planner_mode in {"hold", "cautious-step"}:
        return "immediate"
    if planner_mode == "reflective-planning":
        return "near"
    if planner_mode == "forward-push" and council_divergence == "low" and int(loop_summary.get("active_count") or 0) > 0:
        return "short-span"
    return "near"


def _derive_planning_posture(
    *,
    planner_mode: str,
    affective_bearing: str,
    quiet_initiative: dict[str, object],
) -> str:
    if planner_mode == "hold":
        return "held"
    if planner_mode == "cautious-step":
        return "narrow"
    if planner_mode == "reflective-planning" or affective_bearing in {"inward", "held"} or quiet_initiative.get("active"):
        return "reflective"
    if planner_mode == "forward-push":
        return "forward"
    return "staged"


def _derive_risk_posture(
    *,
    planner_mode: str,
    wrongness_state: str,
    council_divergence: str,
) -> str:
    if planner_mode == "hold" or council_divergence == "high":
        return "constrained"
    if planner_mode in {"cautious-step", "reflective-planning"} or wrongness_state in {"uneasy", "off"}:
        return "careful"
    return "balanced"


def _derive_next_planning_bias(
    *,
    planner_mode: str,
    council_recommendation: str,
    wrongness_state: str,
    quiet_initiative: dict[str, object],
) -> str:
    if planner_mode == "hold":
        return "stabilize-first"
    if planner_mode == "cautious-step" or council_recommendation == "bounded-check" or wrongness_state in {"uneasy", "off"}:
        return "verify-before-push"
    if planner_mode == "reflective-planning" or council_recommendation == "observe-more" or quiet_initiative.get("active"):
        return "observe-before-move"
    if planner_mode == "forward-push" or council_recommendation == "carry-forward":
        return "carry-forward"
    return "stepwise-progress"


def _derive_confidence(
    *,
    planner_mode: str,
    wrongness_state: str,
    council_divergence: str,
    loop_summary: dict[str, object],
) -> str:
    if planner_mode == "hold":
        return "low"
    if planner_mode == "forward-push" and wrongness_state == "clear" and council_divergence == "low":
        return "high"
    if planner_mode == "incremental" and int(loop_summary.get("standby_count") or 0) > 0 and council_divergence != "high":
        return "high"
    if planner_mode in {"cautious-step", "reflective-planning"}:
        return "medium"
    return "medium"


def _source_contributors(
    *,
    embodied_state: str,
    strain_level: str,
    affective_state: str,
    affective_bearing: str,
    epistemic_runtime_state: dict[str, object],
    loop_summary: dict[str, object],
    council_runtime: dict[str, object],
    conflict_trace: dict[str, object],
    quiet_initiative: dict[str, object],
) -> list[dict[str, str]]:
    contributors: list[dict[str, str]] = [
        {
            "source": "embodied-state",
            "signal": f"{embodied_state} / strain={strain_level}",
        },
        {
            "source": "affective-meta-state",
            "signal": f"{affective_state} / bearing={affective_bearing}",
        },
        {
            "source": "epistemic-runtime-state",
            "signal": (
                f"{str(epistemic_runtime_state.get('wrongness_state') or 'clear')}"
                f" / regret={str(epistemic_runtime_state.get('regret_signal') or 'none')}"
            ),
        },
        {
            "source": "loop-runtime",
            "signal": (
                f"{str(loop_summary.get('current_status') or 'none')}"
                f" / active={int(loop_summary.get('active_count') or 0)}"
                f" / standby={int(loop_summary.get('standby_count') or 0)}"
            ),
        },
        {
            "source": "council-runtime",
            "signal": (
                f"{str(council_runtime.get('council_state') or 'quiet')}"
                f" / recommend={str(council_runtime.get('recommendation') or 'hold')}"
                f" / divergence={str(council_runtime.get('divergence_level') or 'low')}"
            ),
        },
    ]
    if str(conflict_trace.get("outcome") or "none") != "none":
        contributors.append(
            {
                "source": "conflict-resolution",
                "signal": (
                    f"{str(conflict_trace.get('outcome') or 'none')}"
                    f" / reason={str(conflict_trace.get('reason_code') or 'none')}"
                ),
            }
        )
    if quiet_initiative.get("active"):
        contributors.append(
            {
                "source": "quiet-initiative",
                "signal": (
                    f"{str(quiet_initiative.get('state') or 'holding')}"
                    f" / hold_count={int(quiet_initiative.get('hold_count') or 0)}"
                ),
            }
        )
    return contributors


def _guidance_for_planner(state: dict[str, object]) -> str:
    mode = str(state.get("planner_mode") or "incremental")
    risk = str(state.get("risk_posture") or "balanced")
    bias = str(state.get("next_planning_bias") or "stepwise-progress")
    if mode == "hold":
        return "Hold planning to immediate stabilization; do not treat planning pressure as authorization."
    if mode == "cautious-step":
        return "Prefer one bounded next step and verification before any stronger push."
    if mode == "reflective-planning":
        return "Keep planning observant and near-horizon while reflective pressure is live."
    if mode == "forward-push":
        return "Carry planning forward in a bounded way, but stay inside runtime gates and council bounds."
    return f"Use staged planning with {risk} risk posture and {bias} bias."


def _safe_embodied_state() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.embodied_state import build_embodied_state_surface
        return build_embodied_state_surface()
    except Exception:
        return None


def _safe_affective_meta_state() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.affective_meta_state import build_affective_meta_state_surface
        return build_affective_meta_state_surface()
    except Exception:
        return None


def _safe_epistemic_runtime_state() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.epistemic_runtime_state import build_epistemic_runtime_state_surface
        return build_epistemic_runtime_state_surface()
    except Exception:
        return None


def _safe_loop_runtime() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.loop_runtime import build_loop_runtime_surface
        return build_loop_runtime_surface()
    except Exception:
        return None


def _safe_council_runtime() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.council_runtime import build_council_runtime_surface
        return build_council_runtime_surface()
    except Exception:
        return None


def _safe_conflict_trace() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.conflict_resolution import get_last_conflict_trace
        return get_last_conflict_trace()
    except Exception:
        return None


def _safe_quiet_initiative() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.conflict_resolution import get_quiet_initiative
        return get_quiet_initiative()
    except Exception:
        return None
