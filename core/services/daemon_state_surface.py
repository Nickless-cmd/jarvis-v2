"""Samlet flade for daemon- og runtime-lagene — de build_*_surface ingen indgang havde.

MAALT 7/11-2026 paa tvaers af HELE repoet: 464 ``build_*_surface`` i core/services.
181 var synlige gennem de seks foerste indgange (/central/mind?s=state,
/central/memory-state, /central/infra-state, /central/inner-state,
/central/relation-state, /central/self-state). 283 var usynlige for operatoeren.

De 105 her er resten efter at central/selv/droem/privat-bunken blev taget
saerskilt. Det er de lag der KOERER: daemoner, rytmer, signal-tracking,
refleksions-cyklusser, vane- og maal-maskineri, værktojs-routing, sansning.

Grupperet efter hvad laget GOER, ikke efter mappenavn: en fil i ``core/services/``
siger hvor koden bor, ikke hvad den tilhoerer.

Bemaerk om ``active``: en flade der svarer ``active=False`` med en grund er ikke
doed — den melder at der intet er at vise. Derfor skelner denne aggregator mellem
``svarer`` (returnerede en ikke-tom dict) og ``active`` (indholdets eget svar).

UDELADT efter maaling: ``relational_warmth.build_relational_warmth_surface``
kaster ``NoUserContextError`` uden bruger-kontekst (samme fejlform som
``memory_write_policy`` og ``relation_dynamics``). Den tvinges ikke ind.
"""
from __future__ import annotations

import importlib
from typing import Any

