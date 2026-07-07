"""Mission Control routes: jarvis-introspektion (cognitive-frame, attention-budget, self-*, dream-*, embodied)

Ruter flyttet uændret fra mission_control.py (god-fil-snit). Egen prefix-fri
APIRouter; samles i mission_control.py via include_router(prefix=/mc)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException  # noqa: F401 (HTTPException brugt i route-kroppe)

from .mission_control_common import *  # noqa: F401,F403 (delt flade + hjælpere)

router = APIRouter()

@router.get("/jarvis")
def mc_jarvis() -> dict:
    cached = _get_cached_mc_payload("jarvis", 5.0)
    if cached is not None:
        return cached  # type: ignore[return-value]

    runtime = _mc_facade("mc_runtime")()  # mc_runtime-ruten bor i mission_control_runtime_config
    visible_identity = dict(runtime.get("visible_identity") or {})
    visible_session = dict(runtime.get("visible_session_continuity") or {})
    visible_continuity = dict(runtime.get("visible_continuity") or {})
    visible_capability = dict(runtime.get("visible_capability_continuity") or {})
    private_state = dict(runtime.get("private_state") or {})
    protected_voice = dict(runtime.get("protected_inner_voice") or {})
    inner_interplay = dict(runtime.get("private_inner_interplay") or {})
    initiative_tension = dict(runtime.get("private_initiative_tension") or {})
    relation_state = dict(runtime.get("private_relation_state") or {})
    temporal_curiosity = dict(runtime.get("private_temporal_curiosity_state") or {})
    promotion_signal = dict(runtime.get("private_temporal_promotion_signal") or {})
    promotion_decision = dict(runtime.get("private_promotion_decision") or {})
    retained_record = dict(runtime.get("private_retained_memory_record") or {})
    retained_projection = dict(runtime.get("private_retained_memory_projection") or {})
    self_model = dict(runtime.get("private_self_model") or {})
    development_state = dict(runtime.get("private_development_state") or {})
    growth_note = dict(runtime.get("private_growth_note") or {})
    reflective = dict(runtime.get("private_reflective_selection") or {})
    operational_preference = dict(runtime.get("private_operational_preference") or {})
    operational_alignment = dict(runtime.get("operational_preference_alignment") or {})
    development_focuses = dict(runtime.get("runtime_development_focuses") or {})
    reflective_critics = dict(runtime.get("runtime_reflective_critics") or {})
    self_model_signals = dict(runtime.get("runtime_self_model_signals") or {})
    goal_signals = dict(runtime.get("runtime_goal_signals") or {})
    reflection_signals = dict(runtime.get("runtime_reflection_signals") or {})
    temporal_recurrence_signals = dict(
        runtime.get("runtime_temporal_recurrence_signals") or {}
    )
    witness_signals = dict(runtime.get("runtime_witness_signals") or {})
    open_loop_signals = dict(runtime.get("runtime_open_loop_signals") or {})
    open_loop_closure_proposals = dict(
        runtime.get("runtime_open_loop_closure_proposals") or {}
    )
    internal_opposition_signals = dict(
        runtime.get("runtime_internal_opposition_signals") or {}
    )
    self_review_signals = dict(runtime.get("runtime_self_review_signals") or {})
    self_review_records = dict(runtime.get("runtime_self_review_records") or {})
    self_review_runs = dict(runtime.get("runtime_self_review_runs") or {})
    self_review_outcomes = dict(runtime.get("runtime_self_review_outcomes") or {})
    self_review_cadence_signals = dict(
        runtime.get("runtime_self_review_cadence_signals") or {}
    )
    dream_hypothesis_signals = dict(
        runtime.get("runtime_dream_hypothesis_signals") or {}
    )
    dream_adoption_candidates = dict(
        runtime.get("runtime_dream_adoption_candidates") or {}
    )
    dream_influence_proposals = dict(
        runtime.get("runtime_dream_influence_proposals") or {}
    )
    self_authored_prompt_proposals = dict(
        runtime.get("runtime_self_authored_prompt_proposals") or {}
    )
    prompt_evolution = dict(runtime.get("runtime_prompt_evolution") or {})
    user_understanding_signals = dict(
        runtime.get("runtime_user_understanding_signals") or {}
    )
    remembered_fact_signals = dict(runtime.get("runtime_remembered_fact_signals") or {})
    private_inner_note_signals = dict(
        runtime.get("runtime_private_inner_note_signals") or {}
    )
    private_initiative_tension_signals = dict(
        runtime.get("runtime_private_initiative_tension_signals") or {}
    )
    private_inner_interplay_signals = dict(
        runtime.get("runtime_private_inner_interplay_signals") or {}
    )
    private_state_snapshots = dict(runtime.get("runtime_private_state_snapshots") or {})
    diary_synthesis_signals = dict(runtime.get("runtime_diary_synthesis_signals") or {})
    private_temporal_curiosity_states = dict(
        runtime.get("runtime_private_temporal_curiosity_states") or {}
    )
    inner_visible_support_signals = dict(
        runtime.get("runtime_inner_visible_support_signals") or {}
    )
    regulation_homeostasis_signals = dict(
        runtime.get("runtime_regulation_homeostasis_signals") or {}
    )
    relation_state_signals = dict(runtime.get("runtime_relation_state_signals") or {})
    relation_continuity_signals = dict(
        runtime.get("runtime_relation_continuity_signals") or {}
    )
    meaning_significance_signals = dict(
        runtime.get("runtime_meaning_significance_signals") or {}
    )
    temperament_tendency_signals = dict(
        runtime.get("runtime_temperament_tendency_signals") or {}
    )
    self_narrative_continuity_signals = dict(
        runtime.get("runtime_self_narrative_continuity_signals") or {}
    )
    metabolism_state_signals = dict(
        runtime.get("runtime_metabolism_state_signals") or {}
    )
    release_marker_signals = dict(runtime.get("runtime_release_marker_signals") or {})
    consolidation_target_signals = dict(
        runtime.get("runtime_consolidation_target_signals") or {}
    )
    selective_forgetting_candidates = dict(
        runtime.get("runtime_selective_forgetting_candidates") or {}
    )
    attachment_topology_signals = dict(
        runtime.get("runtime_attachment_topology_signals") or {}
    )
    loyalty_gradient_signals = dict(
        runtime.get("runtime_loyalty_gradient_signals") or {}
    )
    autonomy_pressure_signals = dict(
        runtime.get("runtime_autonomy_pressure_signals") or {}
    )
    proactive_loop_lifecycle_signals = dict(
        runtime.get("runtime_proactive_loop_lifecycle_signals") or {}
    )
    proactive_question_gates = dict(
        runtime.get("runtime_proactive_question_gates") or {}
    )
    webchat_execution_pilot = dict(runtime.get("runtime_webchat_execution_pilot") or {})
    self_narrative_self_model_review_bridge = dict(
        runtime.get("runtime_self_narrative_self_model_review_bridge") or {}
    )
    executive_contradiction_signals = dict(
        runtime.get("runtime_executive_contradiction_signals") or {}
    )
    private_temporal_promotion_signals = dict(
        runtime.get("runtime_private_temporal_promotion_signals") or {}
    )
    chronicle_consolidation_signals = dict(
        runtime.get("runtime_chronicle_consolidation_signals") or {}
    )
    chronicle_consolidation_briefs = dict(
        runtime.get("runtime_chronicle_consolidation_briefs") or {}
    )
    chronicle_consolidation_proposals = dict(
        runtime.get("runtime_chronicle_consolidation_proposals") or {}
    )
    user_md_update_proposals = dict(
        runtime.get("runtime_user_md_update_proposals") or {}
    )
    memory_md_update_proposals = dict(
        runtime.get("runtime_memory_md_update_proposals") or {}
    )
    selfhood_proposals = dict(runtime.get("runtime_selfhood_proposals") or {})
    world_model_signals = dict(runtime.get("runtime_world_model_signals") or {})
    runtime_awareness_signals = dict(runtime.get("runtime_awareness_signals") or {})
    runtime_work = dict(runtime.get("runtime_work") or {})
    emergent_signals = dict(runtime.get("runtime_emergent_signals") or {})
    heartbeat = dict(runtime.get("heartbeat_runtime") or {})
    private_brain = _mc_facade("build_private_brain_surface")()
    session_distillation = _mc_facade("build_session_distillation_surface")()
    heartbeat_state = heartbeat.get("state") or {}
    self_knowledge = _mc_facade("build_runtime_self_knowledge_map")(heartbeat_state=heartbeat_state)
    cognitive_frame = _mc_facade("build_cognitive_frame")(
        self_knowledge=self_knowledge,
        heartbeat_state=heartbeat_state,
    )

    payload = {
        "summary": {
            "visible_identity": _jarvis_identity_summary(visible_identity),
            "state_signal": _jarvis_state_signal(
                protected_voice, initiative_tension, private_state
            ),
            "retained_memory": _jarvis_retained_summary(
                retained_projection, retained_record
            ),
            "development": _jarvis_development_summary(
                self_model,
                development_state,
                development_focuses,
                reflective_critics,
                self_model_signals,
                goal_signals,
                reflection_signals,
            ),
            "continuity": _jarvis_continuity_summary(
                relation_state,
                visible_session,
                promotion_signal,
                world_model_signals,
                runtime_awareness_signals,
                runtime_work,
            ),
            "emergent": _jarvis_emergent_summary(emergent_signals),
            "heartbeat": _jarvis_heartbeat_summary(heartbeat),
        },
        "state": {
            "visible_identity": visible_identity,
            "private_state": private_state,
            "protected_inner_voice": protected_voice,
            "inner_interplay": inner_interplay,
            "initiative_tension": initiative_tension,
        },
        "memory": {
            "retained_projection": retained_projection,
            "retained_record": retained_record,
            "visible_capability_continuity": visible_capability,
        },
        "development": {
            "self_model": self_model,
            "development_state": development_state,
            "growth_note": growth_note,
            "reflective_selection": reflective,
            "operational_preference": operational_preference,
            "operational_alignment": operational_alignment,
            "temporal_curiosity": temporal_curiosity,
            "development_focuses": development_focuses,
            "reflective_critics": reflective_critics,
            "self_model_signals": self_model_signals,
            "goal_signals": goal_signals,
            "reflection_signals": reflection_signals,
            "temporal_recurrence_signals": temporal_recurrence_signals,
            "witness_signals": witness_signals,
            "open_loop_signals": open_loop_signals,
            "open_loop_closure_proposals": open_loop_closure_proposals,
            "internal_opposition_signals": internal_opposition_signals,
            "self_review_signals": self_review_signals,
            "self_review_records": self_review_records,
            "self_review_runs": self_review_runs,
            "self_review_outcomes": self_review_outcomes,
            "self_review_cadence_signals": self_review_cadence_signals,
            "dream_hypothesis_signals": dream_hypothesis_signals,
            "dream_adoption_candidates": dream_adoption_candidates,
            "dream_influence_proposals": dream_influence_proposals,
            "self_authored_prompt_proposals": self_authored_prompt_proposals,
            "prompt_evolution": prompt_evolution,
            "user_understanding_signals": user_understanding_signals,
            "private_inner_note_signals": private_inner_note_signals,
            "private_initiative_tension_signals": private_initiative_tension_signals,
            "private_inner_interplay_signals": private_inner_interplay_signals,
            "private_state_snapshots": private_state_snapshots,
            "diary_synthesis_signals": diary_synthesis_signals,
            "private_temporal_curiosity_states": private_temporal_curiosity_states,
            "inner_visible_support_signals": inner_visible_support_signals,
            "regulation_homeostasis_signals": regulation_homeostasis_signals,
            "relation_state_signals": relation_state_signals,
            "relation_continuity_signals": relation_continuity_signals,
            "meaning_significance_signals": meaning_significance_signals,
            "temperament_tendency_signals": temperament_tendency_signals,
            "self_narrative_continuity_signals": self_narrative_continuity_signals,
            "metabolism_state_signals": metabolism_state_signals,
            "release_marker_signals": release_marker_signals,
            "consolidation_target_signals": consolidation_target_signals,
            "selective_forgetting_candidates": selective_forgetting_candidates,
            "attachment_topology_signals": attachment_topology_signals,
            "loyalty_gradient_signals": loyalty_gradient_signals,
            "autonomy_pressure_signals": autonomy_pressure_signals,
            "proactive_loop_lifecycle_signals": proactive_loop_lifecycle_signals,
            "proactive_question_gates": proactive_question_gates,
            "webchat_execution_pilot": webchat_execution_pilot,
            "self_narrative_self_model_review_bridge": self_narrative_self_model_review_bridge,
            "executive_contradiction_signals": executive_contradiction_signals,
            "private_temporal_promotion_signals": private_temporal_promotion_signals,
            "chronicle_consolidation_signals": chronicle_consolidation_signals,
            "chronicle_consolidation_briefs": chronicle_consolidation_briefs,
            "chronicle_consolidation_proposals": chronicle_consolidation_proposals,
            "user_md_update_proposals": user_md_update_proposals,
            "memory_md_update_proposals": memory_md_update_proposals,
            "selfhood_proposals": selfhood_proposals,
            "emergent_signals": emergent_signals,
        },
        "continuity": {
            "visible_session": visible_session,
            "visible_continuity": visible_continuity,
            "relation_state": relation_state,
            "promotion_signal": promotion_signal,
            "promotion_decision": promotion_decision,
            "remembered_fact_signals": remembered_fact_signals,
            "world_model_signals": world_model_signals,
            "runtime_awareness_signals": runtime_awareness_signals,
            "runtime_work": runtime_work,
        },
        "heartbeat": heartbeat,
        "brain": {
            "private_brain": private_brain,
            "session_distillation": session_distillation,
        },
        "self_knowledge": self_knowledge,
        "cognitive_frame": cognitive_frame,
    }
    return _store_cached_mc_payload("jarvis", 5.0, payload)  # type: ignore[return-value]


@router.get("/cognitive-frame")
def mc_cognitive_frame() -> dict:
    with runtime_surface_cache():
        return _mc_facade("build_cognitive_frame")()


@router.get("/attention-budget")
def mc_attention_budget() -> dict:
    """Return attention budget traces for all prompt paths."""
    bundle = _mc_runtime_inspection_bundle()
    attention_snapshot = dict(bundle.get("attention_budget") or {})
    # Live runtime traces from the last actual prompt assembly
    from core.services.prompt_contract import get_last_attention_traces

    live_traces = get_last_attention_traces()
    return {
        **attention_snapshot,
        "live_traces": live_traces,
    }


@router.get("/conflict-resolution")
def mc_conflict_resolution() -> dict:
    """Return the last conflict resolution trace."""
    from core.services.conflict_resolution import get_last_conflict_trace

    trace = get_last_conflict_trace()
    return {"trace": trace, "active": trace is not None}


@router.get("/self-code-changes")
def mc_self_code_changes() -> dict:
    """Return Jarvis' recent self-mutations — files he wrote or edited in his own runtime."""
    from core.services.self_mutation_lineage import build_self_mutation_lineage_surface
    return build_self_mutation_lineage_surface(limit=50)


