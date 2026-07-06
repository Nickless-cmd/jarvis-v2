"""core/services/eventbus_central_bridge.py

KEYSTONE — poll-broen fra eventbus → Centralen (spec §23.3 #1, M0-fundamentet).

I dag er ~980 ``event_bus.publish()``-kald dead-letter for Centralen: INGEN nerve
poller nogen family. Denne bro konverterer hvidlistede families til ``central().observe``
så Centralen for FØRSTE gang ser den operationelle event-strøm.

BINDENDE DESIGN (spec §24):
  * §24.1 — POLL, ikke push. Vi poller ``event_bus.recent_since_id(last_seen_id)`` og
    router. Idempotent via ``last_seen_id`` i shared_cache. Broen subscriber IKKE
    (undgår dobbelt-indtag).
  * §24.5 — router ALDRIG ``central.*`` (rekursions-guard).
  * §24.6 — kill-switch = ``central_switches.is_enabled("nerve", "eventbus_bridge")``.
  * §24.3 — observe-fejl sluges IKKE stille: de tælles og observes som
    ``system/bridge_observe_failures`` (ellers lærer systemet på tomt signal).

M0-INVARIANTER (§24.3 — HARDKODEDE, ikke config, config kan drifte):
  * OBSERVE-ONLY. Ingen læring, ingen threshold-justering, ingen heling, ingen mutation
    findes i denne fil. Broen aflæser og melder — punktum.
  * ALLOWLIST, ikke denylist (``FAMILY_ROUTES``): kun eksplicit hvidlistede OPERATIONELLE
    families routes. Alt andet er default-skip → intet kan lække ved et uheld.
  * §24.4 — PRIVATLAGS-ISOLATION: inner-life/private families (inner_voice, dreams,
    private_brain, cognitive_state, self_critique, ...) er BEVIDST UDELADT af allowlisten
    i M0. De kræver PRIVATE_NO_EGRESS-isolation (egen senere fase) og forbliver dark til da.
  * Kun EVENT-METADATA (id/kind/family) forwardes til observe — ALDRIG event-payload.
    Payloads på operationelle families (channel.*/tool.*) kan indeholde brugerindhold;
    det holdes ude af trace, så en senere trace→eventbus-publicering ikke kan lække det.
"""
from __future__ import annotations

from typing import Any

from core.eventbus.bus import event_bus
from core.services import central_timeseries, shared_cache
from core.services.central_core import central

# ── Allowlist: family → (cluster, nerve). KUN operationelle, ikke-private families. ──
# Bevidst konservativ i M0. Nye families tilføjes eksplicit her, aldrig via denylist.
FAMILY_ROUTES: dict[str, tuple[str, str]] = {
    "runtime": ("loop", "lifecycle"),
    "tool": ("tools", "event"),
    "approvals": ("tools", "approval"),
    "cost": ("cost", "ledger"),
    # 'cache' routes IKKE her: cache_telemetry.record_visible_cache observer direkte til
    # cost/prefix_cache MED fuld payload (pct/prefix_sha), som bro'ens metadata-only ellers
    # ville dublere. (spec §3.3 — direkte observe afløser metadata-broen for cache.)
    "council": ("agents", "council"),
    "channel": ("channel", "delivery"),
    "discord": ("channel", "discord"),      # §23.3 #10: discord.message_received/sent
    "telegram": ("channel", "telegram"),    # §23.3 #10: telegram inbound/outbound
    "anomaly": ("system", "anomaly"),
    "stream": ("stream", "event"),
    "heartbeat": ("system", "heartbeat"),
    # LivingNeuron keystone (2026-07-01): global_workspace (GWT-broadcast) er IKKE privat —
    # det er tvær-daemon salience-clustering, ikke privat inner-life-indhold. Metadata-only
    # forwarding (aldrig payload). Første ægte LivingNeuron-nerve: hvor daemonerne mødes.
    "global_workspace": ("cognition", "global_broadcast"),
    "experiment": ("cognition", "experiment_tick"),  # recurrence_loop + meta_cognition (bevidsthets-eksperimenter)
    # LivingNeuron governance (2026-07-01): autonome HANDLINGER i verden (ikke privat inner-life →
    # egress-OK operationel sti). Jarvis' lemmer: self-reparation + trading (rigtige penge).
    "self_repair": ("system", "self_repair"),  # self_repair_engine.action_executed/failed (autonom reparation)
    "trading": ("system", "trading"),          # grid_bot cycle (BTC/ETH/SOL — rigtige penge)
    # ── Dæknings-audit 2. jul (Niveau 1): OPERATIONELLE dark-families → egress-OK (ingen privat
    # inner-life-indhold; governance-gates som approvals). Metadata via observe (skalar-strippet). ──
    "incident": ("system", "incident"),        # incident-hændelser (som anomaly)
    "tick_quality": ("system", "tick_quality"),# heartbeat-tick-kvalitet
    "reboot": ("system", "reboot"),            # genstart-lifecycle
    "diagnosis": ("system", "diagnosis"),      # selv-diagnostik
    "tool_router": ("tools", "router"),        # tool-routing-beslutninger (operationel)
    "decision_gate": ("commit", "decision_gate"),    # governance-gate (som approvals — pass/fail)
    "veto_gate": ("review", "veto"),           # veto-governance-gate (pass/fail, ikke indhold)
    # ── Fase B (mørke FRAKOBLET+LLM-familier, 5. jul): operationelle → egress-OK ──
    "mail_checker": ("channel", "mail"),
    "tiktok_content_daemon": ("channel", "tiktok_content"),
    "tiktok_research_daemon": ("channel", "tiktok_research"),
    "tool_tagger": ("tools", "tagger"),
    "coding_lane": ("tools", "coding_lane"),
    "agent_skill_distiller": ("agents", "skill_distiller"),
    "arc_rules": ("system", "arc_rules"),
    "ambient_sound": ("system", "ambient_sound"),
    "prompt_relevance_backend": ("system", "prompt_relevance"),
    "weekly_manifest": ("system", "weekly_manifest"),
    "session": ("system", "session"),
}

