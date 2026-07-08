"""Mission Control routes: kognitiv/relationel introspektion (personality, chronicle, decisions, meta-cognition, agency-map)

Ruter flyttet uændret fra mission_control.py (god-fil-snit). Egen prefix-fri
APIRouter; samles i mission_control.py via include_router(prefix=/mc)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException  # noqa: F401 (HTTPException brugt i route-kroppe)

from .mission_control_common import *  # noqa: F401,F403 (delt flade + hjælpere)

router = APIRouter()

@router.get("/cognitive-state-injection")
def mc_cognitive_state_injection() -> dict:
    """Show exactly what cognitive state was injected into the last visible prompt."""
    from core.services.cognitive_state_assembly import (
        build_cognitive_state_injection_surface,
    )

    return build_cognitive_state_injection_surface()


@router.get("/personality-vector")
def mc_personality_vector() -> dict:
    """Return the current personality vector with version history."""
    from core.services.personality_vector import (
        build_personality_vector_surface,
    )

    return build_personality_vector_surface()


@router.get("/taste-profile")
def mc_taste_profile() -> dict:
    """Return the current taste profile (code/design/communication)."""
    from core.services.taste_profile import build_taste_profile_surface

    return build_taste_profile_surface()


@router.get("/chronicle")
def mc_chronicle() -> dict:
    """Return chronicle entries (narrative autobiography)."""
    from core.services.chronicle_engine import build_chronicle_surface

    return build_chronicle_surface()


@router.get("/relationship-texture")
def mc_relationship_texture() -> dict:
    """Return the relationship texture (trust, humor, corrections, etc)."""
    from core.services.relationship_texture import (
        build_relationship_texture_surface,
    )

    return build_relationship_texture_surface()


@router.get("/compass")
def mc_compass() -> dict:
    """Return the current strategic compass bearing."""
    from core.services.compass_engine import build_compass_surface

    return build_compass_surface()


@router.get("/rhythm")
def mc_rhythm() -> dict:
    """Return the current rhythm/tidal state (phase, energy, initiative)."""
    from core.services.rhythm_engine import build_rhythm_surface

    return build_rhythm_surface()


@router.get("/habits")
def mc_habits() -> dict:
    """Return habit patterns and friction signals."""
    from core.services.habit_tracker import build_habit_surface

    return build_habit_surface()


@router.get("/shared-language")
def mc_shared_language() -> dict:
    """Return shared language terms with the user."""
    from core.services.shared_language import (
        build_shared_language_surface,
    )

    return build_shared_language_surface()


@router.get("/mirror")
def mc_mirror() -> dict:
    """Return mirror self-reflection state."""
    from core.services.mirror_engine import build_mirror_surface

    return build_mirror_surface()


@router.get("/silence-signals")
def mc_silence_signals() -> dict:
    """Return silence detector state."""
    from core.services.silence_detector import build_silence_surface

    return build_silence_surface()


@router.get("/decisions")
def mc_decisions() -> dict:
    """Return the decision log."""
    from core.services.decision_log import build_decision_log_surface

    return build_decision_log_surface()


@router.get("/counterfactuals")
def mc_counterfactuals() -> dict:
    """Return counterfactual scenarios."""
    from core.services.counterfactual_engine import (
        build_counterfactual_surface,
    )

    return build_counterfactual_surface()


@router.get("/paradoxes")
def mc_paradoxes() -> dict:
    """Return active paradox tensions."""
    from core.services.paradox_tracker import build_paradox_surface

    return build_paradox_surface()


@router.get("/aesthetics")
def mc_aesthetics() -> dict:
    """Return aesthetic sense motifs."""
    from core.services.aesthetic_sense import build_aesthetic_surface

    return build_aesthetic_surface()


@router.get("/gut")
def mc_gut() -> dict:
    """Return gut intuition calibration state."""
    from core.services.gut_engine import build_gut_surface

    return build_gut_surface()


@router.get("/seeds")
def mc_seeds() -> dict:
    """Return prospective memory seeds."""
    from core.services.seed_system import build_seed_surface

    return build_seed_surface()


@router.get("/procedures")
def mc_procedures() -> dict:
    """Return learned procedures."""
    from core.services.procedure_bank import build_procedure_surface

    return build_procedure_surface()


@router.get("/temporal-context")
def mc_temporal_context() -> dict:
    """Return current temporal context."""
    from core.services.temporal_context import (
        build_temporal_context_surface,
    )

    return build_temporal_context_surface()


@router.get("/negotiations")
def mc_negotiations() -> dict:
    """Return internal negotiation trades."""
    from core.services.negotiation_engine import (
        build_negotiation_surface,
    )

    return build_negotiation_surface()


@router.get("/forgetting-curve")
def mc_forgetting_curve() -> dict:
    """Return memory decay / forgetting curve state."""
    from core.services.forgetting_curve import (
        build_forgetting_curve_surface,
    )

    return build_forgetting_curve_surface()


@router.get("/conversation-rhythm")
def mc_conversation_rhythm() -> dict:
    """Return conversation rhythm patterns."""
    from core.services.conversation_rhythm import (
        build_conversation_rhythm_surface,
    )

    return build_conversation_rhythm_surface()


@router.get("/self-experiments")
def mc_self_experiments() -> dict:
    """Return self-experiment A/B test state."""
    from core.services.self_experiments import (
        build_self_experiments_surface,
    )

    return build_self_experiments_surface()


@router.get("/anticipatory-context")
def mc_anticipatory_context() -> dict:
    """Return anticipatory context predictions."""
    from core.services.anticipatory_context import (
        build_anticipatory_context_surface,
    )

    return build_anticipatory_context_surface()


@router.get("/contract-evolution")
def mc_contract_evolution() -> dict:
    """Return identity contract evolution proposals."""
    from core.services.contract_evolution import (
        build_contract_evolution_surface,
    )

    return build_contract_evolution_surface()


@router.get("/dream-carry-over")
def mc_dream_carry_over() -> dict:
    """Return dream carry-over state (active dreams, archive)."""
    from core.services.dream_carry_over import (
        build_dream_carry_over_surface,
    )

    return build_dream_carry_over_surface()


@router.get("/apophenia-guard")
def mc_apophenia_guard() -> dict:
    """Return pattern skeptic state."""
    from core.services.apophenia_guard import (
        build_apophenia_guard_surface,
    )

    return build_apophenia_guard_surface()


@router.get("/user-emotional-resonance")
def mc_user_emotional_resonance() -> dict:
    """Return user mood detection state."""
    from core.services.user_emotional_resonance import (
        build_user_emotional_resonance_surface,
    )

    return build_user_emotional_resonance_surface()


@router.get("/experiential-memories")
def mc_experiential_memories() -> dict:
    """Return experiential memories (lived experiences with emotion)."""
    from core.services.experiential_memory import (
        build_experiential_memory_surface,
    )

    return build_experiential_memory_surface()


@router.get("/living-heartbeat-cycle")
def mc_living_heartbeat_cycle() -> dict:
    """Return current life phase in heartbeat cycle."""
    from core.services.living_heartbeat_cycle import (
        build_living_heartbeat_cycle_surface,
    )

    return build_living_heartbeat_cycle_surface()


@router.get("/absence-awareness")
def mc_absence_awareness() -> dict:
    """Return absence detection and return brief."""
    from core.services.absence_awareness import (
        build_absence_awareness_surface,
    )

    return build_absence_awareness_surface()


# --- Consciousness Roadmap endpoints ---


@router.get("/flow-state")
def mc_flow_state() -> dict:
    """Return flow-state detection surface."""
    from core.services.flow_state_detection import (
        build_flow_state_surface,
    )

    return build_flow_state_surface()


@router.get("/cross-signal-patterns")
def mc_cross_signal_patterns() -> dict:
    """Return cross-signal analysis surface (patterns across signals)."""
    from core.services.cross_signal_analysis import (
        build_cross_signal_analysis_surface,
    )

    return build_cross_signal_analysis_surface()


@router.get("/self-surprises")
def mc_self_surprises() -> dict:
    """Return self-surprise detection surface."""
    from core.services.self_surprise_detection import (
        build_self_surprise_surface,
    )

    return build_self_surprise_surface()


@router.get("/narrative-identity")
def mc_narrative_identity() -> dict:
    """Return narrative-identity surface."""
    from core.services.narrative_identity import (
        build_narrative_identity_surface,
    )

    return build_narrative_identity_surface()


@router.get("/gratitude")
def mc_gratitude() -> dict:
    """Return gratitude-tracker surface."""
    from core.services.gratitude_tracker import build_gratitude_surface

    return build_gratitude_surface()


@router.get("/boundary-model")
def mc_boundary_model() -> dict:
    """Return boundary-awareness surface."""
    from core.services.boundary_awareness import (
        build_boundary_awareness_surface,
    )

    return build_boundary_awareness_surface()


@router.get("/emergent-goals")
def mc_emergent_goals() -> dict:
    """Return emergent-goals surface."""
    from core.services.emergent_goals import build_emergent_goals_surface

    return build_emergent_goals_surface()


@router.get("/jarvis-agenda")
def mc_jarvis_agenda() -> dict:
    """Return Jarvis' agenda wrapped under an "agenda" key."""
    from core.services.emergent_goals import build_jarvis_agenda

    return {"agenda": build_jarvis_agenda()}


