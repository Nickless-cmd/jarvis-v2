"""Request-scoped research instructions consumed by prompt assembly surfaces."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from core.services.research_contract import ResearchPolicy


@dataclass(frozen=True)
class _PromptResearch:
    policy: ResearchPolicy
    skill_instructions: str
    evidence: str


_ACTIVE: ContextVar[_PromptResearch | None] = ContextVar("research_prompt_context", default=None)


@contextmanager
def research_context(
    policy: ResearchPolicy,
    *,
    skill_instructions: str = "",
    evidence: str = "",
):
    token = _ACTIVE.set(_PromptResearch(policy, skill_instructions.strip(), evidence.strip()))
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def research_prompt_section() -> str:
    active = _ACTIVE.get()
    if active is None:
        return ""
    policy = active.policy
    lines = [
        "[RESEARCH CONTRACT]",
        "Research mode was explicitly selected by the user.",
        f"Source target: {policy.source_target}; tool-call budget: {policy.max_tool_calls}; "
        f"wall time: {policy.wall_time_seconds}s.",
        "Use structured web results as evidence. Prefer primary, authoritative, directly "
        "relevant and current sources; separate fact from inference and state unresolved "
        "uncertainty. Cite web-derived factual claims immediately after the sentence or "
        "paragraph they support. Time-sensitive claims require a current, explicitly dated "
        "source matching the requested period. Surface links when navigation materially "
        "helps. Never invent citations, reference IDs or special citation syntax.",
    ]
    if active.skill_instructions:
        lines.extend(("Canonical deep-research skill:", active.skill_instructions))
    if active.evidence:
        lines.extend(("Verified evidence ledger:", active.evidence))
    return "\n".join(lines)
