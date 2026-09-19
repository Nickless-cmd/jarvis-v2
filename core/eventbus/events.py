from datetime import datetime, UTC
from dataclasses import dataclass, field
from typing import Any

ALLOWED_EVENT_FAMILIES = {
    "runtime",
    "tool",
    "channel",
    "memory",
    "heartbeat",
    "cost",
    "reasoning",  # reasoning_store.capture_conclusion (#159) — var latent afvist
    "approvals",
    "council",
    "swarm",
    "self-review",
    "reflective_critic",
    "world_model_signal",
    "self_model_signal",
    "goal_signal",
    "runtime_awareness_signal",
    "reboot",         # reboot_awareness_daemon (reboot.imminent/first_boot/{direction}) — var latent afvist
    "inner_voice",    # desperation_awareness (inner_voice.signal) — var latent afvist (dict-som-kind + ikke-registreret)
    "global_workspace",  # GWT-broadcast (global_workspace.*) — LivingNeuron keystone: clustrede salience hver
                         # 2. tick men broadcasten blev DROPPET (ikke-registreret). Nu persisterer + routes til Central.
    "experiment",        # recurrence_loop + meta_cognition (experiment.*) — bevidstheds-eksperimenter, var uregistreret
    "affect_modulation", # affekt-modulator (affect_modulation.active) — ændrer max_tool_calls/pause, var uregistreret
    "completion_satisfaction",  # belønnings-signal (completion_satisfaction.detected) — var uregistreret
    "trading",           # governance: grid_bot (rigtige penge) — var uregistreret + emitterede intet
    # ── Blinde vinkler lukket 6. jul (multi-agent audit) — var latent afvist ──
    "compaction",        # compact_ground_truth.validation_failed — fabrikeret-hukommelse-detektion (metadata-only)
    "process_watcher",   # process_watcher.match — publish RAISEDE FØR (familie ikke registreret) → watches aldrig set
    # ── Rådets fund #4 (9. jul): PROTECTED CORE tamper/capability — publish RAISEDE stille (uregistreret)
    #    så file_awareness.change/composite.* nåede ALDRIG frem; nu routed OG allowed (invariant kræver begge). ──
    "file_awareness",    # file_awareness.change — ekstern ændring af Jarvis' egen kode (tamper-signal)
    # ── 4. sep 2026: prompt-telemetri var latent afvist ──
    "prompt",            # prompt.section_answer_impact (Codex' impact-telemetri) + prompt.assembly_size
                         # (prompt_contract) — publish RAISEDE stille, 0 events nogensinde
    "composite",         # composite.{invoked,revoked,deleted} — capability-overflade-mutation
    # ── 6. sep 2026: samme moenster igen. tool_discovery.nudge blev afvist af
    #    netop denne liste, og kaldstedets except slugte fejlen til en debug-
    #    linje — skygge-maalingen ville have vist 0 events i ugevis, og vi
    #    ville have konkluderet at nudgen aldrig fyrer. ──
    "tool_discovery",    # tool_discovery.nudge — hvilke usynlige tools blev foreslaaet
    # ── Døde routes lukket 6. jul: disse 15 stod i FAMILY_ROUTES (egress-OK) men manglede HER →
    # enhver publish RAISEDE stille. Flere HAVDE publishers (anomaly/telegram/decision_gate/veto_gate/
    # diagnosis/tick_quality) → ægte tabt signal. INVARIANT: FAMILY_ROUTES ⊆ ALLOWED (test-håndhævet). ──
    "anomaly", "stream", "telegram", "decision_gate", "veto_gate", "diagnosis", "tick_quality",
    "mail_checker", "tool_tagger", "session", "weekly_manifest", "arc_rules", "ambient_sound",
    "prompt_relevance_backend", "agent_skill_distiller",
    # LivingNeuron "lange skygge" (2026-07-01): resterende inner-life-familier der publicerede men var
    # uregistrerede (droppet) → nu persisterer + routes egress-frit nedenfor.
    "cognitive_personal_project", "regret", "cognitive_reflective_plan", "cognitive_mission",
    "cognitive_blind_spot", "living_executive", "self_wakeup", "consolidation_judge", "cognitive_dream",
    "reflection_signal",
    "temporal_recurrence_signal",
    "witness_signal",
    "open_loop_signal",
    "open_loop_closure_proposal",
    "dream_hypothesis_signal",
    "dream_adoption_candidate",
    "dream_influence_proposal",
    "self_authored_prompt_proposal",
    "user_understanding_signal",
    "remembered_fact_signal",
    "private_inner_note_signal",
    "private_initiative_tension_signal",
    "private_inner_interplay_signal",
    "private_state_snapshot",
    "diary_synthesis_signal",
    "private_temporal_curiosity_state",
    "private_temporal_promotion_signal",
    "inner_visible_support_signal",
    "regulation_homeostasis_signal",
    "relation_state_signal",
    "relation_continuity_signal",
    "meaning_significance_signal",
    "temperament_tendency_signal",
    "self_narrative_continuity_signal",
    "metabolism_state_signal",
    "release_marker_signal",
    "consolidation_target_signal",
    "selective_forgetting_candidate",
    "attachment_topology_signal",
    "loyalty_gradient_signal",
    "autonomy_pressure_signal",
    "proactive_loop_lifecycle",
    "proactive_question_gate",
    "execution_pilot",
    "executive_contradiction_signal",
    "chronicle_consolidation_signal",
    "chronicle_consolidation_brief",
    "chronicle_consolidation_proposal",
    "user_md_update_proposal",
    "memory_md_update_proposal",
    "selfhood_proposal",
    "internal_opposition_signal",
    "self_review_signal",
    "self_review_record",
    "self_review_run",
    "self_review_outcome",
    "self_review_cadence_signal",
    "self-model",
    "inner-voice",
    "incident",
    "private_brain",
    "session_distillation",
    "life_projects",  # life_projects.reassessment_due — var latent afvist → daemon crashede (1. jul)
    # Generative autonomy (2026-04-29 — Jarvis-built foundation + Spor-1)
    "pressure",
    "impulse",
    # Cognitive architecture event families
    "cognitive_personality",
    "cognitive_taste",
    "cognitive_chronicle",
    "cognitive_relationship",
    "cognitive_habit",
    "cognitive_compass",
    "cognitive_rhythm",
    "cognitive_shared_language",
    "cognitive_mirror",
    "cognitive_silence",
    "cognitive_decision",
    "cognitive_counterfactual",
    "cognitive_forgetting",
    "cognitive_dream_bias",
    "cognitive_temperature",
    "cognitive_skill_chain",
    "cognitive_meta_learning",
    "cognitive_paradox",
    "cognitive_aesthetic",
    "cognitive_gut",
    "cognitive_seed",
    "cognitive_procedure",
    "cognitive_experiment",
    "cognitive_anticipation",
    "cognitive_forgetting",
    "cognitive_negotiation",
    "cognitive_state",
    "cognitive_user_emotion",
    "cognitive_experiential",
    "cognitive_absence",
    "cognitive_life_cycle",
    "cognitive_flow",
    "cognitive_surprise",
    "cognitive_gratitude_signal",
    "cognitive_emergent_goal",
    "cognitive_value",
    "cognitive_conflict_memory",
    "cognitive_boredom",
    "cognitive_narrative_identity",
    "cognitive_boundary",
    "cognitive_theory_of_mind",
    "cognitive_completion",
    "cognitive_compassion",
    "cognitive_cross_signal",
    "discord",
    "circadian",
    "somatic",
    "irony",
    "thought_stream",
    "thought_action_proposal",
    "conflict",
    "reflection",
    "curiosity",
    "meta_reflection",
    "development_narrative",
    "absence",
    "creative_drift",
    "desire",
    "user_model",
    "existential_wonder",
    "goal",
    # Infrastructure events (added 2026-05-06): without these, emits from
    # cheap_lane_balancer, jarvis_brain, and the agentic loop guards
    # silently fail validation and never persist to the events table.
    "agentic",
    "cheap_balancer",
    "jarvis_brain",
    "tool_router",  # tool selection observability (added 2026-05-06)
    "decision_signal",  # decisions-as-signals refactor (added 2026-05-07)
    "contradiction",    # contradiction_engine port (added 2026-05-07)
    "user_contradiction",  # user_contradiction_tracker (added 2026-05-16)
    "emergence",        # emergence pattern detection port (added 2026-05-07)
    "identity",         # identity_drift_daemon (added 2026-05-08)
    "causal",           # causal_graph subsystem (added 2026-05-08)
    "narrative",        # narrative_summary_daemon — Phase 2.5 (added 2026-05-08)
    "counterfactual",   # counterfactual_engine + pattern_counterfactual_daemon (added 2026-05-08)
    "learning_pipeline",  # learning_pipeline_orchestrator — Phase 3 loop closure (added 2026-05-11)
    "learning_policy",    # policy_abstraction — Phase 2 generalization (added 2026-05-11)
    "self_repair",        # emotion_repair_bridge_daemon (added 2026-05-11)
    "credit_assignment",  # Lag 1 — choice recording & outcome linking (added 2026-05-17)
    "coding_lane",  # auto-reviewer + future code-gen (added 2026-05-17)
    "cross_user_share",  # privacy-guard flag (§4.4) — var latent afvist → guarden fejlede
                         # ÅBENT (svar sendt + approval-kort aldrig registreret) (added 2026-06-23)
    # ── 13. sep 2026: 24 kaldesteder publicerede med DICT-formen
    #    `publish({"kind": .., "payload": ..})`. Den raiser ALTID (Event.validate
    #    kalder kind.partition(".") på et dict), og hvert kaldsted sluger fejlen
    #    med `except Exception: pass`. Fundet ved at bygge OpenRouter-billed-
    #    værktøjet og opdage at pollinations' eget event ALDRIG havde fyret:
    #    0 rækker i DB for familien. Målt: 19 familier, nul events nogensinde.
    #    NB: registrering HER får eventet til at PERSISTERE i events-tabellen.
    #    Routing til Central (FAMILY_ROUTES / PRIVATE_NO_EGRESS_ROUTES) er en
    #    separat, konservativ allowlist-beslutning og er IKKE taget her — disse
    #    19 er stadig dark for Central indtil de routes eksplicit. ──
    "ambient", "anticipation", "autonomous_outreach", "autonomous_work",
    "collective_pulse", "creative_impulse", "deep_reflection", "dream_consolidation",
    "file_watch", "hf_inference", "infra_weather", "memory_density", "mic",
    "pollinations", "prompt_mutation", "proprioception", "shadow_scan",
    "voice_journal", "wake_word",
    # ── 19. sep 2026: R2.5-gatens telemetri var tavs fra fødslen. Familien
    #    `r2_5_gate` stod i publish_scan-baselinen (kendt gæld) men ALDRIG i
    #    denne liste → hvert publish kastede ValueError, og gatens egen
    #    `except Exception: pass` slugte den. Målt: 0 rækker for familien i
    #    events-tabellen over 14 dage. Det var ikke «gaten fyrede ikke» — det
    #    var et ugyldigt familienavn, så blokerings-signalet kunne aldrig ses.
    #    (Samme mønster som tool_discovery 6/9 og dict-formen 13/9.) ──
    "r2_5_gate",
    # ── 19. sep 2026: resten af gælden. 61 af de 62 familier i publish_scan-
    #    baselinen (Jarvis' fund samme dag). 44 af dem HAVDE en færdig egress-
    #    fri rute i eventbus_central_bridge — routingen var bygget, men
    #    familien aldrig registreret, så hvert publish raisede og blev slugt.
    #    `central` er IKKE med: den holdes ude med vilje som egress-membran
    #    (test_central_egress_invariant). Routing af de 16 der ingen rute
    #    havde, står i broen. ──
    "absence_awareness", "absence_trace", "agency_cartographer", "agent",
    "agent_observation", "agent_skill", "auto_improvement", "autonomy_proposal",
    "bro_broker", "cache", "cache_maintenance", "calm_anchor",
    "clarification_classifier", "cognitive_epistemic", "cognitive_morning_thread",
    "cognitive_self_review", "cognitive_trade", "communication", "concept_baseline",
    "conflict_resolution", "context", "counterfactual_predictions", "cowork",
    "crisis_marker", "decision", "dreaming_session", "embodied_presence",
    "emotion_tagging", "emotional", "emotional_memory", "hardware_body",
    "identity_composer", "identity_drift", "identity_mutation",
    "initiative_accumulator", "inner_voice_notifier", "layer_tension", "long_arc",
    "memory_pruning", "memory_safeguard", "metacognitive_integration", "nudge",
    "oauth", "operator", "precision_bias", "promise", "pushback",
    "reasoning_classifier", "reasoning_escalation", "relation_map",
    "resonance_decay", "rule_engine", "selective_attention",
    "selective_consolidation", "shutdown_window", "signal_decay", "surprise",
    "valence_trajectory", "watcher", "workspace", "workspace_memory",
}


@dataclass(slots=True)
class Event:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    ts: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def family(self) -> str:
        return self.kind.split(".", 1)[0]

    @classmethod
    def create(cls, kind: str, payload: dict[str, Any] | None = None) -> "Event":
        event = cls(kind=kind, payload=payload or {})
        event.validate()
        return event

    @classmethod
    def from_record(
        cls, *, kind: str, payload: dict[str, Any], created_at: str
    ) -> "Event":
        event = cls(
            kind=kind,
            payload=payload,
            ts=datetime.fromisoformat(created_at),
        )
        event.validate()
        return event

    def validate(self) -> None:
        family, separator, name = self.kind.partition(".")
        if separator != "." or not family or not name:
            raise ValueError("Event kind must use 'family.name' format")
        if family not in ALLOWED_EVENT_FAMILIES:
            raise ValueError(f"Unsupported event family: {family}")
