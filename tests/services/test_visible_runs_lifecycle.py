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
        "core.services.in_flight_runs.mark_interrupted",
        lambda run_id, **kw: calls.append(("interrupted", run_id, kw)),
    )
    monkeypatch.setattr(
        "core.services.in_flight_runs.mark_completed",
        lambda run_id: calls.append(("completed", run_id)),
    )
    monkeypatch.setattr(
        "core.services.in_flight_runs.clear_session",
        lambda session_id: calls.append(("cleared", session_id)),
    )

    finalize_in_flight(
        run_id="run-recovering", session_id="session-1",
        status="recovering", error="budget-opbrugt",
    )

    assert calls == [("interrupted", "run-recovering", {
        "reason": "budget-opbrugt", "summary": "budget-opbrugt",
    })]


def test_completed_run_clears_durable_in_flight_state(monkeypatch):
    from core.services.visible_runs_sections.run_finalization import finalize_in_flight

    calls = []
    monkeypatch.setattr(
        "core.services.in_flight_runs.mark_interrupted",
        lambda run_id, **kw: calls.append(("interrupted", run_id, kw)),
    )
    monkeypatch.setattr(
        "core.services.in_flight_runs.mark_completed",
        lambda run_id: calls.append(("completed", run_id)),
    )
    monkeypatch.setattr(
        "core.services.in_flight_runs.clear_session",
        lambda session_id: calls.append(("cleared", session_id)),
    )

    finalize_in_flight(
        run_id="run-complete", session_id="session-2",
        status="completed", error="",
    )

    assert calls == [("completed", "run-complete"), ("cleared", "session-2")]
