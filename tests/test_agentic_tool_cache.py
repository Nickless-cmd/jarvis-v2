from __future__ import annotations

import importlib


def test_read_only_tool_result_cache_reuses_result_across_runs(
    isolated_runtime,
    monkeypatch,
) -> None:
    # The read-only tool cache persists to the shared state_store JSON
    # (~/.jarvis-v2/state/agentic_tool_result_cache.json). isolated_runtime does
    # not reload state_store, so earlier tests that stored a "read_file" result
    # leak an entry here → the first call below hits the cache and never invokes
    # fake_execute (calls == [] instead of ["read_file"]). Start from an empty
    # cache so this test asserts its own behaviour, not accumulated state.
    from core.services import agentic_tool_cache
    agentic_tool_cache._save({})

    # NB: do NOT importlib.reload(visible_runs) here — isolated_runtime
    # already reloaded it, and a second in-test reload re-executes the module
    # body mid-suite, leaving accumulator state that poisons later non-
    # isolated tests (test_streaming_fault_injection breaker/stall tests).
    visible_runs = importlib.import_module("core.services.visible_runs")
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


def test_stale_cached_result_is_not_reused(isolated_runtime) -> None:
    """Et svar fra i forgårs må ikke serveres i dag.

    Målt 3/10-2026: `decision_list` uden argumenter ramte en post gemt
    1/10 13:33 og svarede 7 aktive beslutninger, mens tabellen havde 24.
    Friskheds-tjekket fandtes kun for `read_file`, så posten blev serveret
    på ubestemt tid.
    """
    from datetime import UTC, datetime, timedelta

    from core.services import agentic_tool_cache

    agentic_tool_cache._save({})
    records = agentic_tool_cache._load()
    records[agentic_tool_cache._signature("decision_list", {})] = {
        "tool_name": "decision_list",
        "arguments": {},
        "result_text": "gammelt svar",
        "status": "ok",
        "stored_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
    }
    agentic_tool_cache._save(records)

    assert agentic_tool_cache.get_cached_result("decision_list", {}) is None


def test_fresh_cached_result_is_still_reused(isolated_runtime) -> None:
    """TTL'en må ikke slå cachen ihjel — et friskt svar genbruges stadig."""
    from datetime import UTC, datetime

    from core.services import agentic_tool_cache

    agentic_tool_cache._save({})
    records = agentic_tool_cache._load()
    records[agentic_tool_cache._signature("decision_list", {})] = {
        "tool_name": "decision_list",
        "arguments": {},
        "result_text": "frisk",
        "status": "ok",
        "stored_at": datetime.now(UTC).isoformat(),
    }
    agentic_tool_cache._save(records)

    hit = agentic_tool_cache.get_cached_result("decision_list", {})
    assert hit is not None
    assert hit["result_text"] == "frisk"
