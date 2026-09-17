from __future__ import annotations

from dataclasses import replace

import pytest

from core.runtime import state_store
from core.services import in_flight_runs
from core.services.visible_run_recovery_coordinator import (
    FailureClass,
    RecoverySettlementRequest,
    settle_segment,
)
from core.services.visible_terminal_policy import TerminalEvidence, TerminalState


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)


def _request(reason: str, failure_class: FailureClass) -> RecoverySettlementRequest:
    in_flight_runs.mark_started(
        run_id="r1", session_id="s1", user_message="finish the task"
    )
    return RecoverySettlementRequest(
        task_id="r1",
        run_id="r1",
        session_id="s1",
        evidence=TerminalEvidence(exit_reason=reason),
        failure_class=failure_class,
        summary=reason,
        checkpoint_ref="checkpoint-r1",
    )


@pytest.mark.parametrize(
    ("reason", "failure_class"),
    [
        ("shutdown", FailureClass.PROCESS),
        ("provider-timeout", FailureClass.PROVIDER),
        ("round-silence-timeout", FailureClass.WATCHDOG),
        ("research-wall-time-exceeded", FailureClass.RESEARCH),
        ("unhandled:ValueError", FailureClass.RUNTIME),
    ],
)
def test_recoverable_failure_classes_never_complete(reason, failure_class):
    out = settle_segment(_request(reason, failure_class))

    assert out.decision.state is TerminalState.RECOVERING
    assert out.record["status"] == "recovering"
    assert out.dispatch_due is True
    assert out.notice["state"] == "recovering"


def test_duplicate_settlement_is_idempotent():
    request = _request("provider-timeout", FailureClass.PROVIDER)

    first = settle_segment(request)
    second = settle_segment(request)

    assert second.record == first.record
    assert first.dispatch_due is True
    assert second.dispatch_due is False


def test_explicit_cancel_is_final_and_revokes_recovery():
    request = _request("user-cancelled", FailureClass.CANCELLATION)
    request = replace(
        request,
        evidence=TerminalEvidence(
            exit_reason="user-cancelled", explicit_user_cancel=True
        ),
    )

    out = settle_segment(request)

    assert out.decision.state is TerminalState.CANCELLED
    assert out.record["status"] == "cancelled"
    assert out.dispatch_due is False
    assert in_flight_runs.claim_due_recovery(owner="other") is None


def test_exhausted_recovery_requests_one_final_synthesis_before_terminal():
    request = _request("provider-timeout", FailureClass.PROVIDER)
    request = replace(
        request,
        evidence=TerminalEvidence(
            exit_reason="provider-timeout", recovery_attempt=3, recovery_limit=3
        ),
    )

    synthesis = settle_segment(request)
    terminal = settle_segment(replace(request, final_synthesis_attempted=True))

    assert synthesis.decision.state is TerminalState.RECOVERING
    assert synthesis.final_synthesis_required is True
    assert synthesis.record["final_synthesis_pending"] is True
    assert terminal.decision.state is TerminalState.FAILED_TERMINAL
    assert terminal.record["status"] == "failed_terminal"


def test_clean_completion_is_durable_and_not_dispatchable():
    request = _request("completed", FailureClass.RUNTIME)

    out = settle_segment(request)

    assert out.decision.state is TerminalState.COMPLETED
    assert out.record["status"] == "completed"
    assert out.dispatch_due is False
