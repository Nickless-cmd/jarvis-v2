from core.services import simple_tool_executor as ste


def test_reexported_from_visible_runs():
    from core.services.visible_runs import _execute_simple_tool_calls as via_vr
    assert via_vr is ste._execute_simple_tool_calls


def test_basic_sequential_execution(monkeypatch):
    # No run_id → controller None → no dedup/cache state; pure pass-through.
    calls = [{"function": {"name": "read_file", "arguments": {"path": "/x"}}}]

    def fake_execute_tool(name, arguments):
        return {"status": "ok", "output": f"ran {name}"}

    monkeypatch.setattr("core.tools.simple_tools.execute_tool", fake_execute_tool)
    monkeypatch.setattr("core.tools.simple_tools.format_tool_result_for_model",
                        lambda name, result: str(result.get("output") or ""))
    # Neutralise the commit-gate so the tool runs.
    monkeypatch.setattr("core.services.commit_gate_arbiter.evaluate_commit_gates",
                        lambda **kw: type("CG", (), {"blocked": False, "soft_warn": "",
                                                     "reason": "", "gate_type": ""})())
    out = ste._execute_simple_tool_calls(calls, force=False)
    assert len(out) == 1
    assert out[0]["tool_name"] == "read_file"
    assert out[0]["status"] == "ok"
    assert out[0]["result_text"] == "ran read_file"
