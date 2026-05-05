from __future__ import annotations


def _state_patch(monkeypatch):
    from core.services import living_executive as lex

    state = {
        "traces": [],
        "last_action_by_key": {},
        "current_focus": {},
        "current_tool_plan": {},
    }
    monkeypatch.setattr(lex, "_load_state", lambda: state)
    monkeypatch.setattr(lex, "_save_state", lambda new_state: state.update(new_state))
    monkeypatch.setattr(lex.event_bus, "publish", lambda *args, **kwargs: None)
    return lex, state


def test_choose_impulse_prefers_highest_intensity(monkeypatch) -> None:
    lex, _state = _state_patch(monkeypatch)

    impulse = lex.choose_impulse([
        {
            "id": 1,
            "kind": "runtime.emotional_gate",
            "payload": {"decision": "verify_first", "input_action": "x"},
        },
        {
            "id": 2,
            "kind": "self_repair.action_failed",
            "payload": {"pattern_id": "p1", "error": "boom"},
        },
    ])

    assert impulse is not None
    assert impulse["action_id"] == "schedule_self_wakeup"
    assert impulse["felt_signal"] == "repair pain"
    assert impulse["intensity"] > 0.8


def test_execute_focus_intent_records_trace_and_focus(monkeypatch) -> None:
    lex, state = _state_patch(monkeypatch)

    trace = lex.run_once(events=[{
        "id": 3,
        "kind": "runtime.emotional_gate",
        "payload": {
            "decision": "verify_first",
            "reason": "fatigue high",
            "input_action": "restart_daemon",
        },
    }])

    assert trace["status"] == "executed"
    assert trace["action_id"] == "record_focus_intent"
    assert state["current_focus"]["focus"] == "emotional gate"
    assert state["traces"][0]["aftertaste"] == "agency expressed"


def test_execute_schedule_self_wakeup_action(monkeypatch) -> None:
    lex, state = _state_patch(monkeypatch)
    import core.services.self_wakeup as sw

    monkeypatch.setattr(
        sw,
        "schedule_self_wakeup",
        lambda **kwargs: {
            "status": "ok",
            "wakeup": {"wakeup_id": "wake-test", **kwargs},
        },
    )

    trace = lex.run_once(events=[{
        "id": 4,
        "kind": "self_repair.action_failed",
        "payload": {"pattern_id": "p1", "name": "Restart mail checker"},
    }])

    assert trace["status"] == "executed"
    assert trace["action_id"] == "schedule_self_wakeup"
    assert "wake-test" in trace["outcome"]
    assert state["traces"][0]["aftertaste"] == "thread held"


def test_cooldown_suppresses_repeated_action(monkeypatch) -> None:
    lex, state = _state_patch(monkeypatch)
    calls = []
    monkeypatch.setitem(
        lex._ACTION_HANDLERS,
        "record_focus_intent",
        lambda impulse: calls.append(impulse) or {"status": "executed", "summary": "ok"},
    )

    event = {
        "id": 5,
        "kind": "runtime.emotional_gate",
        "payload": {"decision": "verify_first", "input_action": "same"},
    }
    first = lex.run_once(events=[event])
    second = lex.run_once(events=[event])

    assert first["status"] == "executed"
    assert second["status"] == "skipped"
    assert len(calls) == 1
    assert len(state["traces"]) == 1


def test_living_executive_surface(monkeypatch) -> None:
    lex, state = _state_patch(monkeypatch)
    state["traces"] = [{
        "trace_id": "lex-test",
        "choice": "Hold focus",
        "action_id": "record_focus_intent",
        "status": "executed",
    }]
    state["current_focus"] = {"focus": "emotional gate"}

    surface = lex.build_living_executive_surface()

    assert surface["active"] is True
    assert surface["mode"] == "experimental-active"
    assert surface["summary"]["last_action"] == "record_focus_intent"
    assert surface["current_focus"]["focus"] == "emotional gate"


def test_tool_failure_proposes_tool_plan_with_precedent(monkeypatch) -> None:
    lex, state = _state_patch(monkeypatch)
    monkeypatch.setattr(
        lex,
        "_recent_memory_precedents",
        lambda **kwargs: [{
            "outcome_id": "out-1",
            "action_id": "tool:bash",
            "status": "error",
            "summary": "previous bash failed",
        }],
    )

    trace = lex.run_once(events=[{
        "id": 8,
        "kind": "tool.completed",
        "payload": {"tool": "bash", "status": "error", "error": "exit 1"},
    }])

    assert trace["status"] == "proposed"
    assert trace["action_id"] == "propose_tool_plan"
    assert state["current_tool_plan"]["tool_name"] == "bash"
    assert state["current_tool_plan"]["tool_family"] == "execution"
    assert state["current_tool_plan"]["runnable_proposals"][0]["tool"] == "bash"
    assert state["current_tool_plan"]["runnable_proposals"][0]["risk"] == "medium"
    assert trace["memory_precedents"][0]["action_id"] == "tool:bash"


def test_memory_precedents_bias_choice_score(monkeypatch) -> None:
    lex, _state = _state_patch(monkeypatch)
    monkeypatch.setattr(
        lex,
        "_recent_memory_precedents",
        lambda **kwargs: [{
            "kind": "runtime_action_outcome",
            "action_id": "tool:bash",
            "status": "failed",
            "summary": "same tool failed before",
            "score": -0.65,
        }],
    )

    impulse = lex.choose_impulse([{
        "id": 9,
        "kind": "tool.completed",
        "payload": {"tool": "bash", "status": "failed", "error": "exit 1"},
    }])

    assert impulse is not None
    assert impulse["choice_score"] > impulse["intensity"]
    assert impulse["memory_bias"] > 0
