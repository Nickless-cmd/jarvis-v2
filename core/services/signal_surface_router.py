"""Signal Surface Router — maps surface names to build functions.

All imports are lazy (inside _build_router) to avoid circular imports
and startup cost. read_surface() is the primary entry point for tools.
"""
from __future__ import annotations

from typing import Any, Callable


def _build_router() -> dict[str, Callable[[], dict[str, Any]]]:
    """Build name → function mapping. Local imports stay lazy."""
    # Signal tracking surfaces
    from core.services.autonomy_pressure_signal_tracking import (
        build_runtime_autonomy_pressure_signal_surface,
    )
    from core.services.goal_signal_tracking import (
        build_runtime_goal_signal_surface,
    )
    from core.services.reflection_signal_tracking import (
        build_runtime_reflection_signal_surface,
    )
    from core.services.temporal_recurrence_signal_tracking import (
        build_runtime_temporal_recurrence_signal_surface,
    )
    from core.services.internal_opposition_signal_tracking import (
        build_runtime_internal_opposition_signal_surface,
    )
    from core.services.self_review_signal_tracking import (
        build_runtime_self_review_signal_surface,
    )
    from core.services.dream_hypothesis_signal_tracking import (
        build_runtime_dream_hypothesis_signal_surface,
    )
    from core.services.user_understanding_signal_tracking import (
        build_runtime_user_understanding_signal_surface,
    )
    from core.services.private_inner_note_signal_tracking import (
        build_runtime_private_inner_note_signal_surface,
    )
    from core.services.private_initiative_tension_signal_tracking import (
        build_runtime_private_initiative_tension_signal_surface,
    )
    from core.services.private_inner_interplay_signal_tracking import (
        build_runtime_private_inner_interplay_signal_surface,
    )
    from core.services.private_state_snapshot_tracking import (
        build_runtime_private_state_snapshot_surface,
    )
    from core.services.diary_synthesis_signal_tracking import (
        build_diary_synthesis_signal_surface,
    )
    from core.services.open_loop_signal_tracking import (
        build_runtime_open_loop_signal_surface,
    )
    from core.services.witness_signal_tracking import (
        build_runtime_witness_signal_surface,
    )
    from core.services.emergent_signal_tracking import (
        build_runtime_emergent_signal_surface,
    )
    from core.services.regulation_homeostasis_signal_tracking import (
        build_runtime_regulation_homeostasis_signal_surface,
    )
    from core.services.relation_state_signal_tracking import (
        build_runtime_relation_state_signal_surface,
    )
    from core.services.relation_continuity_signal_tracking import (
        build_runtime_relation_continuity_signal_surface,
    )
    from core.services.meaning_significance_signal_tracking import (
        build_runtime_meaning_significance_signal_surface,
    )
    from core.services.temperament_tendency_signal_tracking import (
        build_runtime_temperament_tendency_signal_surface,
    )
    from core.services.self_narrative_continuity_signal_tracking import (
        build_runtime_self_narrative_continuity_signal_surface,
    )
    from core.services.metabolism_state_signal_tracking import (
        build_runtime_metabolism_state_signal_surface,
    )
    from core.services.release_marker_signal_tracking import (
        build_runtime_release_marker_signal_surface,
    )
    from core.services.attachment_topology_signal_tracking import (
        build_runtime_attachment_topology_signal_surface,
    )
    from core.services.loyalty_gradient_signal_tracking import (
        build_runtime_loyalty_gradient_signal_surface,
    )
    from core.services.executive_contradiction_signal_tracking import (
        build_runtime_executive_contradiction_signal_surface,
    )
    from core.services.inner_visible_support_signal_tracking import (
        build_runtime_inner_visible_support_signal_surface,
    )
    from core.services.chronicle_consolidation_signal_tracking import (
        build_runtime_chronicle_consolidation_signal_surface,
    )
    from core.services.remembered_fact_signal_tracking import (
        build_runtime_remembered_fact_signal_surface,
    )
    from core.services.world_model_signal_tracking import (
        build_runtime_world_model_signal_surface,
    )
    from core.services.self_model_signal_tracking import (
        build_runtime_self_model_signal_surface,
    )
    from core.services.runtime_awareness_signal_tracking import (
        build_runtime_awareness_signal_surface,
    )
    from core.services.consolidation_target_signal_tracking import (
        build_runtime_consolidation_target_signal_surface,
    )
    from core.services.self_review_cadence_signal_tracking import (
        build_runtime_self_review_cadence_signal_surface,
    )
    from core.services.private_temporal_promotion_signal_tracking import (
        build_runtime_private_temporal_promotion_signal_surface,
    )

    # Daemon state surfaces
    from core.services.somatic_daemon import build_body_state_surface
    from core.services.surprise_daemon import build_surprise_surface
    from core.services.thought_action_proposal_daemon import build_proposal_surface
    from core.services.thought_stream_daemon import build_thought_stream_surface
    from core.services.aesthetic_taste_daemon import build_taste_surface
    from core.services.irony_daemon import build_irony_surface
    from core.services.absence_daemon import build_absence_surface
    from core.services.conflict_daemon import build_conflict_surface
    from core.services.reflection_cycle_daemon import build_reflection_surface
    from core.services.curiosity_daemon import build_curiosity_surface
    from core.services.meta_reflection_daemon import build_meta_reflection_surface
    from core.services.experienced_time_daemon import build_experienced_time_surface
    from core.services.development_narrative_daemon import build_development_narrative_surface
    from core.services.creative_drift_daemon import build_creative_drift_surface
    from core.services.existential_wonder_daemon import build_existential_wonder_surface
    from core.services.autonomous_council_daemon import build_autonomous_council_surface
    from core.services.council_memory_daemon import build_council_memory_surface
    from core.services.dream_insight_daemon import build_dream_insight_surface
    from core.services.code_aesthetic_daemon import build_code_aesthetic_surface
    from core.services.memory_decay_daemon import build_memory_decay_surface
    from core.services.user_model_daemon import build_user_model_surface
    from core.services.desire_daemon import build_desire_surface

    # Runtime context surfaces
    from core.services.embodied_state import build_embodied_state_surface
    from core.services.affective_meta_state import build_affective_meta_state_surface
    from core.services.epistemic_runtime_state import build_epistemic_runtime_state_surface
    from core.services.loop_runtime import build_loop_runtime_surface
    from core.services.dream_articulation import build_dream_articulation_surface
    from core.services.subagent_ecology import build_subagent_ecology_surface

    return {
        # Signal tracking
        "autonomy_pressure": build_runtime_autonomy_pressure_signal_surface,
        "goal_signal": build_runtime_goal_signal_surface,
        "reflection_signal": build_runtime_reflection_signal_surface,
        "temporal_recurrence": build_runtime_temporal_recurrence_signal_surface,
        "internal_opposition": build_runtime_internal_opposition_signal_surface,
        "self_review_signal": build_runtime_self_review_signal_surface,
        "dream_hypothesis": build_runtime_dream_hypothesis_signal_surface,
        "user_understanding": build_runtime_user_understanding_signal_surface,
        "private_inner_note": build_runtime_private_inner_note_signal_surface,
        "private_initiative_tension": build_runtime_private_initiative_tension_signal_surface,
        "private_inner_interplay": build_runtime_private_inner_interplay_signal_surface,
        "private_state_snapshot": build_runtime_private_state_snapshot_surface,
        "diary_synthesis": build_diary_synthesis_signal_surface,
        "open_loop": build_runtime_open_loop_signal_surface,
        "witness": build_runtime_witness_signal_surface,
        "emergent": build_runtime_emergent_signal_surface,
        "regulation_homeostasis": build_runtime_regulation_homeostasis_signal_surface,
        "relation_state": build_runtime_relation_state_signal_surface,
        "relation_continuity": build_runtime_relation_continuity_signal_surface,
        "meaning_significance": build_runtime_meaning_significance_signal_surface,
        "temperament_tendency": build_runtime_temperament_tendency_signal_surface,
        "self_narrative_continuity": build_runtime_self_narrative_continuity_signal_surface,
        "metabolism_state": build_runtime_metabolism_state_signal_surface,
        "release_marker": build_runtime_release_marker_signal_surface,
        "attachment_topology": build_runtime_attachment_topology_signal_surface,
        "loyalty_gradient": build_runtime_loyalty_gradient_signal_surface,
        "executive_contradiction": build_runtime_executive_contradiction_signal_surface,
        "inner_visible_support": build_runtime_inner_visible_support_signal_surface,
        "chronicle_consolidation": build_runtime_chronicle_consolidation_signal_surface,
        "remembered_fact": build_runtime_remembered_fact_signal_surface,
        "world_model": build_runtime_world_model_signal_surface,
        "self_model": build_runtime_self_model_signal_surface,
        "runtime_awareness": build_runtime_awareness_signal_surface,
        "consolidation_target": build_runtime_consolidation_target_signal_surface,
        "self_review_cadence": build_runtime_self_review_cadence_signal_surface,
        "private_temporal_promotion": build_runtime_private_temporal_promotion_signal_surface,
        # Daemon state surfaces
        "body_state": build_body_state_surface,
        "surprise": build_surprise_surface,
        "thought_proposals": build_proposal_surface,
        "thought_stream": build_thought_stream_surface,
        "aesthetic_taste": build_taste_surface,
        "irony": build_irony_surface,
        "absence": build_absence_surface,
        "conflict": build_conflict_surface,
        "reflection_cycle": build_reflection_surface,
        "curiosity": build_curiosity_surface,
        "meta_reflection": build_meta_reflection_surface,
        "experienced_time": build_experienced_time_surface,
        "development_narrative": build_development_narrative_surface,
        "creative_drift": build_creative_drift_surface,
        "existential_wonder": build_existential_wonder_surface,
        "dream_insight": build_dream_insight_surface,
        "code_aesthetic": build_code_aesthetic_surface,
        "memory_decay": build_memory_decay_surface,
        "user_model": build_user_model_surface,
        "desire": build_desire_surface,
        "autonomous_council": build_autonomous_council_surface,
        "council_memory": build_council_memory_surface,
        # Runtime context
        "embodied_state": build_embodied_state_surface,
        "affective_meta_state": build_affective_meta_state_surface,
        "epistemic_state": build_epistemic_runtime_state_surface,
        "loop_runtime": build_loop_runtime_surface,
        "dream_articulation": build_dream_articulation_surface,
        "subagent_ecology": build_subagent_ecology_surface,
    }


_ROUTER: dict[str, Callable[[], dict[str, Any]]] | None = None


def _get_router() -> dict[str, Callable[[], dict[str, Any]]]:
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = _build_router()
    return _ROUTER


def get_surface_names() -> list[str]:
    return sorted(_get_router().keys())


def resolve_surface(name: str) -> Callable[[], dict[str, Any]] | None:
    return _get_router().get(name)


def read_surface(name: str) -> dict[str, Any]:
    """Read a named surface. Returns {"error": ..., "valid": [...]} for unknown names."""
    router = _get_router()
    fn = router.get(name)
    if fn is None:
        return {"error": f"unknown surface '{name}'", "valid": sorted(router.keys())}
    try:
        return fn()
    except Exception as exc:
        return {"error": str(exc), "surface": name}


def list_all_surfaces() -> dict[str, Any]:
    """Call all registered surfaces. Per-surface exceptions caught and returned as errors."""
    router = _get_router()
    result: dict[str, Any] = {}
    for name, fn in router.items():
        try:
            result[name] = fn()
        except Exception as exc:
            result[name] = {"error": str(exc)}
    return result