#: Gruppe → (navn, modul, funktion). Alle maalt 7/11-2026: nul paakraevede
#: argumenter, dict-svar, nul fejl, nul tomme. Ingen LLM-kald.
_GROUPS: dict[str, list[tuple[str, str, str]]] = {
    # Hvad der koerer af sig selv — daemoner, rytmer, kadence, hvile.
    "daemoner": [
        ("action_router", "core.services.action_router", "build_action_router_surface"),
        ("active_sensing", "core.services.active_sensing_daemon", "build_active_sensing_surface"),
        ("anticipatory_action", "core.services.anticipatory_action_daemon", "build_anticipatory_action_surface"),
        ("autonomous_outreach", "core.services.autonomous_outreach_daemon", "build_autonomous_outreach_surface"),
        ("autonomous_work", "core.services.autonomous_work_daemon", "build_autonomous_work_surface"),
        ("code_aesthetic", "core.services.code_aesthetic_daemon", "build_code_aesthetic_surface"),
        ("collective_pulse", "core.services.collective_pulse_daemon", "build_collective_pulse_surface"),
        ("conflict", "core.services.conflict_daemon", "build_conflict_surface"),
        ("development_narrative", "core.services.development_narrative_daemon", "build_development_narrative_surface"),
        ("experienced_time", "core.services.experienced_time_daemon", "build_experienced_time_surface"),
        ("identity_drift", "core.services.identity_drift_daemon", "build_identity_drift_surface"),
        ("infra_weather", "core.services.infra_weather_daemon", "build_infra_weather_surface"),
        ("reboot_awareness", "core.services.reboot_awareness_daemon", "build_reboot_awareness_surface"),
        ("recurrence", "core.services.recurrence_loop_daemon", "build_recurrence_surface"),
        ("reflection_cycle", "core.services.reflection_cycle_daemon", "build_reflection_surface"),
        ("shadow_scan", "core.services.shadow_scan_daemon", "build_shadow_scan_surface"),
        ("signal_decay", "core.services.signal_decay_daemon", "build_signal_decay_surface"),
        ("somatic", "core.services.somatic_daemon", "build_body_state_surface"),
        ("surprise", "core.services.surprise_daemon", "build_surprise_surface"),
        ("thought_stream", "core.services.thought_stream_daemon", "build_thought_stream_surface"),
        ("voice", "core.services.voice_daemon", "build_voice_daemon_surface"),
        ("indre_puls", "core.services.indre_puls", "build_indre_puls_surface"),
        ("rhythm_engine", "core.services.rhythm_engine", "build_rhythm_surface"),
        ("conversation_rhythm", "core.services.conversation_rhythm", "build_conversation_rhythm_surface"),
    ],
    # Hvad jeg har laert og hvordan det former naeste skridt.
    "laering": [
        ("adaptive_learning", "core.services.adaptive_learning_runtime", "build_adaptive_learning_runtime_surface"),
        ("adaptive_planner", "core.services.adaptive_planner_runtime", "build_adaptive_planner_runtime_surface"),
        ("adaptive_reasoning", "core.services.adaptive_reasoning_runtime", "build_adaptive_reasoning_runtime_surface"),
        ("outcome_learning", "core.services.outcome_learning", "build_outcome_learning_surface"),
        ("habit_tracker", "core.services.habit_tracker", "build_habit_surface"),
        ("spaced_repetition", "core.services.spaced_repetition", "build_spaced_repetition_surface"),
        ("interlanguage_practice", "core.services.interlanguage_practice", "build_interlanguage_practice_surface"),
        ("procedure_bank", "core.services.procedure_bank", "build_procedure_surface"),
        ("skill_engine", "core.services.skill_engine", "build_skill_engine_surface"),
        ("seed_system", "core.services.seed_system", "build_seed_surface"),
        ("value_formation", "core.services.value_formation", "build_formed_values_surface"),
        ("identity_canon", "core.services.identity_canon", "build_identity_canon_surface"),
        ("compass_engine", "core.services.compass_engine", "build_compass_surface"),
        ("rule_engine", "core.services.rule_engine", "build_rule_engine_surface"),
        ("automation_dsl", "core.services.automation_dsl", "build_automation_dsl_surface"),
    ],
    # Hvad der holder mig sammen over tid — hukommelse, kontinuitet, historie.
    "kontinuitet": [
        ("chronicle_engine", "core.services.chronicle_engine", "build_chronicle_surface"),
        ("continuity_kernel", "core.services.continuity_kernel", "build_continuity_kernel_surface"),
        ("session_continuity", "core.services.session_continuity", "build_session_continuity_surface"),
        ("experiential_memory", "core.services.experiential_memory", "build_experiential_memory_surface"),
        ("body_memory", "core.services.body_memory", "build_body_memory_surface"),
        ("cognitive_episodes", "core.services.cognitive_episodes", "build_cognitive_episode_surface"),
        ("decision_log", "core.services.decision_log", "build_decision_log_surface"),
        ("decisions_journal", "core.services.decisions_journal", "build_decisions_journal_surface"),
        ("autonomous_history", "core.services.autonomous_sessions", "build_autonomous_history_surface"),
        ("jarvis_brain_reflection", "core.services.jarvis_brain_reflection", "build_jarvis_brain_reflection_surface"),
        ("semantic_indexer", "core.services.semantic_indexer", "build_semantic_indexer_surface"),
        ("idle_consolidation", "core.services.idle_consolidation", "build_idle_consolidation_surface"),
    ],
    # Hvad der taenker videre naar jeg ikke er i en samtale.
    "taenkning": [
        ("idle_thinking", "core.services.idle_thinking", "build_idle_thinking_surface"),
        ("deep_analyzer", "core.services.deep_analyzer", "build_deep_analyzer_surface"),
        ("deep_reflection", "core.services.deep_reflection_slot", "build_deep_reflection_surface"),
        ("reasoning_interceptor", "core.services.reasoning_interceptor", "build_reasoning_interceptor_surface"),
        ("counterfactual", "core.services.counterfactual_self_simulation", "build_counterfactual_surface"),
        ("theory_of_mind", "core.services.theory_of_mind_engine", "build_theory_of_mind_surface"),
        ("epistemics", "core.services.epistemics", "build_epistemics_surface"),
        ("apophenia_guard", "core.services.apophenia_guard", "build_apophenia_guard_surface"),
        ("source_confidence", "core.services.source_confidence_gate", "build_source_confidence_surface"),
        ("contradiction_engine", "core.services.contradiction_engine", "build_contradiction_engine_surface"),
        ("contradiction_resolver", "core.services.contradiction_resolver", "build_contradiction_resolver_surface"),
        ("paradox_tracker", "core.services.paradox_tracker", "build_paradox_surface"),
        ("cross_signal_analysis", "core.services.cross_signal_analysis", "build_cross_signal_analysis_surface"),
        ("causal_graph", "core.services.causal_graph", "build_causal_graph_surface"),
        ("emergence", "core.services.emergence", "build_emergence_surface"),
        ("emergent_bridge", "core.services.emergent_bridge", "build_emergent_bridge_surface"),
        ("emergent_goals", "core.services.emergent_goals", "build_emergent_goals_surface"),
        ("reflection_to_plan", "core.services.reflection_to_plan", "build_reflection_to_plan_surface"),
        ("regret_engine", "core.services.regret_engine", "build_regret_engine_surface"),
        ("rupture_repair", "core.services.rupture_repair", "build_rupture_repair_surface"),
        ("desperation_awareness", "core.services.desperation_awareness", "build_desperation_awareness_surface"),
        ("boundary_awareness", "core.services.boundary_awareness", "build_boundary_awareness_surface"),
        ("developmental_valence", "core.services.developmental_valence", "build_developmental_valence_surface"),
        ("affective_meta_state", "core.services.affective_meta_state", "build_affective_meta_state_surface"),
        ("emotional_controls", "core.services.emotional_controls", "build_emotional_controls_surface"),
        ("flow_state", "core.services.flow_state_detection", "build_flow_state_surface"),
        ("sustained_attention", "core.services.sustained_attention", "build_sustained_attention_surface"),
        ("attention_contour", "core.services.attention_contour", "build_attention_contour_surface"),
        ("text_resonance", "core.services.text_resonance", "build_text_resonance_surface"),
        ("shared_language", "core.services.shared_language", "build_shared_language_surface"),
        ("relationship_texture", "core.services.relationship_texture", "build_relationship_texture_surface"),
        ("unconscious_temperature_field", "core.services.unconscious_temperature_field", "build_unconscious_temperature_field_surface"),
        ("gut_engine", "core.services.gut_engine", "build_gut_surface"),
        ("embodied_state", "core.services.embodied_state", "build_embodied_state_surface"),
        ("somatic_body", "core.services.somatic_runtime_body", "build_somatic_body_surface"),
        ("agency_map", "core.services.agency_map", "build_agency_map_surface"),
        ("personal_project", "core.services.personal_project", "build_personal_project_surface"),
        ("initiative_accumulator", "core.services.initiative_accumulator", "build_initiative_accumulator_surface"),
        ("autonomy_proposal", "core.services.autonomy_proposal_queue", "build_autonomy_proposal_surface"),
        ("proactivity_bridge", "core.services.proactivity_bridge", "build_proactivity_bridge_surface"),
        ("anticipatory_context", "core.services.anticipatory_context", "build_anticipatory_context_surface"),
        ("ghost_networks", "core.services.ghost_networks", "build_ghost_networks_surface"),
        ("subagent_ecology", "core.services.subagent_ecology", "build_subagent_ecology_surface"),
        ("council_runtime", "core.services.council_runtime", "build_council_runtime_surface"),
        ("jobs_engine", "core.services.jobs_engine", "build_jobs_engine_surface"),
        ("system_cartographer", "core.services.system_cartographer", "build_system_cartographer_surface"),
        ("theater_audit", "core.services.theater_audit", "build_theater_audit_surface"),
        ("error_healers", "core.services.error_healers", "build_healer_surface"),
        ("provider_health", "core.services.provider_health_check", "build_provider_health_surface"),
        ("tool_router", "core.services.tool_router", "build_tool_router_surface"),
        ("permission_classifier", "core.services.permission_classifier", "build_permission_classifier_surface"),
        ("silence_detector", "core.services.silence_detector", "build_silence_surface"),
        ("silence_listener", "core.services.silence_listener", "build_silence_listener_surface"),
        ("silence_patterns", "core.services.silence_patterns", "build_silence_patterns_surface"),
    ],
}