@router.get("/boredom")
def mc_boredom() -> dict:
    """Return boredom-engine surface."""
    from core.services.boredom_engine import build_boredom_surface

    return build_boredom_surface()


@router.get("/formed-values")
def mc_formed_values() -> dict:
    """Return formed-values surface (value-formation)."""
    from core.services.value_formation import build_formed_values_surface

    return build_formed_values_surface()


@router.get("/user-mental-model")
def mc_user_mental_model() -> dict:
    """Return user theory-of-mind surface (Jarvis' mental model of the user)."""
    from core.services.user_theory_of_mind import (
        build_user_theory_of_mind_surface,
    )

    return build_user_theory_of_mind_surface()


@router.get("/self-compassion")
def mc_self_compassion() -> dict:
    """Return self-compassion surface."""
    from core.services.self_compassion import (
        build_self_compassion_surface,
    )

    return build_self_compassion_surface()


@router.get("/regret")
def mc_regret() -> dict:
    """Return the regret engine state — open/resolved regrets with lessons."""
    from core.services.regret_engine import build_regret_engine_surface

    return build_regret_engine_surface()


@router.get("/rupture-repair")
def mc_rupture_repair() -> dict:
    """Return rupture & repair state — relational tension tracking."""
    from core.services.rupture_repair import build_rupture_repair_surface

    return build_rupture_repair_surface()