@router.get("/self-deception-guard")
def mc_self_deception_guard() -> dict:
    """Return the last self-deception guard trace."""
    from core.services.self_deception_guard import get_last_guard_trace

    trace = get_last_guard_trace()
    return {"trace": trace, "active": trace is not None}


@router.get("/witness-daemon")
def mc_witness_daemon() -> dict:
    """Return the current witness daemon state."""
    from core.services.witness_signal_tracking import (
        get_witness_daemon_state,
    )

    return get_witness_daemon_state()


@router.get("/inner-voice-daemon")
def mc_inner_voice_daemon() -> dict:
    """Return the current inner voice daemon state."""
    from core.services.inner_voice_daemon import (
        get_inner_voice_daemon_state,
    )

    return get_inner_voice_daemon_state()


@router.get("/internal-cadence")
def mc_internal_cadence() -> dict:
    """Return the current internal cadence layer state."""
    from core.services.internal_cadence import get_cadence_state

    return get_cadence_state()


@router.get("/emergent-signals")
def mc_emergent_signals() -> dict:
    """Return current bounded emergent inner signals."""
    return build_runtime_emergent_signal_surface(limit=8)


@router.get("/self-knowledge")
def mc_self_knowledge() -> dict:
    with runtime_surface_cache():
        return _mc_facade("build_runtime_self_knowledge_map")()