def producer_names() -> list[str]:
    """Navnene i kald-raekkefoelge, paa tvaers af grupperne — til test."""
    return [name for group in _GROUPS.values() for (name, _mod, _fn) in group]


def group_names() -> list[str]:
    """Gruppe-navnene i definitions-raekkefoelge."""
    return list(_GROUPS)


def _call(name: str, mod_path: str, fn_attr: str) -> dict[str, Any]:
    """Kald én producent. En defekt maa ikke skjule de oevrige."""
    try:
        module = importlib.import_module(mod_path)
        surface = getattr(module, fn_attr)()
        if not isinstance(surface, dict):
            return {"active": False, "reason": f"returnerede {type(surface).__name__}, ikke dict"}
        if not surface:
            return {"active": False, "reason": "returnerede en tom dict"}
        return surface
    except Exception as exc:  # én defekt producent må ikke skjule de øvrige
        return {"active": False, "reason": f"{type(exc).__name__}: {exc}"[:200]}


def build_daemon_state_surface() -> dict[str, Any]:
    """Kald alle producenter og returnér deres egne signaler, grupperet. Kaster ALDRIG.

    ``svarer`` er flader der returnerede indhold. ``active`` er de flader der
    selv melder ``active=True`` — forskellen er ikke en fejl: en flade kan svare
    aerligt at der intet er lige nu.
    """
    groups: dict[str, dict[str, Any]] = {}
    svarer: list[str] = []
    aktive: list[str] = []
    taxse: list[str] = []

    for group, producers in _GROUPS.items():
        indhold: dict[str, Any] = {}
        for name, mod_path, fn_attr in producers:
            surface = _call(name, mod_path, fn_attr)
            indhold[name] = surface
            if "reason" in surface and not surface.get("active"):
                # Fejlede eller svarede tomt — men kun hvis den ikke selv
                # melder en grund som en DEL af et ellers gyldigt svar.
                if len(surface) <= 2:
                    taxse.append(name)
                    continue
            svarer.append(name)
            if surface.get("active") is True:
                aktive.append(name)
        groups[group] = {
            "surfaces": indhold,
            "count": len(indhold),
            "svarer": [n for n in indhold if n in svarer],
        }

    return {
        "mode": "daemon-state-v1",
        "groups": groups,
        "svarer": svarer,
        "active": aktive,
        "taxse": taxse,
        "summary": (
            f"{len(svarer)}/{len(producer_names())} daemon- og runtime-lag svarer "
            f"({len(aktive)} melder aktivt indhold)"
            + (f"; taxse: {', '.join(taxse)}" if taxse else "")
        ),
    }
