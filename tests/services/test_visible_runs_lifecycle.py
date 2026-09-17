def test_run_end_calls_evaluate_and_advance(monkeypatch):
    import core.services.visible_runs as vr
    calls = []
    monkeypatch.setattr(
        "core.context.tool_result_lifecycle.evaluate_and_advance",
        lambda sid, **k: calls.append(sid) or 0,
    )
    vr._advance_tool_lifecycle("sess-vr-1")
    assert calls == ["sess-vr-1"]


def test_recovering_run_remains_durable_for_restart(monkeypatch):
    from core.services.visible_runs_sections.run_finalization import finalize_in_flight

    calls = []
    monkeypatch.setattr(
        "core.services.in_flight_runs.settle_recovering",
        lambda run_id, **kw: calls.append(("recovering", run_id, kw)) or {},
    )

    finalize_in_flight(
        run_id="run-recovering", session_id="session-1",
        status="recovering", error="budget-opbrugt",
    )

    assert calls == [("recovering", "run-recovering", {
        "reason": "budget-opbrugt", "summary": "budget-opbrugt",
    })]


def test_completed_run_is_durably_settled(monkeypatch):
    from core.services.visible_runs_sections.run_finalization import finalize_in_flight

    calls = []
    monkeypatch.setattr(
        "core.services.in_flight_runs.settle_terminal",
        lambda run_id, **kw: calls.append((run_id, kw)) or {},
    )

    finalize_in_flight(
        run_id="run-complete", session_id="session-2",
        status="completed", error="",
    )

    assert calls == [("run-complete", {"status": "completed", "reason": "completed"})]


def test_failed_run_is_preserved_as_terminal_not_erased(monkeypatch):
    from core.services.visible_runs_sections.run_finalization import finalize_in_flight

    calls = []
    monkeypatch.setattr(
        "core.services.in_flight_runs.settle_terminal",
        lambda run_id, **kw: calls.append((run_id, kw)) or {},
    )

    finalize_in_flight(
        run_id="run-failed", session_id="session-3",
        status="failed_terminal", error="provider-auth-failed",
    )

    assert calls == [("run-failed", {
        "status": "failed_terminal", "reason": "provider-auth-failed",
    })]