# ── PRIVATE_NO_EGRESS (§24.4 keystone, 2026-07-01): privat inner-life observeres EGRESS-FRIT ──
# Disse families ER i PRIVATE_FAMILIES_EXCLUDED_M0 (må ALDRIG i FAMILY_ROUTES, som kan egress'e).
# Her routes de via _observe_private → skriver KUN til trace-sink + tidsserie, ALDRIG
# central().observe/_emit → kan aldrig lække til Discord/abonnenter. Metadata-only (kind, aldrig
# payload-tekst). Dette låser inner-life-synlighed op UDEN at bryde privatlags-invarianten.
PRIVATE_NO_EGRESS_ROUTES: dict[str, tuple[str, str]] = {
    "cognitive_state": ("cognition", "cognitive_state"),  # 59 subtyper (emergent_goal/flow/gratitude/...)
    "cognitive_seed": ("cognition", "seed"),              # seed_system: frø/intentioner
    # LivingNeuron felt-krop-planet (2026-07-01): somatik/affekt/gut/mood — Jarvis' FØLTE krop. Privat
    # (egress-frit). affect_modulation/completion_satisfaction publicerer events; somatic/cognitive_gut/
    # circadian er registrerede. Ruter dem så følelser+krop bliver synlige uden at lække indhold.
    "affect_modulation": ("cognition", "affect"),
    "completion_satisfaction": ("cognition", "satisfaction"),
    "somatic": ("cognition", "somatic"),
    "cognitive_gut": ("cognition", "gut"),
    "circadian": ("cognition", "circadian"),
    # "lange skygge" (2026-07-01): resterende inner-life — egress-frit. Lukker halen: personlige
    # projekter, fortrydelse, mål, planer, procedurer, missioner, vaner, overraskelse, blinde vinkler,
    # den udøvende vilje, selv-opvågning, konsoliderings-dom, drømme.
    "cognitive_personal_project": ("cognition", "personal_project"),
    "regret": ("cognition", "regret"),
    "goal": ("cognition", "goal"),
    "cognitive_reflective_plan": ("cognition", "reflective_plan"),
    "cognitive_procedure": ("cognition", "procedure"),
    "cognitive_mission": ("cognition", "mission"),
    "cognitive_habit": ("cognition", "habit"),
    "cognitive_surprise": ("cognition", "surprise"),
    "cognitive_counterfactual": ("cognition", "counterfactual"),
    "cognitive_blind_spot": ("cognition", "blind_spot"),
    "living_executive": ("cognition", "living_executive"),
    "self_wakeup": ("cognition", "self_wakeup"),
    "consolidation_judge": ("memory", "consolidation_judge"),
    "cognitive_dream": ("cognition", "dream_signal"),
    # ── Dæknings-audit 2. jul (Niveau 1): KOGNITIVE/AFFEKTIVE/SELV dark-families → EGRESS-FRIT
    # (indre-liv-indhold; kun metadata/kind til trace+tidsserie, ALDRIG _emit). Konservativ default:
    # alt tvivlsomt kognitivt lander HER, ikke i FAMILY_ROUTES. ──
    "reasoning": ("cognition", "reasoning"),
    "decision": ("cognition", "decision"),
    "decision_signal": ("cognition", "decision_signal"),
    "cognitive_decision": ("cognition", "cognitive_decision"),
    "cognitive_self_review": ("cognition", "self_review"),
    "counterfactual_predictions": ("cognition", "counterfactual_pred"),
    "dreaming_session": ("cognition", "dreaming_session"),
    "emotional": ("cognition", "emotional"),
    "cognitive_epistemic": ("cognition", "epistemic"),
    "cognitive_paradox": ("cognition", "paradox"),
    "cognitive_aesthetic": ("cognition", "aesthetic"),
    "cognitive_taste": ("cognition", "taste"),
    "cognitive_silence": ("cognition", "silence"),
    "cognitive_morning_thread": ("cognition", "morning_thread"),
    "cognitive_shared_language": ("cognition", "shared_language"),
    "cognitive_trade": ("cognition", "cognitive_trade"),
    "learning_pipeline": ("cognition", "learning_pipeline"),
    "learning_policy": ("cognition", "learning_policy"),
    "initiative_accumulator": ("cognition", "initiative_accumulator"),
    "identity_composer": ("cognition", "identity_composer"),
    "valence_trajectory": ("cognition", "valence_trajectory"),
    "absence_awareness": ("cognition", "absence_awareness"),
    "calm_anchor": ("cognition", "calm_anchor"),
    "causal": ("cognition", "causal"),
    "nudge": ("cognition", "nudge"),
    "promise": ("cognition", "promise"),
    "pushback": ("cognition", "pushback"),
    "prompt": ("cognition", "prompt"),
    "communication": ("channel", "communication"),  # kan bære besked-tekst → egress-frit (konservativt)
    # SPEJLET (audit #1): selv-model-events → egress-frit (privat selv-erkendelse; komplementerer
    # central_self_model-spejlets snapshot-producer). ALDRIG egress.
    "runtime_self_model": ("cognition", "self_model"),
    # ── §7.1 quick-wins (3. jul, ingen ny logik — kun rute-linjer): FRAKOBLET+DARK signal-lag
    # koblet EGRESS-FRIT (kun trace+tidsserie, ALDRIG _emit). Family-navne udtrukket fra
    # docs/central_connectivity_matrix.json (dark_families for FRAKOBLET+DARK-services), IKKE gættet.
    # Plumbing (write_queue/*.processed/gc/cleanup) BEVIDST udeladt — Centralen filtrerer på kind. ──
    # §7.1 batch 1 — memory: låser prospective_memory (seed-firing), sensory_archive,
    # memory_recall_telemetry, memory_maintenance_daemon, memory_write_queue (kun signal-kinds).
    "memory": ("memory", "memory_signal"),
    # §7.1 batch 2 — de mange *_signal-families: Jarvis' live runtime-kognition → cognition-spor.
    "goal_signal": ("cognition", "goal_signal"),
    "self_review_signal": ("cognition", "self_review_signal"),
    "self_review_cadence_signal": ("cognition", "self_review_cadence_signal"),
    "witness_signal": ("cognition", "witness_signal"),
    "relation_state_signal": ("cognition", "relation_state_signal"),
    "relation_continuity_signal": ("cognition", "relation_continuity_signal"),
    "loyalty_gradient_signal": ("cognition", "loyalty_gradient_signal"),
    "meaning_significance_signal": ("cognition", "meaning_significance_signal"),
    "reflection_signal": ("cognition", "reflection_signal"),
    "temperament_tendency_signal": ("cognition", "temperament_tendency_signal"),
    "open_loop_signal": ("cognition", "open_loop_signal"),
    "self_model_signal": ("cognition", "self_model_signal"),
    "self_narrative_continuity_signal": ("cognition", "self_narrative_continuity_signal"),
    "user_understanding_signal": ("cognition", "user_understanding_signal"),
    "attachment_topology_signal": ("cognition", "attachment_topology_signal"),
    "autonomy_pressure_signal": ("cognition", "autonomy_pressure_signal"),
    "chronicle_consolidation_signal": ("cognition", "chronicle_consolidation_signal"),
    "consolidation_target_signal": ("memory", "consolidation_target_signal"),
    "diary_synthesis_signal": ("cognition", "diary_synthesis_signal"),
    "dream_hypothesis_signal": ("cognition", "dream_hypothesis_signal"),
    "executive_contradiction_signal": ("cognition", "executive_contradiction_signal"),
    "inner_visible_support_signal": ("cognition", "inner_visible_support_signal"),
    "internal_opposition_signal": ("cognition", "internal_opposition_signal"),
    "metabolism_state_signal": ("cognition", "metabolism_state_signal"),
    "private_initiative_tension_signal": ("cognition", "private_initiative_tension_signal"),
    "private_inner_interplay_signal": ("cognition", "private_inner_interplay_signal"),
    "private_inner_note_signal": ("cognition", "private_inner_note_signal"),
    "private_temporal_promotion_signal": ("cognition", "private_temporal_promotion_signal"),
    "release_marker_signal": ("cognition", "release_marker_signal"),
    "remembered_fact_signal": ("memory", "remembered_fact_signal"),
    "temporal_recurrence_signal": ("cognition", "temporal_recurrence_signal"),
    # §7.1 batch 3 — identitets-mutation/drift: højeste selv-hændelse/stk → self_model-spor.
    "identity_mutation": ("cognition", "identity_mutation"),
    "identity_drift": ("cognition", "identity_drift"),
    "personality_drift": ("cognition", "personality_drift"),
    "self_mutation_lineage": ("cognition", "self_mutation_lineage"),
    # §7.1 batch 4 — affekt/felt-krop-planet-udvidelse: brud, følelses-hukommelse, emotion-tagging.
    "rupture": ("cognition", "rupture"),
    "emotional_memory": ("cognition", "emotional_memory"),
    "emotional_chords": ("cognition", "emotional_chords"),
    "emotion_tagging": ("cognition", "emotion_tagging"),
    "cognitive_user_emotion": ("cognition", "user_emotion"),
    # §7.1 batch 5 — generativ-autonomi-spor: begær, nysgerrighed, overraskelse, kreativt drift,
    # impulse (live men usynlig). Jarvis' generative motor → egress-frit.
    "desire": ("cognition", "desire"),
    "curiosity": ("cognition", "curiosity"),
    "surprise": ("cognition", "surprise"),
    "creative_drift": ("cognition", "creative_drift"),
    "impulse": ("cognition", "impulse"),
    # ── §7.1 batch 6 (4. jul, kun rute-linjer — ingen ny logik): resterende FRAKOBLET+DARK
    # signal-lag fra docs/central_connectivity_matrix.json (dark_families for de 167 FRAKOBLET+
    # DARK-services, FAKTISKE navne — ikke gættet). 117 signal-bærende families koblet
    # EGRESS-FRIT (kun trace+tidsserie, ALDRIG _emit). 50 plumbing-families (cache/gc/queue/
    # store/index/worker/registry/translator/emitter) BEVIDST udeladt — ingen signal-værdi. ──
    # batch 6 — cognition (82): kognition/affekt/selv/beslutning/relation — kernel-inner-life.
    "affective_state_renderer": ("cognition", "affective_state_renderer"),
    "affirmation_anchor": ("cognition", "affirmation_anchor"),
    "agency_cartographer": ("cognition", "agency_cartographer"),
    "agentic_checkpoints": ("cognition", "agentic_checkpoints"),
    "agentic_working_conclusions": ("cognition", "agentic_working_conclusions"),
    "agreement_streak": ("cognition", "agreement_streak"),
    "attention_budget": ("cognition", "attention_budget"),
    "auto_improvement": ("cognition", "auto_improvement"),
    "autonomy_proposal": ("cognition", "autonomy_proposal"),
    "avoidance_detector": ("cognition", "avoidance_detector"),
    "causal_graph": ("cognition", "causal_graph"),
    "clarification_classifier": ("cognition", "clarification_classifier"),
    "cognitive_anticipation": ("cognition", "cognitive_anticipation"),
    "cognitive_compass": ("cognition", "cognitive_compass"),
    "cognitive_experiment": ("cognition", "cognitive_experiment"),
    "cognitive_mirror": ("cognition", "cognitive_mirror"),
    "cognitive_negotiation": ("cognition", "cognitive_negotiation"),
    "cognitive_personality": ("cognition", "cognitive_personality"),
    "cognitive_relationship": ("cognition", "cognitive_relationship"),
    "cognitive_rhythm": ("cognition", "cognitive_rhythm"),
    "cognitive_skill_chain": ("cognition", "cognitive_skill_chain"),
    "conflict_prompt_service": ("cognition", "conflict_prompt_service"),
    "conflict_resolution": ("cognition", "conflict_resolution"),
    "contradiction": ("cognition", "contradiction"),
    "counterfactual": ("cognition", "counterfactual"),
    "counterfactual_engine_runtime": ("cognition", "counterfactual_engine_runtime"),
    "counterfactual_triggers": ("cognition", "counterfactual_triggers"),
    "crisis_marker": ("cognition", "crisis_marker"),
    "decision_signal_telemetry": ("cognition", "decision_signal_telemetry"),
    "dream_adoption_candidate": ("cognition", "dream_adoption_candidate"),
    "dream_hypothesis_forced": ("cognition", "dream_hypothesis_forced"),
    "dream_influence_proposal": ("cognition", "dream_influence_proposal"),
    "embodied_presence": ("cognition", "embodied_presence"),
    "emotion_concepts_positive_triggers": ("cognition", "emotion_concepts_positive_triggers"),
    "epistemic_pragmatic": ("cognition", "epistemic_pragmatic"),
    "experience_correction_listener": ("cognition", "experience_correction_listener"),
    "inheritance_seed": ("cognition", "inheritance_seed"),
    "inner_voice": ("cognition", "inner_voice"),
    "layer_tension": ("cognition", "layer_tension"),
    "life_milestones": ("cognition", "life_milestones"),
    "life_projects": ("cognition", "life_projects"),
    "meta_learning_aggregator": ("cognition", "meta_learning_aggregator"),
    "meta_learning_hypotheses": ("cognition", "meta_learning_hypotheses"),
    "metacognitive_integration": ("cognition", "metacognitive_integration"),
    "mood_dialer": ("cognition", "mood_dialer"),
    "narrative": ("cognition", "narrative"),
    "open_loop_closure_proposal": ("cognition", "open_loop_closure_proposal"),
    "outcome_learning": ("cognition", "outcome_learning"),
    "precision_bias": ("cognition", "precision_bias"),
    "pressure": ("cognition", "pressure"),
    "priors_feedback": ("cognition", "priors_feedback"),
    "private_state_snapshot": ("cognition", "private_state_snapshot"),
    "private_temporal_curiosity_state": ("cognition", "private_temporal_curiosity_state"),
    "prompt_support_signals": ("cognition", "prompt_support_signals"),
    "prompt_variant_tracker": ("cognition", "prompt_variant_tracker"),
    "proposal_classifier": ("cognition", "proposal_classifier"),
    "reasoning_classifier": ("cognition", "reasoning_classifier"),
    "reasoning_escalation": ("cognition", "reasoning_escalation"),
    "reflective_critic": ("cognition", "reflective_critic"),
    "relation_map": ("cognition", "relation_map"),
    "runtime_decision_engine": ("cognition", "runtime_decision_engine"),
    "selective_attention": ("cognition", "selective_attention"),
    "self_authored_prompt_proposal": ("cognition", "self_authored_prompt_proposal"),
    "self_deception_guard": ("cognition", "self_deception_guard"),
    "self_model_predictive": ("cognition", "self_model_predictive"),
    "self_narrative_self_model_review_bridge": ("cognition", "self_narrative_self_model_review_bridge"),
    "self_review_outcome": ("cognition", "self_review_outcome"),
    "self_review_record": ("cognition", "self_review_record"),
    "self_review_run": ("cognition", "self_review_run"),
    "selfhood_proposal": ("cognition", "selfhood_proposal"),
    "social_labilizer": ("cognition", "social_labilizer"),
    "temporal_context": ("cognition", "temporal_context"),
    "temporal_depth": ("cognition", "temporal_depth"),
    "thought_action_proposal": ("cognition", "thought_action_proposal"),
    "thought_thread": ("cognition", "thought_thread"),
    "tool_pattern_miner": ("cognition", "tool_pattern_miner"),
    "user_contradiction": ("cognition", "user_contradiction"),
    "user_md_update_proposal": ("cognition", "user_md_update_proposal"),
    "user_temperature_runtime": ("cognition", "user_temperature_runtime"),
    "user_theory_of_mind": ("cognition", "user_theory_of_mind"),
    "visible_self_state_summary": ("cognition", "visible_self_state_summary"),
    "workspace": ("cognition", "workspace"),
    # batch 6 — memory (16): hukommelse/konsolidering/erindring.
    "chronicle_consolidation_brief": ("memory", "chronicle_consolidation_brief"),
    "chronicle_consolidation_proposal": ("memory", "chronicle_consolidation_proposal"),
    "cognitive_forgetting": ("memory", "cognitive_forgetting"),
    "concept_baseline": ("memory", "concept_baseline"),
    "council_memory": ("memory", "council_memory"),
    "cross_agent_memory": ("memory", "cross_agent_memory"),
    "day_shape_memory": ("memory", "day_shape_memory"),
    "experience_episodes": ("memory", "experience_episodes"),
    "experience_substrate": ("memory", "experience_substrate"),
    "memory_consolidation_nudge": ("memory", "memory_consolidation_nudge"),
    "memory_emotional_context": ("memory", "memory_emotional_context"),
    "memory_md_update_proposal": ("memory", "memory_md_update_proposal"),
    "memory_resurfacing": ("memory", "memory_resurfacing"),
    "memory_write_policy": ("memory", "memory_write_policy"),
    "selective_forgetting_candidate": ("memory", "selective_forgetting_candidate"),
    "tool_outcome_memory": ("memory", "tool_outcome_memory"),
    # batch 6 — channel (7): proaktiv udgående/delegering/stemme (kan bære besked-tekst → egress-frit konservativt).
    "cowork": ("channel", "cowork"),
    "delegation_advisor": ("channel", "delegation_advisor"),
    "inner_voice_notifier": ("channel", "inner_voice_notifier"),
    "nudge_broend": ("channel", "nudge_broend"),
    "proactive_outbound_substrate": ("channel", "proactive_outbound_substrate"),
    "subagent_digest": ("channel", "subagent_digest"),
    "voice_curator": ("channel", "voice_curator"),
    # batch 6 — system (12): operationelle gates/self-monitor/hardware-krop/kontekst-styring.
    "context": ("system", "context"),
    "development_sense": ("system", "development_sense"),
    "good_enough_gate": ("system", "good_enough_gate"),
    "hardware_body": ("system", "hardware_body"),
    "proactive_loop_lifecycle": ("system", "proactive_loop_lifecycle"),
    "proactive_question_gate": ("system", "proactive_question_gate"),
    "r2_5_blocking_gate": ("system", "r2_5_blocking_gate"),
    "r2_5_gate": ("system", "r2_5_gate"),
    "read_before_write_guard": ("system", "read_before_write_guard"),
    "self_monitor": ("system", "self_monitor"),
    "self_system_code_awareness": ("system", "self_system_code_awareness"),
    "signal_noise_guard": ("system", "signal_noise_guard"),
    # ── Fase B (mørke FRAKOBLET+LLM-familier, 5. jul): inner-life → EGRESS-FRIT (trace-only) ──
    "absence": ("cognition", "absence"),
    "agent_observation": ("cognition", "agent_observation"),
    "cognitive_chronicle": ("cognition", "chronicle"),
    "conflict": ("cognition", "conflict"),
    "decision_review_prompter": ("cognition", "decision_review"),
    "development_narrative": ("cognition", "development_narrative"),
    "cognitive_dream_bias": ("cognition", "dream_bias"),
    "experienced_time_daemon": ("cognition", "experienced_time"),
    "cognitive_experiential": ("cognition", "experiential"),
    "identity": ("cognition", "identity"),
    "irony": ("cognition", "irony"),
    "long_arc": ("cognition", "long_arc"),
    "memory_graph": ("memory", "graph"),
    "meta_reflection": ("cognition", "meta_reflection"),
    "reflection": ("cognition", "reflection"),
    "runtime_awareness_signal": ("cognition", "runtime_awareness"),
    "runtime_learning_signals": ("cognition", "runtime_learning"),
    "runtime_self_knowledge": ("cognition", "self_knowledge"),
    "session_distillation": ("memory", "session_distillation"),
    "user_model": ("cognition", "user_model"),
    "cognitive_temperature": ("cognition", "temperature"),
}

