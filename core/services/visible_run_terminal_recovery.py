"""Resolve whether an agentic run segment completed or needs recovery."""
from __future__ import annotations

from dataclasses import dataclass
import re

from core.services.visible_terminal_policy import (
    TerminalDecision,
    TerminalEvidence,
    TerminalState,
    classify_terminal,
    has_pending_tool_intent,
    recovery_notice,
)


_COMPLETION_EVIDENCE_RE = re.compile(
    r"\b(?:konklusion(?:en)?\s+er|kort\s+sagt|svaret\s+er|"
    r"færdig|afsluttet|fuldført|implementeret|rettet|løst|verificeret|"
    r"completed|finished|done|fixed|implemented|verified)\b",
    re.IGNORECASE,
)
_NEGATED_COMPLETION_RE = re.compile(
    r"\b(?:ikke|ej|aldrig|not|never)\b.{0,32}"
    r"\b(?:færdig|afsluttet|fuldført|implementeret|rettet|løst|verificeret|"
    r"completed|finished|done|fixed|implemented|verified)\b",
    re.IGNORECASE | re.DOTALL,
)


def has_completion_evidence(text: str | None) -> bool:
    """Conservative positive evidence used only after a forced final round."""
    value = str(text or "")
    return bool(
        value
        and not _NEGATED_COMPLETION_RE.search(value)
        and _COMPLETION_EVIDENCE_RE.search(value)
    )


@dataclass(frozen=True, slots=True)
class AgenticExitResolution:
    decision: TerminalDecision
    exit_reason: str
    event_name: str
    event_payload: dict[str, object]


def resolve_agentic_exit(
    *,
    exit_reason: str,
    final_text: str,
    finish_reason: str = "",
    forced_finalize: bool = False,
    pending_tool_intent: bool = False,
    recovery_attempt: int = 0,
    recovery_limit: int = 3,
) -> AgenticExitResolution:
    pending = bool(pending_tool_intent) or has_pending_tool_intent(final_text)
    decision = classify_terminal(TerminalEvidence(
        exit_reason=exit_reason,
        finish_reason=finish_reason,
        forced_finalize=forced_finalize,
        pending_tool_intent=pending,
        completion_evidence=has_completion_evidence(final_text),
        recovery_attempt=recovery_attempt,
        recovery_limit=recovery_limit,
    ))
    normalized = str(exit_reason or "completed")
    if decision.state is TerminalState.RECOVERING:
        normalized = decision.reason
        return AgenticExitResolution(
            decision, normalized, "run_recovery",
            {"type": "run_recovery", **recovery_notice(normalized, continuing=True)},
        )
    if decision.state is TerminalState.FAILED_TERMINAL:
        normalized = f"failed-terminal:{decision.reason}"
        return AgenticExitResolution(
            decision, normalized, "run_recovery",
            {"type": "run_recovery", **recovery_notice(decision.reason, continuing=False)},
        )
    return AgenticExitResolution(decision, normalized, "", {})
