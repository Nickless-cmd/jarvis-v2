from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_timed_runtime_surface,
)


def build_adaptive_reasoning_runtime_surface() -> dict[str, object]:
    return get_timed_runtime_surface(
        "adaptive_reasoning_runtime_surface",
        30.0,
        _build_adaptive_reasoning_runtime_surface_uncached,
    )


def _build_adaptive_reasoning_runtime_surface_uncached() -> dict[str, object]:
    return build_adaptive_reasoning_runtime_from_sources(
        embodied_state=_safe_embodied_state(),
        affective_meta_state=_safe_affective_meta_state(),
        epistemic_runtime_state=_safe_epistemic_runtime_state(),
        loop_runtime=_safe_loop_runtime(),
        council_runtime=_safe_council_runtime(),
        adaptive_planner=_safe_adaptive_planner(),
        conflict_trace=_safe_conflict_trace(),
        quiet_initiative=_safe_quiet_initiative(),
    )


def build_adaptive_reasoning_runtime_from_sources(
    *,
    embodied_state: dict[str, object] | None,
    affective_meta_state: dict[str, object] | None,
    epistemic_runtime_state: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
    council_runtime: dict[str, object] | None,
    adaptive_planner: dict[str, object] | None,
    conflict_trace: dict[str, object] | None,
    quiet_initiative: dict[str, object] | None,
) -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()

    embodied = embodied_state or {}
    affective = affective_meta_state or {}
    epistemic = epistemic_runtime_state or {}
    loops = loop_runtime or {}
    council = council_runtime or {}
    planner = adaptive_planner or {}
    conflict = conflict_trace or {}
    quiet = quiet_initiative or {}

    loop_summary = loops.get("summary") or {}
    body_state = str(embodied.get("state") or "steady")
    strain_level = str(embodied.get("strain_level") or "low")
    affective_state = str(affective.get("state") or "settled")
    affective_bearing = str(affective.get("bearing") or "even")
    wrongness_state = str(epistemic.get("wrongness_state") or "clear")
    regret_signal = str(epistemic.get("regret_signal") or "none")
    counterfactual_mode = str(epistemic.get("counterfactual_mode") or "none")
    council_recommendation = str(council.get("recommendation") or "hold")
    council_divergence = str(council.get("divergence_level") or "low")
    planner_mode = str(planner.get("planner_mode") or "incremental")
    conflict_outcome = str(conflict.get("outcome") or "none")

    reasoning_mode = _derive_reasoning_mode(
        embodied_state=body_state,
        strain_level=strain_level,
        affective_state=affective_state,
        wrongness_state=wrongness_state,
        council_recommendation=council_recommendation,
        planner_mode=planner_mode,
        conflict_outcome=conflict_outcome,
        quiet_initiative=quiet,
    )
    reasoning_posture = _derive_reasoning_posture(
        reasoning_mode=reasoning_mode,
        affective_bearing=affective_bearing,
        council_divergence=council_divergence,
    )
    certainty_style = _derive_certainty_style(
        reasoning_mode=reasoning_mode,
        wrongness_state=wrongness_state,
        regret_signal=regret_signal,
        council_divergence=council_divergence,
    )
    exploration_bias = _derive_exploration_bias(
        reasoning_mode=reasoning_mode,
        counterfactual_mode=counterfactual_mode,
        planner_mode=planner_mode,
        quiet_initiative=quiet,
    )
    constraint_bias = _derive_constraint_bias(
        reasoning_mode=reasoning_mode,
        council_recommendation=council_recommendation,
        planner_mode=planner_mode,
        conflict_outcome=conflict_outcome,
    )
    confidence = _derive_confidence(
        reasoning_mode=reasoning_mode,
        wrongness_state=wrongness_state,
        council_divergence=council_divergence,
        loop_summary=loop_summary,
        planner_mode=planner_mode,
    )

    return {
        "reasoning_mode": reasoning_mode,
        "reasoning_posture": reasoning_posture,
        "certainty_style": certainty_style,
        "exploration_bias": exploration_bias,
        "constraint_bias": constraint_bias,
        "confidence": confidence,
        "summary": (
            f"{reasoning_mode} adaptive reasoning with {certainty_style} certainty"
            f" and {constraint_bias} constraint bias"
        ),
        "source_contributors": _source_contributors(
            embodied_state=body_state,
            strain_level=strain_level,
            affective_state=affective_state,
            affective_bearing=affective_bearing,
            wrongness_state=wrongness_state,
            regret_signal=regret_signal,
            counterfactual_mode=counterfactual_mode,
            loop_summary=loop_summary,
            council_runtime=council,
            planner=planner,
            conflict_trace=conflict,
            quiet_initiative=quiet,
        )[:7],
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
        "kind": "adaptive-reasoning-runtime-state",
    }


def build_adaptive_reasoning_prompt_section(surface: dict[str, object] | None = None) -> str:
    state = surface or build_adaptive_reasoning_runtime_surface()
    contributors = state.get("source_contributors") or []
    contributor_text = " | ".join(
        f"{item.get('source')}: {item.get('signal')}"
        for item in contributors[:3]
        if item.get("source") and item.get("signal")
    ) or "none"
    freshness = state.get("freshness") or {}
    return "\n".join(
        [
            "Adaptive reasoning light (derived runtime truth, internal-only):",
            (
                f"- mode={state.get('reasoning_mode') or 'direct'}"
                f" | posture={state.get('reasoning_posture') or 'balanced'}"
                f" | certainty={state.get('certainty_style') or 'crisp'}"
                f" | exploration={state.get('exploration_bias') or 'limited'}"
                f" | constraint={state.get('constraint_bias') or 'light'}"
                f" | confidence={state.get('confidence') or 'low'}"
                f" | freshness={freshness.get('state') or 'unknown'}"
            ),
            f"- contributors={contributor_text}",
            f"- guidance={_guidance_for_reasoning(state)}",
        ]
    )