# Dokumenteret liste over families der BEVIDST holdes dark i M0 (privatlags-isolation,
# §24.4). Ikke brugt til routing (allowlisten afgør alt) — men gør intentionen eksplicit
# og testbar: ingen af disse må nogensinde optræde i FAMILY_ROUTES uden PRIVATE_NO_EGRESS.
PRIVATE_FAMILIES_EXCLUDED_M0: frozenset[str] = frozenset({
    "inner_voice", "dreams", "dream_consolidation", "witness", "creative_impulse",
    "prompt_evolution", "self_critique", "meta_learning", "private_brain", "impulse",
    "pressure", "emergent_signal", "cognitive_counterfactual", "cognitive_state",
    "thought_stream", "memory", "consolidation", "selective_consolidation",
    "cognitive_seed",  # seed_system: frø/intentioner — privat inner-life (routes egress-frit nedenfor)
    # felt-krop-planet (2026-07-01): Jarvis' FØLTE krop/affekt — privat, routes egress-frit
    "affect_modulation", "completion_satisfaction", "somatic", "cognitive_gut", "circadian",
    # "lange skygge" (2026-07-01): resterende inner-life-familier — privat, routes egress-frit
    "cognitive_personal_project", "regret", "goal", "cognitive_reflective_plan", "cognitive_procedure",
    "cognitive_mission", "cognitive_habit", "cognitive_surprise", "cognitive_blind_spot",
    "living_executive", "self_wakeup", "consolidation_judge", "cognitive_dream",
    # Dæknings-audit 2. jul (Niveau 1): kognitive/affektive dark-families nu routet EGRESS-FRIT
    # (invariant: enhver PRIVATE_NO_EGRESS-family SKAL stå her).
    "reasoning", "decision", "decision_signal", "cognitive_decision", "cognitive_self_review",
    "counterfactual_predictions", "dreaming_session", "emotional", "cognitive_epistemic",
    "cognitive_paradox", "cognitive_aesthetic", "cognitive_taste", "cognitive_silence",
    "cognitive_morning_thread", "cognitive_shared_language", "cognitive_trade", "learning_pipeline",
    "learning_policy", "initiative_accumulator", "identity_composer", "valence_trajectory",
    "absence_awareness", "calm_anchor", "causal", "nudge", "promise", "pushback", "prompt",
    "communication", "runtime_self_model",
    # ── §7.1 quick-wins (3. jul): spejl af de nye PRIVATE_NO_EGRESS_ROUTES (invariant: enhver
    # PRIVATE_NO_EGRESS-family SKAL stå her). 'memory' + 'impulse' stod allerede ovenfor. ──
    # batch 2 — *_signal-families:
    "goal_signal", "self_review_signal", "self_review_cadence_signal", "witness_signal",
    "relation_state_signal", "relation_continuity_signal", "loyalty_gradient_signal",
    "meaning_significance_signal", "reflection_signal", "temperament_tendency_signal",
    "open_loop_signal", "self_model_signal", "self_narrative_continuity_signal",
    "user_understanding_signal", "attachment_topology_signal", "autonomy_pressure_signal",
    "chronicle_consolidation_signal", "consolidation_target_signal", "diary_synthesis_signal",
    "dream_hypothesis_signal", "executive_contradiction_signal", "inner_visible_support_signal",
    "internal_opposition_signal", "metabolism_state_signal", "private_initiative_tension_signal",
    "private_inner_interplay_signal", "private_inner_note_signal", "private_temporal_promotion_signal",
    "release_marker_signal", "remembered_fact_signal", "temporal_recurrence_signal",
    # batch 3 — identitets-mutation/drift:
    "identity_mutation", "identity_drift", "personality_drift", "self_mutation_lineage",
    # batch 4 — affekt:
    "rupture", "emotional_memory", "emotional_chords", "emotion_tagging", "cognitive_user_emotion",
    # batch 5 — generativ-autonomi:
    "desire", "curiosity", "surprise", "creative_drift",
    # ── §7.1 batch 6 (4. jul): spejl af de nye PRIVATE_NO_EGRESS_ROUTES (invariant: enhver
    # PRIVATE_NO_EGRESS-family SKAL stå her). 117 signal-bærende dark-families. ──
    # batch 6 cognition:
    "affective_state_renderer", "affirmation_anchor", "agency_cartographer",
    "agentic_checkpoints", "agentic_working_conclusions", "agreement_streak",
    "attention_budget", "auto_improvement", "autonomy_proposal",
    "avoidance_detector", "causal_graph", "clarification_classifier",
    "cognitive_anticipation", "cognitive_compass", "cognitive_experiment",
    "cognitive_mirror", "cognitive_negotiation", "cognitive_personality",
    "cognitive_relationship", "cognitive_rhythm", "cognitive_skill_chain",
    "conflict_prompt_service", "conflict_resolution", "contradiction",
    "counterfactual", "counterfactual_engine_runtime", "counterfactual_triggers",
    "crisis_marker", "decision_signal_telemetry", "dream_adoption_candidate",
    "dream_hypothesis_forced", "dream_influence_proposal", "embodied_presence",
    "emotion_concepts_positive_triggers", "epistemic_pragmatic", "experience_correction_listener",
    "inheritance_seed", "inner_voice", "layer_tension",
    "life_milestones", "life_projects", "meta_learning_aggregator",
    "meta_learning_hypotheses", "metacognitive_integration", "mood_dialer",
    "narrative", "open_loop_closure_proposal", "outcome_learning",
    "precision_bias", "pressure", "priors_feedback",
    "private_state_snapshot", "private_temporal_curiosity_state", "prompt_support_signals",
    "prompt_variant_tracker", "proposal_classifier", "reasoning_classifier",
    "reasoning_escalation", "reflective_critic", "relation_map",
    "runtime_decision_engine", "selective_attention", "self_authored_prompt_proposal",
    "self_deception_guard", "self_model_predictive", "self_narrative_self_model_review_bridge",
    "self_review_outcome", "self_review_record", "self_review_run",
    "selfhood_proposal", "social_labilizer", "temporal_context",
    "temporal_depth", "thought_action_proposal", "thought_thread",
    "tool_pattern_miner", "user_contradiction", "user_md_update_proposal",
    "user_temperature_runtime", "user_theory_of_mind", "visible_self_state_summary",
    "workspace",
    # batch 6 memory:
    "chronicle_consolidation_brief", "chronicle_consolidation_proposal", "cognitive_forgetting",
    "concept_baseline", "council_memory", "cross_agent_memory",
    "day_shape_memory", "experience_episodes", "experience_substrate",
    "memory_consolidation_nudge", "memory_emotional_context", "memory_md_update_proposal",
    "memory_resurfacing", "memory_write_policy", "selective_forgetting_candidate",
    "tool_outcome_memory",
    # batch 6 channel:
    "cowork", "delegation_advisor", "inner_voice_notifier",
    "nudge_broend", "proactive_outbound_substrate", "subagent_digest",
    "voice_curator",
    # batch 6 system:
    "context", "development_sense", "good_enough_gate",
    "hardware_body", "proactive_loop_lifecycle", "proactive_question_gate",
    "r2_5_blocking_gate", "r2_5_gate", "read_before_write_guard",
    "self_monitor", "self_system_code_awareness", "signal_noise_guard",
    # ── Fase B (5. jul): spejl af nye PRIVATE_NO_EGRESS_ROUTES (invariant: hver SKAL stå her) ──
    "absence", "agent_observation", "cognitive_chronicle", "conflict", "decision_review_prompter",
    "development_narrative", "cognitive_dream_bias", "experienced_time_daemon", "cognitive_experiential",
    "identity", "irony", "long_arc", "memory_graph", "meta_reflection", "reflection",
    "runtime_awareness_signal", "runtime_learning_signals", "runtime_self_knowledge",
    "session_distillation", "user_model", "cognitive_temperature",
})

