"""Durable, idempotent settlement for every visible-run segment ending."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.services import in_flight_runs
from core.services.visible_terminal_policy import (
    TerminalDecision,
    TerminalEvidence,
    TerminalState,
    classify_terminal,
    recovery_notice,
)


class FailureClass(str, Enum):
    PROCESS = "process"
    CANCELLATION = "cancellation"
    PROVIDER = "provider"
    WATCHDOG = "watchdog"
    RESEARCH = "research"
    RUNTIME = "runtime"


@dataclass(frozen=True, slots=True)
class RecoverySettlementRequest:
    task_id: str
    run_id: str
    session_id: str
    evidence: TerminalEvidence
    failure_class: FailureClass
    summary: str = ""
    checkpoint_ref: str = ""
    generation: int | None = None
    owner: str = ""
    final_synthesis_attempted: bool = False


@dataclass(frozen=True, slots=True)
class RecoverySettlement:
    decision: TerminalDecision
    record: dict[str, object]
    notice: dict[str, object]
    dispatch_due: bool
    final_synthesis_required: bool = False


def _was_same_recovery(
    before: dict[str, object] | None, *, reason: str, final_synthesis: bool,
) -> bool:
    return bool(
        before
        and str(before.get("status") or "") == "recovering"
        and str(before.get("exit_reason") or "") == str(reason)
        and bool(before.get("final_synthesis_pending")) == bool(final_synthesis)
    )


def settle_segment(request: RecoverySettlementRequest) -> RecoverySettlement:
    """Settle exactly once before stream closure or continuation dispatch."""
    before = in_flight_runs.get_record(request.task_id or request.run_id)
    decision = classify_terminal(request.evidence)
    expected = request.generation
    owner = request.owner

    if decision.state is TerminalState.FAILED_TERMINAL and not request.final_synthesis_attempted:
        recovery_decision = TerminalDecision(
            state=TerminalState.RECOVERING,
            reason=decision.reason,
            should_continue=True,
            notify=True,
            stop_reason="recovering",
        )
        duplicate = _was_same_recovery(
            before, reason=decision.reason, final_synthesis=True,
        )
        if duplicate:
            return RecoverySettlement(
                recovery_decision,
                dict(before or {}),
                recovery_notice(decision.reason, continuing=True),
                False,
                final_synthesis_required=True,
            )
        record = in_flight_runs.settle_recovering(
            request.task_id or request.run_id,
            reason=decision.reason,
            summary=request.summary or decision.reason,
            checkpoint_ref=request.checkpoint_ref,
            recovery_limit=request.evidence.recovery_limit,
            expected_generation=expected,
            expected_owner=owner,
            final_synthesis_pending=True,
        )
        return RecoverySettlement(
            recovery_decision,
            record,
            recovery_notice(decision.reason, continuing=True),
            not duplicate,
            final_synthesis_required=True,
        )

    if decision.state is TerminalState.RECOVERING:
        duplicate = _was_same_recovery(
            before, reason=decision.reason, final_synthesis=False,
        )
        if duplicate:
            return RecoverySettlement(
                decision,
                dict(before or {}),
                recovery_notice(decision.reason, continuing=True),
                False,
            )
        record = in_flight_runs.settle_recovering(
            request.task_id or request.run_id,
            reason=decision.reason,
            summary=request.summary or decision.reason,
            checkpoint_ref=request.checkpoint_ref,
            recovery_limit=request.evidence.recovery_limit,
            expected_generation=expected,
            expected_owner=owner,
        )
        return RecoverySettlement(
            decision,
            record,
            recovery_notice(decision.reason, continuing=True),
            not duplicate,
        )

    if decision.state is TerminalState.WAITING_FOR_USER:
        record = in_flight_runs.settle_waiting(
            request.task_id or request.run_id, reason=decision.reason,
        )
        notice = {
            "state": "waiting_for_user",
            "reason": decision.reason,
            "continuing": False,
        }
        return RecoverySettlement(decision, record, notice, False)

    status = (
        "completed"
        if decision.state is TerminalState.COMPLETED
        else "cancelled"
        if decision.state is TerminalState.CANCELLED
        else "failed_terminal"
    )
    record = in_flight_runs.settle_terminal(
        request.task_id or request.run_id,
        status=status,
        reason=decision.reason,
        expected_generation=expected,
        expected_owner=owner,
    ) or {}
    notice = (
        recovery_notice(decision.reason, continuing=False)
        if decision.state is TerminalState.FAILED_TERMINAL
        else {}
    )
    return RecoverySettlement(decision, record, notice, False)
