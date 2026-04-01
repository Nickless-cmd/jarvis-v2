from __future__ import annotations

from datetime import UTC, datetime


def build_adaptive_learning_runtime_surface() -> dict[str, object]:
    return build_adaptive_learning_runtime_from_sources(
        guided_learning=_safe_guided_learning(),
        adaptive_planner=_safe_adaptive_planner(),
        adaptive_reasoning=_safe_adaptive_reasoning(),
        epistemic_runtime_state=_safe_epistemic_runtime_state(),
        prompt_evolution=_safe_prompt_evolution(),
        dream_articulation=_safe_dream_articulation(),
        idle_consolidation=_safe_idle_consolidation(),
        loop_runtime=_safe_loop_runtime(),
    )


def build_adaptive_learning_runtime_from_sources(
    *,
    guided_learning: dict[str, object] | None,
    adaptive_planner: dict[str, object] | None,
    adaptive_reasoning: dict[str, object] | None,
    epistemic_runtime_state: dict[str, object] | None,
    prompt_evolution: dict[str, object] | None,
    dream_articulation: dict[str, object] | None,
    idle_consolidation: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
) -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()

    guided = guided_learning or {}
    planner = adaptive_planner or {}
    reasoning = adaptive_reasoning or {}
    epistemic = epistemic_runtime_state or {}
    prompt_evolution_surface = prompt_evolution or {}
    dream = dream_articulation or {}
    consolidation = idle_consolidation or {}
    loops = loop_runtime or {}

    prompt_summary = prompt_evolution_surface.get("summary") or {}
    dream_summary = dream.get("summary") or {}
    consolidation_summary = consolidation.get("summary") or {}
    loop_summary = loops.get("summary") or {}

    reinforcement_target = _derive_reinforcement_target(
        guided_learning=guided,
        prompt_summary=prompt_summary,
        dream_summary=dream_summary,
        consolidation_summary=consolidation_summary,
        loop_summary=loop_summary,
    )
    learning_engine_mode = _derive_learning_engine_mode(
        guided_learning=guided,
        planner=planner,
        reasoning=reasoning,
        epistemic=epistemic,
        prompt_summary=prompt_summary,
        dream_summary=dream_summary,
        consolidation_summary=consolidation_summary,
    )
    retention_bias = _derive_retention_bias(
        learning_engine_mode=learning_engine_mode,
        guided_learning=guided,
        prompt_summary=prompt_summary,
        loop_summary=loop_summary,
    )
    attenuation_bias = _derive_attenuation_bias(
        learning_engine_mode=learning_engine_mode,
        epistemic=epistemic,
        guided_learning=guided,
        consolidation_summary=consolidation_summary,
    )
    maturation_state = _derive_maturation_state(
        learning_engine_mode=learning_engine_mode,
        dream_summary=dream_summary,
        prompt_summary=prompt_summary,
        consolidation_summary=consolidation_summary,
        loop_summary=loop_summary,
    )
    confidence = _derive_confidence(
        learning_engine_mode=learning_engine_mode,
        guided_learning=guided,
        epistemic=epistemic,
        maturation_state=maturation_state,
    )

    return {
        "learning_engine_mode": learning_engine_mode,
        "reinforcement_target": reinforcement_target,
        "retention_bias": retention_bias,
        "attenuation_bias": attenuation_bias,
        "maturation_state": maturation_state,
        "confidence": confidence,
        "summary": (
            f"{learning_engine_mode} adaptive learning around {reinforcement_target}"
            f" with {maturation_state} maturation"
        ),
        "source_contributors": _source_contributors(
            guided_learning=guided,
            adaptive_planner=planner,
            adaptive_reasoning=reasoning,
            epistemic=epistemic,
            prompt_summary=prompt_summary,
            dream_summary=dream_summary,
            consolidation_summary=consolidation_summary,
            loop_summary=loop_summary,
        )[:8],
        "freshness": {
            "built_at": built_at,
            "state": "fresh",
        },
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
            "guided_learning_enrichment": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "boundary": "not-memory-not-identity-not-action",
        "kind": "adaptive-learning-runtime-state",
    }