def _derive_reasoning_mode(
    *,
    embodied_state: str,
    strain_level: str,
    affective_state: str,
    wrongness_state: str,
    council_recommendation: str,
    planner_mode: str,
    conflict_outcome: str,
    quiet_initiative: dict[str, object],
) -> str:
    if (
        embodied_state in {"strained", "degraded"}
        or strain_level == "high"
        or planner_mode == "hold"
        or conflict_outcome in {"defer", "quiet_hold"}
    ):
        return "constrained"
    # "off" = neutral default, only "uneasy" = actual concern
    if wrongness_state == "uneasy" or planner_mode == "cautious-step":
        return "careful"
    if affective_state == "reflective" or planner_mode == "reflective-planning" or quiet_initiative.get("active"):
        return "reflective"
    if council_recommendation == "observe-more":
        return "exploratory"
    return "direct"


def _derive_reasoning_posture(
    *,
    reasoning_mode: str,
    affective_bearing: str,
    council_divergence: str,
) -> str:
    if reasoning_mode == "constrained":
        return "guarded"
    if reasoning_mode == "careful":
        return "narrow"
    if reasoning_mode == "reflective":
        return "open"
    if council_divergence == "high" or affective_bearing in {"taut", "compressed"}:
        return "guarded"
    return "balanced"


def _derive_certainty_style(
    *,
    reasoning_mode: str,
    wrongness_state: str,
    regret_signal: str,
    council_divergence: str,
) -> str:
    if reasoning_mode in {"constrained", "careful"} or wrongness_state == "uneasy" or regret_signal != "none":
        return "cautious"
    if reasoning_mode in {"reflective", "exploratory"} or council_divergence != "low":
        return "tentative"
    return "crisp"


def _derive_exploration_bias(
    *,
    reasoning_mode: str,
    counterfactual_mode: str,
    planner_mode: str,
    quiet_initiative: dict[str, object],
) -> str:
    if reasoning_mode == "constrained":
        return "minimal"
    if reasoning_mode == "reflective" or quiet_initiative.get("active"):
        return "inner-scan"
    if reasoning_mode == "exploratory" or counterfactual_mode != "none" or planner_mode == "reflective-planning":
        return "alternative-seeking"
    return "limited"


def _derive_constraint_bias(
    *,
    reasoning_mode: str,
    council_recommendation: str,
    planner_mode: str,
    conflict_outcome: str,
) -> str:
    if reasoning_mode == "constrained" or planner_mode == "hold" or conflict_outcome in {"defer", "quiet_hold"}:
        return "strong"
    if council_recommendation in {"bounded-check", "hold"} or planner_mode == "cautious-step":
        return "moderate"
    return "light"


def _derive_confidence(
    *,
    reasoning_mode: str,
    wrongness_state: str,
    council_divergence: str,
    loop_summary: dict[str, object],
    planner_mode: str,
) -> str:
    if reasoning_mode == "constrained":
        return "low"
    if reasoning_mode == "direct" and wrongness_state == "clear" and council_divergence == "low":
        return "high"
    if planner_mode == "forward-push" and int(loop_summary.get("active_count") or 0) > 0:
        return "high"
    return "medium"


def _source_contributors(
    *,
    embodied_state: str,
    strain_level: str,
    affective_state: str,
    affective_bearing: str,
    wrongness_state: str,
    regret_signal: str,
    counterfactual_mode: str,
    loop_summary: dict[str, object],
    council_runtime: dict[str, object],
    planner: dict[str, object],
    conflict_trace: dict[str, object],
    quiet_initiative: dict[str, object],
) -> list[dict[str, str]]:
    contributors: list[dict[str, str]] = [
        {"source": "embodied-state", "signal": f"{embodied_state} / strain={strain_level}"},
        {"source": "affective-meta-state", "signal": f"{affective_state} / bearing={affective_bearing}"},
        {
            "source": "epistemic-runtime-state",
            "signal": f"{wrongness_state} / regret={regret_signal} / counterfactual={counterfactual_mode}",
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
        {
            "source": "adaptive-planner",
            "signal": (
                f"{str(planner.get('planner_mode') or 'incremental')}"
                f" / posture={str(planner.get('planning_posture') or 'staged')}"
                f" / risk={str(planner.get('risk_posture') or 'balanced')}"
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


def _guidance_for_reasoning(state: dict[str, object]) -> str:
    mode = str(state.get("reasoning_mode") or "direct")
    certainty = str(state.get("certainty_style") or "crisp")
    constraint = str(state.get("constraint_bias") or "light")
    if mode == "constrained":
        return "Keep reasoning narrow and bounded; do not turn pressure into authorization."
    if mode == "careful":
        return "Favor careful claims and bounded checks before stronger inference."
    if mode == "reflective":
        return "Let reasoning stay inward and exploratory without overstating certainty."
    if mode == "exploratory":
        return "Open alternatives carefully, but keep conclusions tentative and bounded."
    return f"Reason directly with {certainty} certainty style under {constraint} constraint bias."


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


def _safe_adaptive_planner() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.adaptive_planner_runtime import build_adaptive_planner_runtime_surface
        return build_adaptive_planner_runtime_surface()
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