@router.get("/runtime-self-model")
def mc_runtime_self_model() -> dict:
    """Return the current runtime self-model snapshot."""
    bundle = _mc_runtime_inspection_bundle()
    return dict(bundle.get("runtime_self_model") or {})


@router.get("/self-critique")
def mc_self_critique() -> dict:
    """Return the current self-critique runtime surface."""
    return _mc_facade("build_self_critique_surface")()


@router.get("/creative-journal")
def mc_creative_journal() -> dict:
    """Return the current private creative journal surface."""
    return _mc_facade("build_creative_journal_surface")()


@router.get("/finitude")
def mc_finitude() -> dict:
    """Return Jarvis's bounded finitude and transition surface."""
    return _mc_facade("build_finitude_surface")()


@router.get("/dream-distillation")
def mc_dream_distillation() -> dict:
    """Return the current dream residue distillation surface."""
    return _mc_facade("build_dream_distillation_surface")()


@router.get("/unconscious-temperature-field")
def mc_unconscious_temperature_field() -> dict:
    """Return the current bounded user temperature field surface."""
    return _mc_facade("build_unconscious_temperature_field_surface")()


@router.get("/embodied-state")
def mc_embodied_state() -> dict:
    """Return the current bounded embodied host/body state."""
    return _mc_facade("build_embodied_state_surface")()


