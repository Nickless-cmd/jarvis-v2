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


import contextvars
import time
from core.services import tool_concurrency


_SCOPE = contextvars.ContextVar("_test_scope", default="DEFAULT")


def _mk_calls(names):
    return [{"function": {"name": n, "arguments": {"i": i}}} for i, n in enumerate(names)]


def _patch_reads(monkeypatch, record=None, sleep_map=None):
    def fake_execute_tool(name, arguments):
        if sleep_map:
            time.sleep(sleep_map.get(arguments.get("i"), 0))
        if record is not None:
            record.append((name, arguments.get("i"), _SCOPE.get()))
        return {"status": "ok", "output": f"{name}:{arguments.get('i')}"}
    monkeypatch.setattr("core.tools.simple_tools.execute_tool", fake_execute_tool)
    monkeypatch.setattr("core.tools.simple_tools.format_tool_result_for_model",
                        lambda name, result: str(result.get("output") or ""))
    monkeypatch.setattr("core.services.commit_gate_arbiter.evaluate_commit_gates",
                        lambda **kw: type("CG", (), {"blocked": False, "soft_warn": "",
                                                     "reason": "", "gate_type": ""})())
    monkeypatch.setattr("core.services.agentic_tool_cache.get_cached_result",
                        lambda name, arguments: None)
    monkeypatch.setattr("core.services.agentic_tool_cache.store_result", lambda **kw: None)


def test_parallel_equals_sequential(monkeypatch):
    names = ["read_file", "search_memory", "list_dir"]
    _patch_reads(monkeypatch)
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "off")
    seq = ste._execute_simple_tool_calls(_mk_calls(names))
    _patch_reads(monkeypatch)
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "on")
    par = ste._execute_simple_tool_calls(_mk_calls(names))
    assert [r["result_text"] for r in seq] == [r["result_text"] for r in par]
    assert [r["tool_name"] for r in par] == names  # emission order preserved


def test_parallel_preserves_order_under_out_of_order_completion(monkeypatch):
    names = ["read_file", "search_memory", "list_dir"]
    # First call sleeps longest -> finishes last, but must still be index 0 in output.
    _patch_reads(monkeypatch, sleep_map={0: 0.15, 1: 0.05, 2: 0.0})
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "on")
    out = ste._execute_simple_tool_calls(_mk_calls(names))
    assert [r["result_text"] for r in out] == ["read_file:0", "search_memory:1", "list_dir:2"]


def test_parallel_propagates_contextvars_to_workers(monkeypatch):
    # SECURITY-CRITICAL: mode/role/tier gating reads ContextVars inside execute_tool.
    # A raw worker thread would see DEFAULT. Each task must run in a copied context.
    record: list = []
    _patch_reads(monkeypatch, record=record)
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "on")
    token = _SCOPE.set("OWNER_SCOPE")
    try:
        ste._execute_simple_tool_calls(_mk_calls(["read_file", "search_memory"]))
    finally:
        _SCOPE.reset(token)
    observed = {scope for (_n, _i, scope) in record}
    assert observed == {"OWNER_SCOPE"}, f"worker context not propagated: {observed}"
