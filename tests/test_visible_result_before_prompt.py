from __future__ import annotations

import asyncio
import threading

import pytest

import core.services.ollama_visible_prompt as ollama_prompt
import core.services.visible_followup as visible_followup
import core.services.visible_runs as visible_runs
from core.services import simple_tool_executor
from core.services.visible_model import (
    VisibleModelResult,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)


def _patch_run(monkeypatch, result: dict) -> None:
    def model_stream(**_kwargs):
        yield VisibleModelToolCalls(tool_calls=[{
            "id": "call-1",
            "type": "function",
            "function": {"name": "read_file", "arguments": '{"path":"x"}'},
        }])
        yield VisibleModelStreamDone(result=VisibleModelResult(
            text="", input_tokens=1, output_tokens=1, cost_usd=0.0,
        ))

    monkeypatch.setattr(visible_runs, "stream_visible_model", model_stream)
    monkeypatch.setattr(simple_tool_executor, "_execute_simple_tool_calls",
                        lambda *_args, **_kwargs: [dict(result)])
    monkeypatch.setattr(visible_runs, "_visible_run_cancelled", lambda _run_id: False)
    monkeypatch.setattr(ollama_prompt, "serialize_ollama_chat_messages", lambda value: list(value))
    monkeypatch.setattr(visible_runs, "append_chat_message", lambda **_kwargs: {})
    monkeypatch.setattr(visible_runs, "_persist_session_assistant_message",
                        lambda *_args, **_kwargs: None)
    monkeypatch.setattr(visible_runs, "_track_runtime_candidates",
                        lambda *_args, **_kwargs: None)
    monkeypatch.setattr(visible_runs, "_run_memory_postprocess",
                        lambda *_args, **_kwargs: None)
    monkeypatch.setattr(visible_runs, "write_private_terminal_layers",
                        lambda *_args, **_kwargs: None)
    monkeypatch.setattr("core.costing.ledger.record_cost", lambda **_kwargs: None)
    monkeypatch.setattr("core.services.agentic_checkpoints.save_checkpoint",
                        lambda **_kwargs: None)


def _run() -> visible_runs.VisibleRun:
    return visible_runs.VisibleRun(
        run_id="result-before-prompt",
        lane="primary",
        provider="stub",
        model="stub",
        user_message="read it",
        session_id="session-1",
    )


@pytest.mark.asyncio
async def test_terminal_result_is_emitted_before_blocked_post_tool_prompt(monkeypatch):
    _patch_run(monkeypatch, {
        "tool_name": "read_file",
        "call_id": "call-1",
        "status": "ok",
        "arguments": {"path": "x"},
        "result_text": "contents",
        "result": {"status": "ok"},
    })
    builder_started = threading.Event()
    release_builder = threading.Event()
    phases = []

    def blocked_builder(*_args, **kwargs):
        phases.append(kwargs.get("caller_phase"))
        builder_started.set()
        assert release_builder.wait(timeout=3)
        return [{"role": "user", "content": "read it"}]

    monkeypatch.setattr(visible_runs, "_build_visible_input", blocked_builder)
    chunks: list[str] = []

    async def drive():
        with visible_followup.fault_injection(visible_followup.FAULT_CLEAN_FAIL_BEFORE_DELTA):
            async for chunk in visible_runs._stream_visible_run(_run()):
                chunks.append(chunk)

    task = asyncio.create_task(drive())
    assert await asyncio.to_thread(builder_started.wait, 2)
    assert any(
        "event: capability" in chunk and '"capability_id": "call-1"' in chunk
        for chunk in chunks
    ), "det afsluttede værktøjskort blev holdt bag prompt-builderen"
    assert phases == ["post_tool"]
    release_builder.set()
    await asyncio.wait_for(task, timeout=5)


@pytest.mark.asyncio
async def test_approval_request_is_emitted_before_prompt_work_starts(monkeypatch):
    _patch_run(monkeypatch, {
        "tool_name": "bash",
        "call_id": "call-1",
        "status": "approval_needed",
        "arguments": {"command": "date"},
        "result_text": "",
        "result": {"status": "approval_needed", "message": "må jeg?", "command": "date"},
    })
    builder_started = threading.Event()
    monkeypatch.setattr(
        visible_runs,
        "_build_visible_input",
        lambda *_args, **_kwargs: builder_started.set(),
    )
    monkeypatch.setattr(visible_runs, "saet_godkendelse", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(visible_runs, "_set_visible_approval_state",
                        lambda *_args, **_kwargs: None)
    monkeypatch.setattr(visible_runs, "_publicer_approval_requested",
                        lambda **_kwargs: None)

    stream = visible_runs._stream_visible_run(_run())
    try:
        while True:
            chunk = await asyncio.wait_for(anext(stream), timeout=2)
            if "event: approval_request" in chunk:
                break
        assert not builder_started.is_set()
    finally:
        await stream.aclose()
