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
    "approvals",
    "council",
    "swarm",
    "self-review",
    "reflective_critic",
    "world_model_signal",
    "self_model_signal",
    "goal_signal",
    "runtime_awareness_signal",
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
