def test_run_end_calls_evaluate_and_advance(monkeypatch):
    import core.services.visible_runs as vr
    calls = []
    monkeypatch.setattr(
        "core.context.tool_result_lifecycle.evaluate_and_advance",
        lambda sid, **k: calls.append(sid) or 0,
    )
    vr._advance_tool_lifecycle("sess-vr-1")
    assert calls == ["sess-vr-1"]