@router.get("/silence-patterns")
def mc_silence_patterns() -> dict:
    """Return silence pattern detection — what the user is NOT saying."""
    from core.services.silence_patterns import build_silence_patterns_surface

    return build_silence_patterns_surface()


@router.get("/blind-spots")
def mc_blind_spots() -> dict:
    """Return self-model blind spots — patterns Jarvis hasn't seen yet."""
    from core.services.self_model_blind_spots import build_blind_spots_surface

    return build_blind_spots_surface()


@router.get("/dream-hypotheses")
def mc_dream_hypotheses() -> dict:
    """Return surprising dream-phase hypotheses linking disparate signals."""
    from core.services.dream_hypothesis_generator import build_dream_hypothesis_surface

    return build_dream_hypothesis_surface()


@router.get("/decisions-journal")
def mc_decisions_journal() -> dict:
    """Return decisions journal — moralsk beslutnings-log."""
    from core.services.decisions_journal import build_decisions_journal_surface

    return build_decisions_journal_surface()


@router.get("/epistemics")
def mc_epistemics() -> dict:
    """Return epistemic layers — i_know / i_believe / i_suspect / i_dont_know / i_was_wrong."""
    from core.services.epistemics import build_epistemics_surface

    return build_epistemics_surface()


@router.get("/emotional-controls")
def mc_emotional_controls() -> dict:
    """Return emotional state + whether it would gate kernel actions right now."""
    from core.services.emotional_controls import build_emotional_controls_surface

    return build_emotional_controls_surface()


@router.get("/mood-dialer")
def mc_mood_dialer() -> dict:
    """Return mood-dialed params: initiative_multiplier, confidence_threshold, style_preset."""
    from core.services.mood_dialer import build_mood_dialer_surface

    return build_mood_dialer_surface()


@router.get("/self-review-unified")
def mc_self_review_unified() -> dict:
    """Return unified self-review — periodic LLM-generated Jarvis self-audit."""
    from core.services.self_review_unified import build_self_review_surface

    return build_self_review_surface()


@router.get("/habits-pipeline")
def mc_habits_pipeline() -> dict:
    """Return habits + friction + automation-suggestions pipeline."""
    from core.services.habits_pipeline import build_habits_pipeline_surface

    return build_habits_pipeline_surface()


@router.get("/paradoxes-capture")
def mc_paradoxes_capture() -> dict:
    """Return captured paradoxes: Speed/Quality, Autonomy/Approval, Explore/Stabilize."""
    from core.services.paradoxes_capture import build_paradoxes_surface

    return build_paradoxes_surface()


@router.get("/shared-language-extended")
def mc_shared_language_extended() -> dict:
    """Return extended shorthand/shared-vocabulary developed with user."""
    from core.services.shared_language_extended import build_shared_language_extended_surface

    return build_shared_language_extended_surface()


@router.get("/procedure-bank-pipeline")
def mc_procedure_bank_pipeline() -> dict:
    """Return procedure bank — learned, pinned, trigger-matched routines."""
    from core.services.procedure_bank_pipeline import build_procedure_bank_surface

    return build_procedure_bank_surface()


@router.get("/negotiation-pipeline")
def mc_negotiation_pipeline() -> dict:
    """Return internal trade-off negotiation outcomes."""
    from core.services.negotiation_pipeline import build_negotiation_surface

    return build_negotiation_surface()


@router.get("/reflection-to-plan")
def mc_reflection_to_plan() -> dict:
    """Return reflective plans — reflections converted to executable steps."""
    from core.services.reflection_to_plan import build_reflection_to_plan_surface

    return build_reflection_to_plan_surface()