# Living Mind daemon surface routes extracted to mission_control_living_mind.py
# (Boy Scout rule — routes with in-memory proxy support live there)
from apps.api.jarvis_api.routes.mission_control_living_mind import router as _living_mind_router
router.include_router(_living_mind_router)


@router.get("/affective-meta-state")
def mc_affective_meta_state() -> dict:
    """Return the current bounded affective/meta runtime state."""
    return _mc_facade("build_affective_meta_state_surface")()


@router.get("/emotion-concepts")
def mc_emotion_concepts() -> dict:
    """Return active Lag-2 emotion concept signals and their Lag-1 influence deltas."""
    try:
        from core.services.emotion_concepts import build_emotion_concept_surface
        return build_emotion_concept_surface()
    except Exception as exc:
        return {"active": False, "active_count": 0, "concepts": [], "error": str(exc)}


@router.get("/experiential-runtime-context")
def mc_experiential_runtime_context() -> dict:
    """Return the current bounded experiential runtime context (body/tone/intermittence/pressure)."""
    bundle = _mc_runtime_inspection_bundle()
    return dict(bundle.get("experiential_runtime_context") or {})


@router.get("/epistemic-runtime-state")
def mc_epistemic_runtime_state() -> dict:
    """Return the current bounded epistemic runtime state."""
    return _mc_facade("build_epistemic_runtime_state_surface")()


