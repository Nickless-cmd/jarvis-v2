"""Single source of truth for visible task terminal decisions.

Provider attempts and SSE segments may end without the user's task being done.
This module deliberately contains no I/O so every exit path can ask the same
question before it emits ``completed`` or schedules recovery.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class TerminalState(str, Enum):
    COMPLETED = "completed"
    WAITING_FOR_USER = "waiting_for_user"
    RECOVERING = "recovering"
    CANCELLED = "cancelled"
    FAILED_TERMINAL = "failed_terminal"


@dataclass(frozen=True, slots=True)
class TerminalEvidence:
    exit_reason: str = "completed"
    finish_reason: str = ""
    forced_finalize: bool = False
    pending_tool_intent: bool = False
    explicit_user_cancel: bool = False
    waiting_for_user: bool = False
    completion_evidence: bool = True
    recovery_attempt: int = 0
    recovery_limit: int = 3


@dataclass(frozen=True, slots=True)
class TerminalDecision:
    state: TerminalState
    reason: str
    should_continue: bool
    notify: bool
    stop_reason: str


_DSML_TOOL_INTENT_RE = re.compile(
    r"<｜｜DSML｜｜\s*(?:tool_calls|calls)\s*>|"
    r"<｜｜DSML｜｜\s*invoke\b",
    re.IGNORECASE,
)


def has_pending_tool_intent(text: str | None) -> bool:
    return bool(text and _DSML_TOOL_INTENT_RE.search(str(text)))


def is_recoverable_exit_reason(reason: str | None) -> bool:
    value = str(reason or "").strip().lower()
    if not value or value == "completed":
        return False
    if value in {"user-cancelled", "user-steer-stop", "user-steer-stop-mid-stream"}:
        return False
    return (
        value == "budget-opbrugt"
        or value in {"shutdown", "provider-not-supported", "completed-truncated",
                     "pending-tool-intent", "forced-finalize-unverified"}
        or value.startswith("interrupted:")
        or value.startswith("early-exit-")
        or value.startswith("provider-")
        or value.startswith("round-")
        or value.startswith("turn-")
        or value.startswith("research-")
        or value.startswith("runtime-")
        or value.startswith("unhandled:")
        or value.startswith("relay_")
    )


def classify_terminal(evidence: TerminalEvidence) -> TerminalDecision:
    reason = str(evidence.exit_reason or "").strip() or "unknown"
    if evidence.explicit_user_cancel or reason in {
        "user-cancelled", "user-steer-stop", "user-steer-stop-mid-stream",
    }:
        return TerminalDecision(
            TerminalState.CANCELLED, reason, False, False, "cancelled")
    if evidence.waiting_for_user:
        return TerminalDecision(
            TerminalState.WAITING_FOR_USER, reason, False, True, "waiting_for_user")

    recovery_reason = ""
    if evidence.pending_tool_intent:
        recovery_reason = "pending-tool-intent"
    elif evidence.forced_finalize and not evidence.completion_evidence:
        recovery_reason = "forced-finalize-unverified"
    elif str(evidence.finish_reason or "").strip().lower() == "length":
        recovery_reason = "completed-truncated"
    elif is_recoverable_exit_reason(reason):
        recovery_reason = reason
    elif evidence.forced_finalize and reason != "completed":
        recovery_reason = reason

    if recovery_reason:
        if int(evidence.recovery_attempt) >= max(0, int(evidence.recovery_limit)):
            return TerminalDecision(
                TerminalState.FAILED_TERMINAL, recovery_reason,
                False, True, "failed_terminal")
        return TerminalDecision(
            TerminalState.RECOVERING, recovery_reason,
            True, True, "recovering")

    return TerminalDecision(
        TerminalState.COMPLETED, reason, False, False, "end_turn")


def recovery_notice(reason: str, *, continuing: bool = True) -> dict[str, object]:
    descriptions = {
        "budget-opbrugt": "Arbejdsvinduets rundebudget blev brugt.",
        "pending-tool-intent": "Jarvis havde stadig et vaerktoejskald klar.",
        "completed-truncated": "Modellens svar blev afkortet.",
        "shutdown": "Jarvis-runtime genstarter.",
        "provider-not-supported": "Den valgte model kunne ikke fortsaette vaerktoejssporet.",
        "forced-finalize-unverified": "En tvungen slutrunde manglede bevis for at opgaven var faerdig.",
        "relay_source_idle_timeout": "Svar-kilden var tavs ud over det haarde sikkerhedsloft.",
        "relay_source_closed": "Svar-kilden lukkede uden en normal afslutning.",
    }
    detail = descriptions.get(str(reason or ""), "Det aktuelle run-segment sluttede foer opgaven.")
    if str(reason or "") == "shutdown" and continuing:
        action = "Checkpointet er bevaret til genoptagelse efter genstart."
    else:
        action = "Jarvis fortsaetter automatisk fra sit checkpoint." if continuing else (
            "Checkpointet er bevaret, men automatisk recovery er opbrugt.")
    return {
        "state": "recovering" if continuing else "failed_terminal",
        "reason": str(reason or "unknown"),
        "message": f"{detail} {action}",
        "continuing": bool(continuing),
    }
