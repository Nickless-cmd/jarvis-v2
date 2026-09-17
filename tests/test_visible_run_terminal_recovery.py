from core.services.visible_run_terminal_recovery import resolve_agentic_exit
from core.services.visible_terminal_policy import TerminalState


def test_forced_final_dsml_intent_becomes_recovery_event():
    result = resolve_agentic_exit(
        exit_reason="completed",
        final_text="Nu samler jeg loggen.",
        finish_reason="stop",
        forced_finalize=True,
        pending_tool_intent=True,
    )
    assert result.exit_reason == "pending-tool-intent"
    assert result.decision.state is TerminalState.RECOVERING
    assert result.event_name == "run_recovery"
    assert result.event_payload["continuing"] is True


def test_forced_final_with_explicit_conclusion_can_complete():
    result = resolve_agentic_exit(
        exit_reason="completed",
        final_text="Konklusionen er, at firewall-reglen blokerede trafikken.",
        finish_reason="stop",
        forced_finalize=True,
        pending_tool_intent=False,
    )
    assert result.exit_reason == "completed"
    assert result.decision.state is TerminalState.COMPLETED
    assert result.event_name == ""


def test_forced_final_without_completion_evidence_recovers():
    result = resolve_agentic_exit(
        exit_reason="completed",
        final_text="Jeg har undersøgt loggen og samler nu resultaterne.",
        finish_reason="stop",
        forced_finalize=True,
        pending_tool_intent=False,
    )
    assert result.exit_reason == "forced-finalize-unverified"
    assert result.decision.state is TerminalState.RECOVERING
    assert result.event_payload["continuing"] is True


def test_negated_completion_claim_never_counts_as_evidence():
    result = resolve_agentic_exit(
        exit_reason="completed",
        final_text="Opgaven er ikke afsluttet; jeg mangler stadig verifikationen.",
        finish_reason="stop",
        forced_finalize=True,
    )
    assert result.exit_reason == "forced-finalize-unverified"
    assert result.decision.state is TerminalState.RECOVERING


def test_length_finish_recovers_even_with_partial_text():
    result = resolve_agentic_exit(
        exit_reason="completed", final_text="Et halvt svar",
        finish_reason="length", forced_finalize=False,
    )
    assert result.exit_reason == "completed-truncated"
    assert result.decision.state is TerminalState.RECOVERING


def test_exhausted_recovery_chain_never_promises_another_continuation():
    result = resolve_agentic_exit(
        exit_reason="early-exit-tool-only",
        final_text="",
        recovery_attempt=3,
        recovery_limit=3,
    )
    assert result.decision.state is TerminalState.FAILED_TERMINAL
    assert result.event_payload["continuing"] is False
    assert result.event_payload["state"] == "failed_terminal"


def test_visible_run_routes_exit_through_terminal_recovery():
    """Opgave 3 (17/9-2026): udgangen går nu gennem `settle_segment_exit`, som
    skriver den durable post FØR den terminale SSE. Klassifikationen er den
    samme — `resolve_agentic_exit` er stadig den rene funktion bag den."""
    import inspect
    from core.services import visible_runs
    source = inspect.getsource(visible_runs)
    assert "settle_segment_exit(" in source
    assert '_agentic_loop_exit_reason = "early-exit-empty-text"' in source
    assert '_agentic_loop_exit_reason = "early-exit-tool-only"' in source
    assert '_agentic_loop_exit_reason = "early-exit-loop-gate-skip"' in source