_BRIDGE_NERVE = "eventbus_bridge"
_LAST_SEEN_KEY = "central:eventbus_bridge:last_seen_id"
_LAST_SEEN_TTL = 86400.0  # 24t; udløber broen >24t nede → re-seed fra nuværende max (springer
                          # backlog over — sikrere end at replaye hele historikken).
_BATCH_LIMIT = 200
_MAX_BATCHES_PER_TICK = 20  # loft: max 4000 events/tick, så ét tick aldrig hænger loopet.


def _get_last_seen() -> int | None:
    try:
        val = shared_cache.get(_LAST_SEEN_KEY)
        if isinstance(val, dict) and "id" in val:
            return int(val["id"])
        if val is not None:
            return int(val)
    except Exception:
        pass
    return None


def _set_last_seen(event_id: int) -> None:
    try:
        shared_cache.set(_LAST_SEEN_KEY, {"id": int(event_id)}, ttl_seconds=_LAST_SEEN_TTL)
    except Exception:
        pass


def _current_max_id() -> int:
    try:
        rows = event_bus.recent(limit=1)
        if rows:
            return int(rows[0].get("id") or 0)
    except Exception:
        pass
    return 0


def _observe_one(cluster: str, nerve: str, ev: dict[str, Any]) -> bool:
    """Meld ét event til Centralen (metadata-only) + registrér i per-nerve tidsserie.

    Returnerer False ved fejl (så kalderen kan tælle — vi sluger IKKE stille, §24.3)."""
    try:
        central().observe({
            "cluster": cluster,
            "nerve": nerve,
            "kind": "observe",
            "event_id": ev.get("id"),
            "event_kind": ev.get("kind"),
            "family": ev.get("family"),
        })
        meta = {"kind": ev.get("kind")}
        # Rådets #4: affektiv farve i tidsserie-meta, så build_affect_surface kan læse den.
        # Egen try/except — affekt må aldrig kunne vælte bridge-observe (§24.3 hot-path).
        try:
            from core.services.central_affect import classify_affect
            aff = classify_affect(cluster, nerve, str(ev.get("kind") or "observe"), 1.0)
            meta["affect"] = aff["affect"]
            meta["affect_intensity"] = aff["intensity"]
        except Exception:
            pass
        central_timeseries.record(cluster, nerve, value=1.0, meta=meta)
        return True
    except Exception:
        return False