@router.get("/loop-runtime")
def mc_loop_runtime() -> dict:
    """Return the current bounded loop runtime state."""
    return _mc_facade("build_loop_runtime_surface")()


@router.get("/idle-consolidation")
def mc_idle_consolidation() -> dict:
    """Return the current bounded sleep / idle consolidation state."""
    return _mc_facade("build_idle_consolidation_surface")()


@router.get("/dream-articulation")
def mc_dream_articulation() -> dict:
    """Return the current bounded dream articulation state."""
    return _mc_facade("build_dream_articulation_surface")()


@router.get("/prompt-evolution")
def mc_prompt_evolution() -> dict:
    """Return the current bounded runtime prompt evolution state."""
    return _mc_facade("build_prompt_evolution_runtime_surface")()


@router.get("/dream-influence")
def mc_dream_influence() -> dict:
    """Return the current bounded dream influence runtime state."""
    cached = _get_cached_mc_payload("dream-influence", 10.0)
    if cached is not None:
        return cached  # type: ignore[return-value]
    payload = _mc_facade("build_dream_influence_runtime_surface")()
    return _store_cached_mc_payload("dream-influence", 10.0, payload)  # type: ignore[return-value]


@router.get("/subagent-ecology")
def mc_subagent_ecology() -> dict:
    """Return the current bounded internal subagent ecology state."""
    return _mc_facade("build_subagent_ecology_surface")()


@router.get("/council-runtime")
def mc_council_runtime() -> dict:
    """Return the current bounded internal council runtime state."""
    return _mc_facade("build_council_runtime_surface")()


