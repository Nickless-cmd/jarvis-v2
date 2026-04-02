from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_timed_runtime_surface,
)


def build_dream_influence_runtime_surface() -> dict[str, object]:
    return get_timed_runtime_surface(
        "dream_influence_runtime_surface",
        30.0,
        _build_dream_influence_runtime_surface_uncached,
    )


def _build_dream_influence_runtime_surface_uncached() -> dict[str, object]:
    return build_dream_influence_runtime_from_sources(
        dream_articulation=_safe_dream_articulation(),
        guided_learning=_safe_guided_learning(),
        adaptive_learning=_safe_adaptive_learning(),
        adaptive_reasoning=_safe_adaptive_reasoning(),
        affective_meta_state=_safe_affective_meta_state(),
        epistemic_runtime_state=_safe_epistemic_runtime_state(),
        prompt_evolution=_safe_prompt_evolution(),
    )


def build_dream_influence_runtime_from_sources(
    *,
    dream_articulation: dict[str, object] | None,
    guided_learning: dict[str, object] | None,
    adaptive_learning: dict[str, object] | None,
    adaptive_reasoning: dict[str, object] | None,
    affective_meta_state: dict[str, object] | None,
    epistemic_runtime_state: dict[str, object] | None,
    prompt_evolution: dict[str, object] | None,
) -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()

    dream = dream_articulation or {}
    guided = guided_learning or {}
    adaptive_learning_surface = adaptive_learning or {}
    reasoning = adaptive_reasoning or {}
    affective = affective_meta_state or {}
    epistemic = epistemic_runtime_state or {}
    prompt_evolution_surface = prompt_evolution or {}

    dream_summary = dream.get("summary") or {}
    dream_artifact = dream.get("latest_artifact") or {}
    prompt_summary = prompt_evolution_surface.get("summary") or {}

    influence_state = _derive_influence_state(
        dream_summary=dream_summary,
        guided_learning=guided,
        adaptive_learning=adaptive_learning_surface,
        epistemic=epistemic,
    )
    influence_target = _derive_influence_target(
        influence_state=influence_state,
        dream_summary=dream_summary,
        guided_learning=guided,
        adaptive_learning=adaptive_learning_surface,
        prompt_summary=prompt_summary,
        affective=affective,
    )
    influence_mode = _derive_influence_mode(
        influence_target=influence_target,
        dream_summary=dream_summary,
        guided_learning=guided,
        adaptive_learning=adaptive_learning_surface,
        reasoning=reasoning,
        affective=affective,
        epistemic=epistemic,
    )
    influence_strength = _derive_influence_strength(
        influence_state=influence_state,
        dream_summary=dream_summary,
        adaptive_learning=adaptive_learning_surface,
        prompt_summary=prompt_summary,
        epistemic=epistemic,
    )
    influence_hint = _derive_influence_hint(
        influence_state=influence_state,
        influence_target=influence_target,
        influence_mode=influence_mode,
        guided_learning=guided,
        adaptive_learning=adaptive_learning_surface,
        prompt_summary=prompt_summary,
        dream_artifact=dream_artifact,
    )
    confidence = _derive_confidence(
        influence_state=influence_state,
        influence_strength=influence_strength,
        epistemic=epistemic,
        prompt_summary=prompt_summary,
    )

    return {
        "influence_state": influence_state,
        "influence_target": influence_target,
        "influence_mode": influence_mode,
        "influence_strength": influence_strength,
        "influence_hint": influence_hint,
        "confidence": confidence,
        "summary": (
            f"dream influence {influence_state} toward {influence_target}"
            f" via {influence_mode} ({influence_strength})"
        ),
        "source_contributors": _source_contributors(
            dream_summary=dream_summary,
            dream_artifact=dream_artifact,
            guided_learning=guided,
            adaptive_learning=adaptive_learning_surface,
            reasoning=reasoning,
            affective=affective,
            epistemic=epistemic,
            prompt_summary=prompt_summary,
        )[:7],
        "freshness": {
            "built_at": built_at,
            "state": "fresh",
        },
        "seam_usage": {
            "guided_learning_enrichment": True,
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "boundary": "not-memory-not-identity-not-action",
        "kind": "dream-influence-runtime-state",
    }


def build_dream_influence_prompt_section(surface: dict[str, object] | None = None) -> str:
    state = surface or build_dream_influence_runtime_surface()
    contributors = state.get("source_contributors") or []
    contributor_text = " | ".join(
        f"{item.get('source')}: {item.get('signal')}"
        for item in contributors[:3]
        if item.get("source") and item.get("signal")
    ) or "none"
    freshness = state.get("freshness") or {}
    return "\n".join(
        [
            "Dream influence light (derived runtime truth, internal-only):",
            (
                f"- state={state.get('influence_state') or 'quiet'}"
                f" | target={state.get('influence_target') or 'none'}"
                f" | mode={state.get('influence_mode') or 'stabilize'}"
                f" | strength={state.get('influence_strength') or 'none'}"
                f" | confidence={state.get('confidence') or 'low'}"
                f" | freshness={freshness.get('state') or 'unknown'}"
            ),
            f"- hint={state.get('influence_hint') or 'none'}",
            f"- contributors={contributor_text}",
        ]
    )


def _derive_influence_state(
    *,
    dream_summary: dict[str, object],
    guided_learning: dict[str, object],
    adaptive_learning: dict[str, object],
    epistemic: dict[str, object],
) -> str:
    dream_state = str(dream_summary.get("last_state") or "idle")
    learning_mode = str(guided_learning.get("learning_mode") or "reinforce")
    engine_mode = str(adaptive_learning.get("learning_engine_mode") or "retain")
    wrongness = str(epistemic.get("wrongness_state") or "clear")

    if dream_state == "pressing" and wrongness not in {"off", "strained"}:
        return "active"
    if dream_state in {"forming", "tentative", "pressing"}:
        return "present"
    if learning_mode == "explore" and engine_mode in {"reinforce", "consolidate"}:
        return "present"
    return "quiet"


def _derive_influence_target(
    *,
    influence_state: str,
    dream_summary: dict[str, object],
    guided_learning: dict[str, object],
    adaptive_learning: dict[str, object],
    prompt_summary: dict[str, object],
    affective: dict[str, object],
) -> str:
    if influence_state == "quiet":
        return "none"

    target_asset = str(prompt_summary.get("latest_target_asset") or "none")
    if target_asset not in {"", "none"}:
        return "prompting"
    if str(guided_learning.get("learning_focus") or "reasoning") == "self-knowledge":
        return "learning"
    if str(adaptive_learning.get("reinforcement_target") or "reasoning") == "inner-synthesis":
        return "learning"
    if str(affective.get("state") or "settled") == "reflective":
        return "affective-bearing"
    if str(dream_summary.get("last_state") or "idle") == "pressing":
        return "reasoning"
    return "learning"


def _derive_influence_mode(
    *,
    influence_target: str,
    dream_summary: dict[str, object],
    guided_learning: dict[str, object],
    adaptive_learning: dict[str, object],
    reasoning: dict[str, object],
    affective: dict[str, object],
    epistemic: dict[str, object],
) -> str:
    if influence_target == "none":
        return "stabilize"
    if influence_target == "prompting":
        return "reinforce"
    if str(epistemic.get("wrongness_state") or "clear") in {"off", "strained"}:
        return "soften"
    if str(guided_learning.get("learning_mode") or "reinforce") == "explore":
        return "explore"
    if str(adaptive_learning.get("learning_engine_mode") or "retain") == "consolidate":
        return "stabilize"
    if str(reasoning.get("reasoning_mode") or "direct") == "careful":
        return "caution"
    if str(affective.get("state") or "settled") == "reflective":
        return "stabilize"
    return "explore"


def _derive_influence_strength(
    *,
    influence_state: str,
    dream_summary: dict[str, object],
    adaptive_learning: dict[str, object],
    prompt_summary: dict[str, object],
    epistemic: dict[str, object],
) -> str:
    if influence_state == "quiet":
        return "none"
    if (
        str(dream_summary.get("last_state") or "idle") == "pressing"
        and str(epistemic.get("wrongness_state") or "clear") == "clear"
    ):
        return "medium"
    if str(adaptive_learning.get("learning_engine_mode") or "retain") in {"reinforce", "consolidate"}:
        return "medium" if str(prompt_summary.get("last_state") or "idle") == "pressing" else "low"
    return "low"


def _derive_influence_hint(
    *,
    influence_state: str,
    influence_target: str,
    influence_mode: str,
    guided_learning: dict[str, object],
    adaptive_learning: dict[str, object],
    prompt_summary: dict[str, object],
    dream_artifact: dict[str, object],
) -> str:
    if influence_state == "quiet":
        return "no-bounded-dream-pull"
    latest_summary = str(dream_artifact.get("summary") or "").strip()
    if influence_target == "prompting":
        return (
            f"{influence_mode} prompt-shape toward "
            f"{str(prompt_summary.get('latest_target_asset') or 'prompting')}"
        )
    if influence_target == "learning":
        return (
            f"{influence_mode} learning around "
            f"{str(guided_learning.get('learning_focus') or adaptive_learning.get('reinforcement_target') or 'self-knowledge')}"
        )
    if influence_target == "affective-bearing":
        return f"{influence_mode} reflective-bearing"
    if latest_summary:
        return latest_summary[:120]
    return f"{influence_mode} {influence_target}"


def _derive_confidence(
    *,
    influence_state: str,
    influence_strength: str,
    epistemic: dict[str, object],
    prompt_summary: dict[str, object],
) -> str:
    if influence_state == "quiet":
        return "low"
    if str(epistemic.get("wrongness_state") or "clear") in {"off", "strained"}:
        return "low"
    if influence_strength == "medium" and str(prompt_summary.get("last_state") or "idle") in {"forming", "pressing"}:
        return "medium"
    return "medium"


def _source_contributors(
    *,
    dream_summary: dict[str, object],
    dream_artifact: dict[str, object],
    guided_learning: dict[str, object],
    adaptive_learning: dict[str, object],
    reasoning: dict[str, object],
    affective: dict[str, object],
    epistemic: dict[str, object],
    prompt_summary: dict[str, object],
) -> list[dict[str, str]]:
    contributors = [
        {
            "source": "dream-articulation",
            "signal": (
                f"{str(dream_summary.get('last_state') or 'idle')}"
                f" / reason={str(dream_summary.get('last_reason') or 'no-run-yet')}"
                f" / summary={str(dream_artifact.get('summary') or dream_summary.get('latest_summary') or 'none')[:72]}"
            ),
        },
        {
            "source": "guided-learning",
            "signal": (
                f"{str(guided_learning.get('learning_mode') or 'reinforce')}"
                f" / focus={str(guided_learning.get('learning_focus') or 'reasoning')}"
                f" / pressure={str(guided_learning.get('learning_pressure') or 'low')}"
            ),
        },
        {
            "source": "adaptive-learning",
            "signal": (
                f"{str(adaptive_learning.get('learning_engine_mode') or 'retain')}"
                f" / target={str(adaptive_learning.get('reinforcement_target') or 'reasoning')}"
                f" / maturation={str(adaptive_learning.get('maturation_state') or 'early')}"
            ),
        },
        {
            "source": "adaptive-reasoning",
            "signal": (
                f"{str(reasoning.get('reasoning_mode') or 'direct')}"
                f" / posture={str(reasoning.get('reasoning_posture') or 'balanced')}"
                f" / certainty={str(reasoning.get('certainty_style') or 'crisp')}"
            ),
        },
        {
            "source": "affective-meta-state",
            "signal": (
                f"{str(affective.get('state') or 'settled')}"
                f" / bearing={str(affective.get('bearing') or 'even')}"
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
    return contributors


def _safe_dream_articulation() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.dream_articulation import (
            build_dream_articulation_surface,
        )
        return build_dream_articulation_surface()
    except Exception:
        return None


def _safe_guided_learning() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.guided_learning_runtime import (
            build_guided_learning_runtime_surface,
        )
        return build_guided_learning_runtime_surface()
    except Exception:
        return None


def _safe_adaptive_learning() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.adaptive_learning_runtime import (
            build_adaptive_learning_runtime_surface,
        )
        return build_adaptive_learning_runtime_surface()
    except Exception:
        return None


def _safe_adaptive_reasoning() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.adaptive_reasoning_runtime import (
            build_adaptive_reasoning_runtime_surface,
        )
        return build_adaptive_reasoning_runtime_surface()
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


def _safe_prompt_evolution() -> dict[str, object] | None:
    try:
        from apps.api.jarvis_api.services.prompt_evolution_runtime import (
            build_prompt_evolution_runtime_surface,
        )
        return build_prompt_evolution_runtime_surface()
    except Exception:
        return None
