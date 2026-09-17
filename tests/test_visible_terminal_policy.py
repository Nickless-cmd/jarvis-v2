from core.services.visible_terminal_policy import (
    TerminalEvidence,
    TerminalState,
    classify_terminal,
    has_pending_tool_intent,
    recovery_notice,
)


def test_clean_stop_is_the_only_normal_completion():
    decision = classify_terminal(TerminalEvidence(exit_reason="completed", finish_reason="stop"))
    assert decision.state is TerminalState.COMPLETED
    assert decision.should_continue is False


def test_forced_finalize_with_pending_tool_intent_recovers():
    decision = classify_terminal(TerminalEvidence(
        exit_reason="completed",
        finish_reason="stop",
        forced_finalize=True,
        pending_tool_intent=True,
    ))
    assert decision.state is TerminalState.RECOVERING
    assert decision.reason == "pending-tool-intent"
    assert decision.should_continue is True
    assert decision.stop_reason == "recovering"


def test_budget_shutdown_and_provider_failures_are_recoverable_segments():
    for reason in (
        "budget-opbrugt",
        "shutdown",
        "provider-not-supported",
        "completed-truncated",
        "interrupted:provider-timeout",
        "early-exit-tool-only",
    ):
        decision = classify_terminal(TerminalEvidence(exit_reason=reason))
        assert decision.state is TerminalState.RECOVERING, reason
        assert decision.should_continue is True, reason


def test_explicit_user_stop_is_final_and_never_auto_continues():
    decision = classify_terminal(TerminalEvidence(
        exit_reason="user-cancelled", explicit_user_cancel=True,
    ))
    assert decision.state is TerminalState.CANCELLED
    assert decision.should_continue is False


def test_recovery_chain_limit_becomes_visible_terminal_failure():
    decision = classify_terminal(TerminalEvidence(
        exit_reason="shutdown", recovery_attempt=3, recovery_limit=3,
    ))
    assert decision.state is TerminalState.FAILED_TERMINAL
    assert decision.should_continue is False
    assert decision.notify is True


def test_deepseek_calls_dialect_is_pending_tool_intent():
    text = (
        '<｜｜DSML｜｜ calls>\n'
        '<｜｜DSML｜｜ invoke name="bash">\n'
        '<｜｜DSML｜｜ parameter name="command">echo hej</｜｜DSML｜｜ parameter>\n'
        '</｜｜DSML｜｜ invoke>\n'
        '</｜｜DSML｜｜ calls>'
    )
    assert has_pending_tool_intent(text) is True


def test_shutdown_notice_does_not_promise_work_in_a_dying_process():
    notice = recovery_notice("shutdown", continuing=True)
    assert "checkpoint" in str(notice["message"]).lower()
    assert "fortsaetter automatisk" not in str(notice["message"]).lower()