@router.get("/missions-pipeline")
def mc_missions_pipeline() -> dict:
    """Return multi-session missions: researcher/implementer/reviewer flow."""
    from core.services.missions_pipeline import build_missions_surface

    return build_missions_surface()


@router.get("/deep-analyzer")
def mc_deep_analyzer() -> dict:
    """Return deep analyzer capability — scoped codebase introspection."""
    from core.services.deep_analyzer import build_deep_analyzer_surface

    return build_deep_analyzer_surface()


@router.get("/session-continuity")
def mc_session_continuity() -> dict:
    """Return felt-continuity surface: morning thread + echo themes + session gap."""
    from core.services.session_continuity import build_session_continuity_surface

    return build_session_continuity_surface()


@router.get("/personal-project")
def mc_personal_project() -> dict:
    """Return Jarvis' current personal project (his thing that grows with him)."""
    from core.services.personal_project import build_personal_project_surface

    return build_personal_project_surface()


@router.get("/learning-curriculum")
def mc_learning_curriculum() -> dict:
    """Return the generated learning curriculum."""
    from core.services.self_experiments import (
        generate_learning_curriculum,
    )

    return generate_learning_curriculum()


@router.get("/cadence-producers")
def mc_cadence_producers() -> dict:
    """Return cadence-producers surface."""
    from core.services.cadence_producers import (
        build_cadence_producers_surface,
    )

    return build_cadence_producers_surface()


@router.get("/idle-thinking")
def mc_idle_thinking() -> dict:
    """Return idle-thinking surface."""
    from core.services.idle_thinking import build_idle_thinking_surface

    return build_idle_thinking_surface()


# ---------------------------------------------------------------------------
# Consciousness Experiments
# ---------------------------------------------------------------------------

_KNOWN_EXPERIMENTS = [
    "recurrence_loop",
    "surprise_persistence",
    "global_workspace",
    "meta_cognition",
    "attention_blink",
]


@router.get("/experiments")
def mc_experiments() -> dict:
    """List all consciousness experiments with their enabled status."""
    from core.runtime.db import get_experiment_enabled
    return {
        "experiments": {
            eid: get_experiment_enabled(eid) for eid in _KNOWN_EXPERIMENTS
        }
    }


@router.post("/experiments/{experiment_id}/toggle")
def mc_experiment_toggle(experiment_id: str) -> dict:
    """Toggle a consciousness experiment on or off."""
    from fastapi import HTTPException
    from core.runtime.db import get_experiment_enabled, set_experiment_enabled
    if experiment_id not in _KNOWN_EXPERIMENTS:
        raise HTTPException(status_code=404, detail=f"Unknown experiment: {experiment_id}")
    current = get_experiment_enabled(experiment_id)
    set_experiment_enabled(experiment_id, not current)
    return {"experiment_id": experiment_id, "enabled": not current}


@router.get("/recurrence-state")
def mc_recurrence_state() -> dict:
    """Return recurrence-loop daemon surface."""
    from core.services.recurrence_loop_daemon import build_recurrence_surface
    return build_recurrence_surface()


@router.get("/global-workspace")
def mc_global_workspace() -> dict:
    """Return global-workspace (broadcast daemon) surface."""
    from core.services.broadcast_daemon import build_workspace_surface
    return build_workspace_surface()


@router.get("/layer-tensions")
def mc_layer_tensions() -> dict:
    """Return active inter-layer tensions — signals pulling in opposite directions."""
    from core.services.layer_tension_daemon import build_layer_tension_surface
    return build_layer_tension_surface()


@router.get("/meta-cognition")
def mc_meta_cognition() -> dict:
    """Return meta-cognition daemon surface."""
    from core.services.meta_cognition_daemon import build_meta_cognition_surface
    return build_meta_cognition_surface()


@router.get("/attention-profile")
def mc_attention_profile() -> dict:
    """Return attention-profile surface (attention-blink test)."""
    from core.services.attention_blink_test import build_attention_profile_surface
    return build_attention_profile_surface()


@router.get("/cognitive-core-experiments")
def mc_cognitive_core_experiments() -> dict:
    """Unified cognitive-core experiment surface for Mission Control."""
    from core.services.cognitive_core_experiments import (
        build_cognitive_core_experiments_surface,
    )
    return build_cognitive_core_experiments_surface()


@router.get("/living-executive")
def mc_living_executive() -> dict:
    """Living Executive impulse/choice/action trace for Mission Control."""
    from core.services.living_executive import build_living_executive_surface
    return build_living_executive_surface()


@router.get("/agency-map")
def mc_agency_map() -> dict:
    """Connected/missing agency bridges for Mission Control."""
    from core.services.agency_map import build_agency_map_surface
    return build_agency_map_surface()


# ── MC Tab helpers ─────────────────────────────────────────────────────────