def build_adaptive_learning_prompt_section(surface: dict[str, object] | None = None) -> str:
    state = surface or build_adaptive_learning_runtime_surface()
    contributors = state.get("source_contributors") or []
    contributor_text = " | ".join(
        f"{item.get('source')}: {item.get('signal')}"
        for item in contributors[:3]
        if item.get("source") and item.get("signal")
    ) or "none"
    freshness = state.get("freshness") or {}
    return "\n".join(
        [
            "Adaptive learning engine light (derived runtime truth, internal-only):",
            (
                f"- mode={state.get('learning_engine_mode') or 'reinforce'}"
                f" | target={state.get('reinforcement_target') or 'reasoning'}"
                f" | retention={state.get('retention_bias') or 'light'}"
                f" | attenuation={state.get('attenuation_bias') or 'none'}"
                f" | maturation={state.get('maturation_state') or 'early'}"
                f" | confidence={state.get('confidence') or 'low'}"
                f" | freshness={freshness.get('state') or 'unknown'}"
            ),
            f"- contributors={contributor_text}",
            f"- guidance={_guidance_for_adaptive_learning(state)}",
        ]
    )


def _derive_reinforcement_target(
    *,
    guided_learning: dict[str, object],
    prompt_summary: dict[str, object],
    dream_summary: dict[str, object],
    consolidation_summary: dict[str, object],
    loop_summary: dict[str, object],
) -> str:
    guided_focus = str(guided_learning.get("learning_focus") or "reasoning")
    target_asset = str(prompt_summary.get("latest_target_asset") or "none")
    prompt_state = str(prompt_summary.get("last_state") or "idle")
    dream_state = str(dream_summary.get("last_state") or "idle")
    consolidation_state = str(consolidation_summary.get("last_state") or "idle")
    loop_status = str(loop_summary.get("current_status") or "none")

    if target_asset not in {"", "none"} or prompt_state in {"forming", "pressing"}:
        return "prompt-shape"
    if dream_state in {"forming", "pressing"} or consolidation_state in {"settling", "holding"}:
        return "inner-synthesis"
    if guided_focus in {"timing", "restraint"} or loop_status == "standby":
        return guided_focus
    if guided_focus in {"planning", "reasoning", "self-knowledge", "prompting"}:
        return guided_focus
    return "reasoning"


def _derive_learning_engine_mode(
    *,
    guided_learning: dict[str, object],
    planner: dict[str, object],
    reasoning: dict[str, object],
    epistemic: dict[str, object],
    prompt_summary: dict[str, object],
    dream_summary: dict[str, object],
    consolidation_summary: dict[str, object],
) -> str:
    learning_mode = str(guided_learning.get("learning_mode") or "reinforce")
    wrongness_state = str(epistemic.get("wrongness_state") or "clear")
    planner_mode = str(planner.get("planner_mode") or "incremental")
    reasoning_mode = str(reasoning.get("reasoning_mode") or "direct")
    prompt_state = str(prompt_summary.get("last_state") or "idle")
    dream_state = str(dream_summary.get("last_state") or "idle")
    consolidation_state = str(consolidation_summary.get("last_state") or "idle")

    if wrongness_state == "strained" or learning_mode == "stabilize":
        return "rebalance"
    if consolidation_state in {"settling", "holding"}:
        return "consolidate"
    if learning_mode == "clarify" or reasoning_mode in {"careful", "constrained"}:
        return "retain"
    if prompt_state == "pressing" or dream_state == "pressing" or planner_mode == "forward-push":
        return "reinforce"
    if learning_mode == "explore":
        return "attenuate"
    return "retain"


def _derive_retention_bias(
    *,
    learning_engine_mode: str,
    guided_learning: dict[str, object],
    prompt_summary: dict[str, object],
    loop_summary: dict[str, object],
) -> str:
    if learning_engine_mode == "reinforce":
        return "warm"
    if learning_engine_mode in {"retain", "consolidate"}:
        return "hold"
    if str(guided_learning.get("learning_pressure") or "low") == "high" or int(loop_summary.get("active_count") or 0) > 0:
        return "warm"
    if str(prompt_summary.get("last_state") or "idle") == "forming":
        return "warm"
    return "light"


def _derive_attenuation_bias(
    *,
    learning_engine_mode: str,
    epistemic: dict[str, object],
    guided_learning: dict[str, object],
    consolidation_summary: dict[str, object],
) -> str:
    wrongness_state = str(epistemic.get("wrongness_state") or "clear")
    learning_mode = str(guided_learning.get("learning_mode") or "reinforce")
    consolidation_reason = str(consolidation_summary.get("last_reason") or "no-run-yet")

    if learning_engine_mode == "attenuate":
        return "release"
    if learning_engine_mode == "rebalance" or wrongness_state in {"off", "strained"}:
        return "soften"
    if learning_mode == "explore" and consolidation_reason != "no-run-yet":
        return "soften"
    return "none"


