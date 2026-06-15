import core.services.gut_calibration as gc


def _clear():
    gc._pending.clear()


def test_started_stashes_hunch(monkeypatch):
    _clear()
    monkeypatch.setattr("core.services.gut_engine.derive_gut_signal",
                        lambda *, task_description: {"hunch": "proceed"})
    gc.observe_run_event("runtime.autonomous_run_started", {"run_id": "r1", "focus": "fix bug"})
    assert gc._pending["r1"] == "proceed"


def test_completed_records_outcome(monkeypatch):
    _clear()
    monkeypatch.setattr("core.services.gut_engine.derive_gut_signal",
                        lambda *, task_description: {"hunch": "proceed"})
    captured = {}
    monkeypatch.setattr("core.services.gut_engine.record_gut_outcome",
                        lambda *, hunch, actual_outcome: captured.update(h=hunch, o=actual_outcome))
    gc.observe_run_event("runtime.autonomous_run_started", {"run_id": "r1"})
    gc.observe_run_event("runtime.autonomous_run_completed", {"run_id": "r1"})
    assert captured == {"h": "proceed", "o": "completed"}
    assert "r1" not in gc._pending  # ryddet efter registrering


def test_failed_maps_to_error(monkeypatch):
    _clear()
    monkeypatch.setattr("core.services.gut_engine.derive_gut_signal",
                        lambda *, task_description: {"hunch": "caution"})
    captured = {}
    monkeypatch.setattr("core.services.gut_engine.record_gut_outcome",
                        lambda *, hunch, actual_outcome: captured.update(o=actual_outcome))
    gc.observe_run_event("runtime.autonomous_run_started", {"run_id": "r2"})
    gc.observe_run_event("runtime.autonomous_run_failed", {"run_id": "r2"})
    assert captured["o"] == "error"


def test_outcome_without_started_is_noop(monkeypatch):
    _clear()
    called = {"n": 0}
    monkeypatch.setattr("core.services.gut_engine.record_gut_outcome",
                        lambda *, hunch, actual_outcome: called.__setitem__("n", called["n"] + 1))
    gc.observe_run_event("runtime.autonomous_run_completed", {"run_id": "ghost"})
    assert called["n"] == 0


def test_observe_never_raises():
    _clear()
    # Manglende run_id / tom payload må ikke kaste.
    gc.observe_run_event("runtime.autonomous_run_started", {})
    gc.observe_run_event("runtime.autonomous_run_completed", {})
    gc.observe_run_event("irrelevant.event", {"run_id": "x"})
