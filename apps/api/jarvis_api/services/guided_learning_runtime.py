from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_cached_runtime_surface,
)


def build_guided_learning_runtime_surface() -> dict[str, object]:
    return get_cached_runtime_surface(
        "guided_learning_runtime_surface",
        _build_guided_learning_runtime_surface_uncached,
    )


def _build_guided_learning_runtime_surface_uncached() -> dict[str, object]:
    return build_guided_learning_runtime_from_sources(
        adaptive_planner=_safe_adaptive_planner(),
        adaptive_reasoning=_safe_adaptive_reasoning(),
        epistemic_runtime_state=_safe_epistemic_runtime_state(),
        prompt_evolution=_safe_prompt_evolution(),
        dream_articulation=_safe_dream_articulation(),
        loop_runtime=_safe_loop_runtime(),
        council_runtime=_safe_council_runtime(),
    )


def build_guided_learning_runtime_from_sources(
    *,
    adaptive_planner: dict[str, object] | None,
    adaptive_reasoning: dict[str, object] | None,
    epistemic_runtime_state: dict[str, object] | None,
    prompt_evolution: dict[str, object] | None,
    dream_articulation: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
    council_runtime: dict[str, object] | None,
) -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()

    planner = adaptive_planner or {}
    reasoning = adaptive_reasoning or {}
    epistemic = epistemic_runtime_state or {}
    prompt_evolution_surface = prompt_evolution or {}
    dream = dream_articulation or {}
    loops = loop_runtime or {}
    council = council_runtime or {}

    prompt_summary = prompt_evolution_surface.get("summary") or {}
    dream_summary = dream.get("summary") or {}
    loop_summary = loops.get("summary") or {}

    learning_focus = _derive_learning_focus(
        planner=planner,
        reasoning=reasoning,
        epistemic=epistemic,
        prompt_summary=prompt_summary,
        dream_summary=dream_summary,
        loop_summary=loop_summary,
        council=council,
    )
    learning_mode = _derive_learning_mode(
        learning_focus=learning_focus,
        planner=planner,
        reasoning=reasoning,
        epistemic=epistemic,
        prompt_summary=prompt_summary,
        dream_summary=dream_summary,
        council=council,
    )
    learning_posture = _derive_learning_posture(
        learning_mode=learning_mode,
        council=council,
        reasoning=reasoning,
    )
    next_learning_bias = _derive_next_learning_bias(
        learning_mode=learning_mode,
        learning_focus=learning_focus,
        planner=planner,
        reasoning=reasoning,
        epistemic=epistemic,
        prompt_summary=prompt_summary,
    )
    learning_pressure = _derive_learning_pressure(
        learning_mode=learning_mode,
        planner=planner,
        epistemic=epistemic,
        council=council,
        prompt_summary=prompt_summary,
        dream_summary=dream_summary,
    )
    confidence = _derive_confidence(
        learning_mode=learning_mode,
        learning_focus=learning_focus,
        learning_pressure=learning_pressure,
        council=council,
        epistemic=epistemic,
    )

    return {
        "learning_mode": learning_mode,
        "learning_focus": learning_focus,
        "learning_posture": learning_posture,
        "next_learning_bias": next_learning_bias,
        "learning_pressure": learning_pressure,
        "confidence": confidence,
        "summary": (
            f"{learning_mode} guided learning around {learning_focus}"
            f" with {learning_posture} posture"
        ),
        "source_contributors": _source_contributors(
            adaptive_planner=planner,
            adaptive_reasoning=reasoning,
            epistemic=epistemic,
            prompt_summary=prompt_summary,
            dream_summary=dream_summary,
            loop_summary=loop_summary,
            council=council,
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
        "kind": "guided-learning-runtime-state",
    }


def build_guided_learning_prompt_section(surface: dict[str, object] | None = None) -> str:
    state = surface or build_guided_learning_runtime_surface()
    contributors = state.get("source_contributors") or []
    contributor_text = " | ".join(
        f"{item.get('source')}: {item.get('signal')}"
        for item in contributors[:3]
        if item.get("source") and item.get("signal")
    ) or "none"
    freshness = state.get("freshness") or {}
    return "\n".join(
        [
            "Guided learning light (derived runtime truth, internal-only):",
            (
                f"- mode={state.get('learning_mode') or 'reinforce'}"
                f" | focus={state.get('learning_focus') or 'reasoning'}"
                f" | posture={state.get('learning_posture') or 'gentle'}"
                f" | bias={state.get('next_learning_bias') or 'keep-current-shape'}"
                f" | pressure={state.get('learning_pressure') or 'low'}"
                f" | confidence={state.get('confidence') or 'low'}"
                f" | freshness={freshness.get('state') or 'unknown'}"
            ),
            f"- contributors={contributor_text}",
            f"- guidance={_guidance_for_learning(state)}",
        ]
    )


def _derive_learning_focus(
    *,
    planner: dict[str, object],
    reasoning: dict[str, object],
    epistemic: dict[str, object],
    prompt_summary: dict[str, object],
    dream_summary: dict[str, object],
    loop_summary: dict[str, object],
    council: dict[str, object],
) -> str:
    latest_target_asset = str(prompt_summary.get("latest_target_asset") or "none")
    wrongness_state = str(epistemic.get("wrongness_state") or "clear")
    counterfactual_mode = str(epistemic.get("counterfactual_mode") or "none")
    planner_mode = str(planner.get("planner_mode") or "incremental")
    reasoning_mode = str(reasoning.get("reasoning_mode") or "direct")
    council_recommendation = str(council.get("recommendation") or "hold")

    if latest_target_asset not in {"", "none"}:
        return "prompting"
    if wrongness_state == "strained" or council_recommendation == "bounded-check":
        return "restraint"
    if counterfactual_mode == "missed-timing" or str(loop_summary.get("current_status") or "none") == "standby":
        return "timing"
    if planner_mode in {"hold", "cautious-step", "forward-push"}:
        return "planning"
    if reasoning_mode in {"careful", "constrained", "exploratory"}:
        return "reasoning"
    if str(dream_summary.get("last_state") or "idle") in {"forming", "pressing"}:
        return "self-knowledge"
    return "reasoning"


def _derive_learning_mode(
    *,
    learning_focus: str,
    planner: dict[str, object],
    reasoning: dict[str, object],
    epistemic: dict[str, object],
    prompt_summary: dict[str, object],
    dream_summary: dict[str, object],
    council: dict[str, object],
) -> str:
    wrongness_state = str(epistemic.get("wrongness_state") or "clear")
    planner_mode = str(planner.get("planner_mode") or "incremental")
    reasoning_mode = str(reasoning.get("reasoning_mode") or "direct")
    council_recommendation = str(council.get("recommendation") or "hold")
    prompt_state = str(prompt_summary.get("last_state") or "idle")
    dream_state = str(dream_summary.get("last_state") or "idle")

    if wrongness_state == "strained" or planner_mode == "hold":
        return "stabilize"
    if wrongness_state in {"uneasy", "off"} or reasoning_mode in {"careful", "constrained"} or council_recommendation == "bounded-check":
        return "clarify"
    if reasoning_mode == "exploratory" or council_recommendation == "observe-more" or dream_state in {"forming", "pressing"}:
        return "explore"
    if prompt_state in {"forming", "pressing"} or learning_focus in {"planning", "prompting", "timing"}:
        return "practice"
    return "reinforce"


def _derive_learning_posture(
    *,
    learning_mode: str,
    council: dict[str, object],
    reasoning: dict[str, object],
) -> str:
    if learning_mode == "stabilize":
        return "watchful"
    if learning_mode in {"practice", "explore"}:
        return "active"
    if str(council.get("divergence_level") or "low") == "high" or str(reasoning.get("reasoning_posture") or "balanced") == "guarded":
        return "watchful"
    return "gentle"


def _derive_next_learning_bias(
    *,
    learning_mode: str,
    learning_focus: str,
    planner: dict[str, object],
    reasoning: dict[str, object],
    epistemic: dict[str, object],
    prompt_summary: dict[str, object],
) -> str:
    if learning_mode == "stabilize":
        return "tighten-bounds"
    if learning_focus == "restraint":
        return "exercise-restraint"
    if learning_focus == "timing":
        return "check-timing"
    if learning_focus == "prompting" and str(prompt_summary.get("latest_target_asset") or "none") != "none":
        return "rehearse-framing"
    if learning_focus == "planning" and str(planner.get("planner_mode") or "incremental") != "incremental":
        return "rehearse-next-step"
    if learning_focus == "reasoning" and str(reasoning.get("certainty_style") or "crisp") != "crisp":
        return "tighten-claims"
    if str(epistemic.get("counterfactual_mode") or "none") != "none":
        return "compare-alternatives"
    return "keep-current-shape"


def _derive_learning_pressure(
    *,
    learning_mode: str,
    planner: dict[str, object],
    epistemic: dict[str, object],
    council: dict[str, object],
    prompt_summary: dict[str, object],
    dream_summary: dict[str, object],
) -> str:
    if (
        learning_mode == "stabilize"
        or str(planner.get("planner_mode") or "incremental") == "hold"
        or str(epistemic.get("wrongness_state") or "clear") == "strained"
        or str(council.get("recommendation") or "hold") == "bounded-check"
        or str(prompt_summary.get("last_state") or "idle") == "pressing"
        or str(dream_summary.get("last_state") or "idle") == "pressing"
    ):
        return "high"
    if learning_mode in {"clarify", "practice", "explore"}:
        return "medium"
    return "low"


def _derive_confidence(
    *,
    learning_mode: str,
    learning_focus: str,
    learning_pressure: str,
    council: dict[str, object],
    epistemic: dict[str, object],
) -> str:
    if learning_mode == "stabilize":
        return "low"
    if learning_pressure == "high" or str(council.get("divergence_level") or "low") == "high":
        return "low"
    if learning_mode == "reinforce" and str(epistemic.get("wrongness_state") or "clear") == "clear":
        return "high"
    if learning_focus in {"planning", "prompting"} and learning_pressure == "medium":
        return "medium"
    return "medium"


def _source_contributors(
    *,
    adaptive_planner: dict[str, object],
    adaptive_reasoning: dict[str, object],
    epistemic: dict[str, object],
    prompt_summary: dict[str, object],
    dream_summary: dict[str, object],
    loop_summary: dict[str, object],
    council: dict[str, object],
) -> list[dict[str, str]]:
    contributors = [
        {
            "source": "adaptive-planner",
            "signal": (
                f"{str(adaptive_planner.get('planner_mode') or 'incremental')}"
                f" / horizon={str(adaptive_planner.get('plan_horizon') or 'near')}"
                f" / risk={str(adaptive_planner.get('risk_posture') or 'balanced')}"
            ),
        },
        {
            "source": "adaptive-reasoning",
            "signal": (
                f"{str(adaptive_reasoning.get('reasoning_mode') or 'direct')}"
                f" / posture={str(adaptive_reasoning.get('reasoning_posture') or 'balanced')}"
                f" / certainty={str(adaptive_reasoning.get('certainty_style') or 'crisp')}"
            ),
        },
        {
            "source": "epistemic-runtime-state",
            "signal": (
                f"{str(epistemic.get('wrongness_state') or 'clear')}"
                f" / regret={str(epistemic.get('regret_signal') or 'none')}"
                f" / counterfactual={str(epistemic.get('counterfactual_mode') or 'none')}"
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
                f"{str(council.get('council_state') or 'quiet')}"
                f" / recommend={str(council.get('recommendation') or 'hold')}"
                f" / divergence={str(council.get('divergence_level') or 'low')}"
            ),
        },
    ]
    if str(prompt_summary.get("last_state") or "idle") != "idle" or str(prompt_summary.get("latest_target_asset") or "none") != "none":
        contributors.append(
            {
                "source": "prompt-evolution",
                "signal": (
                    f"{str(prompt_summary.get('last_state') or 'idle')}"
                    f" / target={str(prompt_summary.get('latest_target_asset') or 'none')}"
                ),
            }
        )
    if str(dream_summary.get("last_state") or "idle") != "idle":
        contributors.append(
            {
                "source": "dream-articulation",
                "signal": (
                    f"{str(dream_summary.get('last_state') or 'idle')}"
                    f" / reason={str(dream_summary.get('last_reason') or 'no-run-yet')}"
                ),
            }
        )
    return contributors


def _guidance_for_learning(state: dict[str, object]) -> str:
    mode = str(state.get("learning_mode") or "reinforce")
    focus = str(state.get("learning_focus") or "reasoning")
    bias = str(state.get("next_learning_bias") or "keep-current-shape")
    if mode == "stabilize":
        return "Treat learning as bounded stabilization; do not turn learning pressure into action authority."
    if mode == "clarify":
        return f"Use learning to clarify {focus} in small bounded ways before stronger pushes."
    if mode == "explore":
        return f"Let learning explore {focus} carefully without overclaiming progress."
    if mode == "practice":
        return f"Use bounded rehearsal around {focus} with bias={bias}, not autonomous execution."
    return f"Reinforce what is already working around {focus} while keeping bias={bias} bounded."


def _safe_adaptive_planner() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.adaptive_planner_runtime import build_adaptive_planner_runtime_surface
        return build_adaptive_planner_runtime_surface()
    except Exception:
        return None


def _safe_adaptive_reasoning() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.adaptive_reasoning_runtime import build_adaptive_reasoning_runtime_surface
        return build_adaptive_reasoning_runtime_surface()
    except Exception:
        return None


def _safe_epistemic_runtime_state() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.epistemic_runtime_state import build_epistemic_runtime_state_surface
        return build_epistemic_runtime_state_surface()
    except Exception:
        return None


def _safe_prompt_evolution() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.prompt_evolution_runtime import build_prompt_evolution_runtime_surface
        return build_prompt_evolution_runtime_surface()
    except Exception:
        return None


def _safe_dream_articulation() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.dream_articulation import build_dream_articulation_surface
        return build_dream_articulation_surface()
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