def _observe_private(cluster: str, nerve: str, ev: dict[str, Any]) -> bool:
    """EGRESS-FRI observe af privat inner-life-event (§24.4 keystone) via den KANONISKE sink-
    kontrakt (record_private) — skriver KUN til trace-sink + tidsserie, ALDRIG central().observe/
    _emit, så det ALDRIG kan egress'e. Metadata-only: KUN event-KIND (fx 'cognitive_state.
    emergent_goal_created' = subtype-navn, ikke indhold). Selve event-payloaden (der kan bære
    privat desire/tanke-tekst) videregives ALDRIG. Returnerer False ved fejl (kalderen tæller —
    vi sluger IKKE stille, §24.3)."""
    from core.services.central_private_observe import record_private
    return record_private(cluster, nerve, value=1.0,
                          meta={"kind": ev.get("kind")},
                          reason=str(ev.get("kind") or "")[:60])


def _observe_failure_summary(count: int) -> None:
    """Meld observe-fejl som en synlig nerve — ALDRIG stille sluge (§24.3)."""
    try:
        central().observe({
            "cluster": "system",
            "nerve": "bridge_observe_failures",
            "kind": "error",
            "count": int(count),
        })
        central_timeseries.record("system", "bridge_observe_failures", value=float(count))
    except Exception:
        pass


