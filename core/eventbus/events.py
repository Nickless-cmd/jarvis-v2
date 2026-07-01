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
