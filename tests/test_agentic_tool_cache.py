from __future__ import annotations

import importlib


def test_read_only_tool_result_cache_reuses_result_across_runs(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    simple_tools = importlib.import_module("core.tools.simple_tools")

    calls: list[str] = []

    def fake_execute(tool_name: str, arguments: dict) -> dict:
        calls.append(tool_name)
        return {"status": "ok", "text": "cached file content"}

    monkeypatch.setattr(simple_tools, "execute_tool", fake_execute)
    monkeypatch.setattr(
        simple_tools,
        "format_tool_result_for_model",
        lambda tool_name, result: str(result.get("text") or ""),
    )

    tool_calls = [
        {"function": {"name": "read_file", "arguments": {"path": "missing-cache-test.txt"}}}
    ]

    first = visible_runs._execute_simple_tool_calls(tool_calls, run_id="run-cache-1")
    second = visible_runs._execute_simple_tool_calls(tool_calls, run_id="run-cache-2")

    assert first[0]["result_text"] == "cached file content"
    assert second[0]["result_text"] == "cached file content"
    assert second[0]["cached"] is True
    assert calls == ["read_file"]
