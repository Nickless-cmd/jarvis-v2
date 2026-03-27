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
    "user_md_update_proposal",
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
