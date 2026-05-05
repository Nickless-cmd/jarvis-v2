from __future__ import annotations


def test_record_tool_outcome_memory_persists_runtime_action(monkeypatch) -> None:
    from core.services import tool_outcome_memory as tom
    from core.services import runtime_action_outcome_tracking as tracking

    recorded = []
    monkeypatch.setattr(
        tracking,
        "record_runtime_action_outcome",
        lambda **kwargs: recorded.append(kwargs) or {"outcome_id": "out-tool-1", **kwargs},
    )

    stored = tom.record_tool_outcome_memory(
        tool_name="bash",
        arguments={"command": "false", "_runtime_turn_id": "hidden"},
        result={"status": "error", "error": "exit 1"},
        mode="tool",
    )

    assert stored["action_id"] == "tool:bash"
    assert recorded[0]["mode"] == "tool"
    assert recorded[0]["score"] < 0
    assert recorded[0]["payload"]["tool_family"] == "execution"
    assert recorded[0]["payload"]["arguments_preview"] == {"command": "false"}
    assert recorded[0]["result"]["tool_family"] == "execution"
    assert recorded[0]["result"]["summary"] == "exit 1"


def test_tool_outcome_scoring_uses_tool_family() -> None:
    from core.services import tool_outcome_memory as tom

    assert tom.classify_tool_family("read_file") == "read"
    assert tom.classify_tool_family("write_file") == "write"
    assert tom.classify_tool_family("browser_navigate") == "browser"
    assert tom._score_for_outcome(status="ok", family="write", result={}) > tom._score_for_outcome(status="ok", family="read", result={})
    assert tom._score_for_outcome(status="failed", family="write", result={}) < tom._score_for_outcome(status="failed", family="read", result={})


def test_simple_tool_execution_records_tool_outcome(monkeypatch) -> None:
    from core.tools import simple_tools
    from core.services import tool_outcome_memory as tom

    recorded = []
    monkeypatch.setitem(
        simple_tools._TOOL_HANDLERS,
        "unit_test_tool",
        lambda args: {"status": "ok", "summary": f"handled {args['value']}"},
    )
    monkeypatch.setattr(simple_tools.event_bus, "publish", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        tom,
        "record_tool_outcome_memory",
        lambda **kwargs: recorded.append(kwargs) or {"outcome_id": "out-tool-2"},
    )

    result = simple_tools.execute_tool("unit_test_tool", {"value": "x"})

    assert result["status"] == "ok"
    assert recorded[0]["tool_name"] == "unit_test_tool"
    assert recorded[0]["result"]["summary"] == "handled x"