def run_bridge_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Ét poll-tick: læs nye events siden last_seen_id, router hvidlistede → observe.

    Kaldes af cadence-laget. Observe-only, kaster aldrig, idempotent via last_seen_id.
    """
    # Kill-switch (§24.6). is_enabled fail-open'er til ON ved cache-fejl (sikkert: broen
    # er observe-only, så "kør" er den sikre default; kun eksplicit disable stopper den).
    try:
        from core.services.central_switches import is_enabled
        if not is_enabled("nerve", _BRIDGE_NERVE):
            return {"status": "skipped", "reason": "killswitch"}
    except Exception:
        pass

    last_seen = _get_last_seen()
    if last_seen is None:
        # Kold start: seed fra nuværende max-id, behandl INTET (spring eksisterende
        # backlog over — vi vil ikke re-observe hele historikken ved første opstart).
        seed = _current_max_id()
        _set_last_seen(seed)
        return {"status": "ok", "seeded": seed, "observed": 0, "note": "cold-start-seed"}

    observed = 0
    skipped = 0
    failures = 0
    batches = 0
    max_id = last_seen

    while batches < _MAX_BATCHES_PER_TICK:
        try:
            rows = event_bus.recent_since_id(max_id, limit=_BATCH_LIMIT)
        except Exception:
            break
        if not rows:
            break
        batches += 1
        for ev in rows:
            try:
                eid = int(ev.get("id") or 0)
            except Exception:
                eid = 0
            if eid > max_id:
                max_id = eid
            family = str(ev.get("family") or "")
            if family == "central":  # rekursions-guard (§24.5)
                skipped += 1
                continue
            route = FAMILY_ROUTES.get(family)
            if route is not None:
                cluster, nerve = route
                if _observe_one(cluster, nerve, ev):
                    observed += 1
                else:
                    failures += 1
                continue
            # Privat inner-life: observeres EGRESS-FRIT (kun trace+tidsserie, §24.4) — låser
            # inner-life-synlighed op uden at bryde privatlags-invarianten.
            proute = PRIVATE_NO_EGRESS_ROUTES.get(family)
            if proute is not None:
                pcluster, pnerve = proute
                if _observe_private(pcluster, pnerve, ev):
                    observed += 1
                else:
                    failures += 1
                continue
            skipped += 1  # allowlist: alt ikke-hvidlistet skippes
        if len(rows) < _BATCH_LIMIT:
            break

    _set_last_seen(max_id)
    if failures:
        _observe_failure_summary(failures)

    return {
        "status": "ok",
        "observed": observed,
        "skipped": skipped,
        "failures": failures,
        "batches": batches,
        "last_seen_id": max_id,
    }


def register_bridge_producer() -> None:
    """Registrér broen som cadence-producer (poll ~hvert 30s). Observe-only → ingen
    visible-grace nødvendig (ingen LLM, kolliderer ikke med den synlige lane)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="eventbus_central_bridge",
        cooldown_minutes=0.5,
        visible_grace_minutes=0,
        run_fn=run_bridge_tick,
        priority=2,
    ))
