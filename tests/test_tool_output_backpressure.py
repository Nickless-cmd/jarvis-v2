from __future__ import annotations

import asyncio
import json
import threading
from types import SimpleNamespace

import pytest

from core.services import simple_tool_executor
from core.services.tool_execution_trace import OutputDelta
from core.services.tool_execution_trace import BoundedOutputBuffer
from core.services.visible_tool_exec import run_tool_batch


def _event(frame: str) -> tuple[str, dict]:
    lines = frame.strip().splitlines()
    return lines[0].split(":", 1)[1].strip(), json.loads(lines[1].split(":", 1)[1])


@pytest.mark.asyncio
async def test_live_chunks_are_yielded_before_executor_finishes(monkeypatch):
    release = threading.Event()

    def execute(_calls, *, output_buffer, **_kwargs):
        output_buffer.put(OutputDelta("call-1", "stdout", 1, "før\x1b[3"))
        output_buffer.put(OutputDelta("call-1", "stdout", 2, "1mrød\x1b[0m\n"))
        release.wait(timeout=2)
        return [{"tool_name": "bash", "status": "ok", "result_text": "done"}]

    monkeypatch.setattr(simple_tool_executor, "_execute_simple_tool_calls", execute)
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: SimpleNamespace(live_tool_output_enabled=True),
    )
    run = SimpleNamespace(
        run_id="run-1", session_id="s", autonomous=False,
        user_message="go", local_tool_exec=False, user_id="owner", origin="",
    )
    out = {}
    stream = run_tool_batch(
        [{"id": "call-1", "function": {"name": "bash", "arguments": "{}"}}],
        run=run,
        loop=asyncio.get_running_loop(),
        tool_scope="chat",
        step_counter=0,
        heartbeat_interval_s=5,
        heartbeat_phase="test",
        out=out,
    )

    first = _event(await anext(stream))
    assert first[0] == "working_step"
    delta = _event(await asyncio.wait_for(anext(stream), timeout=1))
    assert delta[0] == "tool_output_delta"
    assert delta[1]["chunk"] == "førrød\n"
    assert "\x1b" not in delta[1]["chunk"]
    assert not release.is_set()
    release.set()
    async for _frame in stream:
        pass
    assert out["results"][0]["call_id"] == "call-1"


@pytest.mark.asyncio
async def test_disabled_live_output_emits_no_delta_and_preserves_result(monkeypatch):
    def execute(_calls, *, output_buffer=None, **_kwargs):
        assert output_buffer is None
        return [{"tool_name": "bash", "status": "ok", "result_text": "done"}]

    monkeypatch.setattr(simple_tool_executor, "_execute_simple_tool_calls", execute)
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: SimpleNamespace(live_tool_output_enabled=False),
    )
    run = SimpleNamespace(
        run_id="run-2", session_id="s", autonomous=False,
        user_message="go", local_tool_exec=False, user_id="owner", origin="",
    )
    out = {}
    frames = [frame async for frame in run_tool_batch(
        [{"id": "call-2", "function": {"name": "bash", "arguments": "{}"}}],
        run=run,
        loop=asyncio.get_running_loop(),
        tool_scope="chat",
        step_counter=0,
        heartbeat_interval_s=5,
        heartbeat_phase="test",
        out=out,
    )]
    assert all(_event(frame)[0] != "tool_output_delta" for frame in frames)
    assert out["results"][0]["result_text"] == "done"


def test_parallel_executor_binds_each_real_call_id_and_marks_boundaries(monkeypatch):
    from core.services import tool_execution_trace
    from core.tools import simple_tools
    from core.services import tool_concurrency

    monkeypatch.setattr(
        simple_tool_executor,
        "_prepare_call",
        lambda tc, **_kwargs: ("run", {
            "name": tc["function"]["name"], "arguments": {},
            "signature": tc["id"], "soft_warn": "", "run_id": "", "inbox_varsel": "",
        }),
    )
    monkeypatch.setattr(
        simple_tool_executor,
        "_finalize_call",
        lambda token, raw, **_kwargs: {"tool_name": token["name"], "status": "ok", "raw": raw},
    )
    monkeypatch.setattr(tool_concurrency, "is_parallelizable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "on")
    monkeypatch.setattr(simple_tool_executor, "_tag_checkpoint_hvis_redigering", lambda *_args: None)
    boundaries = []
    monkeypatch.setattr(tool_execution_trace, "mark_dispatch", lambda call_id: boundaries.append(("start", call_id)))
    monkeypatch.setattr(tool_execution_trace, "mark_execution_complete", lambda call_id: boundaries.append(("end", call_id)))

    def execute(_name, _args):
        tool_execution_trace.emit_current_output("stdout", "x")
        return {"status": "ok"}

    monkeypatch.setattr(simple_tools, "execute_tool", execute)
    output = BoundedOutputBuffer()
    calls = [
        {"id": "call-a", "function": {"name": "read_file", "arguments": {}}},
        {"id": "call-b", "function": {"name": "search", "arguments": {}}},
    ]
    simple_tool_executor._execute_simple_tool_calls(calls, output_buffer=output)
    assert {delta.tool_use_id for delta in output.drain()} == {"call-a", "call-b"}
    assert set(boundaries) == {
        ("start", "call-a"), ("end", "call-a"),
        ("start", "call-b"), ("end", "call-b"),
    }