def _derive_maturation_state(
    *,
    learning_engine_mode: str,
    dream_summary: dict[str, object],
    prompt_summary: dict[str, object],
    consolidation_summary: dict[str, object],
    loop_summary: dict[str, object],
) -> str:
    if learning_engine_mode == "consolidate" or str(consolidation_summary.get("last_state") or "idle") in {"settling", "holding"}:
        return "stabilizing"
    if (
        str(dream_summary.get("last_state") or "idle") in {"forming", "pressing"}
        or str(prompt_summary.get("last_state") or "idle") in {"forming", "pressing"}
        or int(loop_summary.get("standby_count") or 0) > 0
    ):
        return "forming"
    return "early"


def _derive_confidence(
    *,
    learning_engine_mode: str,
    guided_learning: dict[str, object],
    epistemic: dict[str, object],
    maturation_state: str,
) -> str:
    if learning_engine_mode == "rebalance":
        return "low"
    if maturation_state == "stabilizing" and str(epistemic.get("wrongness_state") or "clear") == "clear":
        return "high"
    if str(guided_learning.get("learning_pressure") or "low") == "medium":
        return "medium"
    return "medium"


def _source_contributors(
    *,
    guided_learning: dict[str, object],
    adaptive_planner: dict[str, object],
    adaptive_reasoning: dict[str, object],
    epistemic: dict[str, object],
    prompt_summary: dict[str, object],
    dream_summary: dict[str, object],
    consolidation_summary: dict[str, object],
    loop_summary: dict[str, object],
) -> list[dict[str, str]]:
    contributors = [
        {
            "source": "guided-learning",
            "signal": (
                f"{str(guided_learning.get('learning_mode') or 'reinforce')}"
                f" / focus={str(guided_learning.get('learning_focus') or 'reasoning')}"
                f" / pressure={str(guided_learning.get('learning_pressure') or 'low')}"
            ),
        },
        {
            "source": "adaptive-planner",
            "signal": (
                f"{str(adaptive_planner.get('planner_mode') or 'incremental')}"
                f" / risk={str(adaptive_planner.get('risk_posture') or 'balanced')}"
            ),
        },
        {
            "source": "adaptive-reasoning",
            "signal": (
                f"{str(adaptive_reasoning.get('reasoning_mode') or 'direct')}"
                f" / certainty={str(adaptive_reasoning.get('certainty_style') or 'crisp')}"
            ),
        },
        {
            "source": "epistemic-runtime-state",
            "signal": (
                f"{str(epistemic.get('wrongness_state') or 'clear')}"
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
    ]
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
    if str(consolidation_summary.get("last_state") or "idle") != "idle":
        contributors.append(
            {
                "source": "idle-consolidation",
                "signal": (
                    f"{str(consolidation_summary.get('last_state') or 'idle')}"
                    f" / reason={str(consolidation_summary.get('last_reason') or 'no-run-yet')}"
                ),
            }
        )
    return contributors


def _guidance_for_adaptive_learning(state: dict[str, object]) -> str:
    mode = str(state.get("learning_engine_mode") or "retain")
    target = str(state.get("reinforcement_target") or "reasoning")
    retention = str(state.get("retention_bias") or "light")
    attenuation = str(state.get("attenuation_bias") or "none")
    if mode == "rebalance":
        return "Rebalance learning gently; do not let correction pressure become authorization."
    if mode == "consolidate":
        return f"Use bounded consolidation to stabilize {target} while retention={retention}."
    if mode == "reinforce":
        return f"Keep {target} warm and bounded with retention={retention}, not autonomous rehearsal."
    if mode == "attenuate":
        return f"Soften and release stale learning pressure around {target} with attenuation={attenuation}."
    return f"Retain {target} lightly with retention={retention} and attenuation={attenuation}."


def _safe_guided_learning() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.guided_learning_runtime import build_guided_learning_runtime_surface
        return build_guided_learning_runtime_surface()
    except Exception:
        return None


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


def _safe_idle_consolidation() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.idle_consolidation import build_idle_consolidation_surface
        return build_idle_consolidation_surface()
    except Exception:
        return None


def _safe_loop_runtime() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.loop_runtime import build_loop_runtime_surface
        return build_loop_runtime_surface()
    except Exception:
        return None
