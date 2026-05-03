import importlib


def test_resolve_pending_approval_leaves_transcript_persistence_to_stream(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    simple_tools = importlib.import_module("core.tools.simple_tools")

    appended_messages: list[dict] = []
    monkeypatch.setattr(
        visible_runs,
        "append_chat_message",
        lambda **kwargs: appended_messages.append(kwargs),
    )
    monkeypatch.setattr(
        simple_tools,
        "execute_tool_force",
        lambda tool_name, arguments: {"status": "ok", "tool_name": tool_name, "arguments": arguments},
    )
    monkeypatch.setattr(
        simple_tools,
        "format_tool_result_for_model",
        lambda tool_name, result: "[no output]",
    )

    approval_id = "approval-test-shared-resolution"
    visible_runs._set_visible_approval_state(
        approval_id,
        {
            "approval_id": approval_id,
            "status": "pending",
            "tool_name": "bash",
            "arguments": {"command": "touch /tmp/visible-runs-approval-test"},
            "run_id": "visible-test-run",
            "session_id": "chat-test-session",
            "created_at": "2026-04-14T00:00:00+00:00",
        },
    )

    result = visible_runs.resolve_pending_approval(approval_id, approved=True)

    assert result["status"] == "ok"
    assert result["tool"] == "bash"
    assert result["result_text"] == "[no output]"
    assert appended_messages == []

    shared_state = visible_runs._get_visible_approval_state(approval_id)
    assert shared_state["status"] == "approved"
    assert shared_state["tool_status"] == "ok"
    assert shared_state["result_text"] == "[no output]"


def test_execute_simple_tool_calls_suppresses_duplicate_tool_call_within_visible_run(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    simple_tools = importlib.import_module("core.tools.simple_tools")

    executed_calls: list[tuple[str, dict]] = []

    def _fake_execute_tool(tool_name: str, arguments: dict) -> dict:
        executed_calls.append((tool_name, arguments))
        return {
            "status": "approval_needed",
            "message": "approval required",
        }

    monkeypatch.setattr(simple_tools, "execute_tool", _fake_execute_tool)
    monkeypatch.setattr(
        simple_tools,
        "format_tool_result_for_model",
        lambda tool_name, result: "[approval required]",
    )

    run = visible_runs.VisibleRun(
        run_id="visible-duplicate-tool-guard",
        lane="primary",
        provider="test",
        model="test",
        user_message="run duplicate guard",
        session_id="chat-test-session",
    )
    visible_runs.register_visible_run(run)

    try:
        tool_calls = [
            {
                "function": {
                    "name": "bash",
                    "arguments": {"command": "touch /tmp/jarvis-approval-smoke.txt"},
                }
            }
        ]

        first = visible_runs._execute_simple_tool_calls(tool_calls, run_id=run.run_id)
        second = visible_runs._execute_simple_tool_calls(tool_calls, run_id=run.run_id)
    finally:
        visible_runs.unregister_visible_run(run.run_id)

    assert len(executed_calls) == 1
    assert first[0]["status"] == "approval_needed"
    assert second[0]["status"] == "duplicate_suppressed"
    assert second[0]["result_text"] == "[Duplicate tool call skipped in same visible run]"


def test_classify_visible_run_interruption_distinguishes_timeout_disconnect_and_cancel(
    isolated_runtime,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)

    assert visible_runs._classify_visible_run_interruption("timed out waiting for provider stream item") == {
        "interruption_reason": "provider-timeout",
        "interruption_source": "provider-stream",
    }
    assert visible_runs._classify_visible_run_interruption("client disconnect during sse") == {
        "interruption_reason": "client-disconnect",
        "interruption_source": "client-stream",
    }
    assert visible_runs._classify_visible_run_interruption("user-cancelled") == {
        "interruption_reason": "user-interrupted",
        "interruption_source": "runtime-control",
    }
    assert visible_runs._classify_visible_run_interruption("approval wait timeout") == {
        "interruption_reason": "approval-wait-timeout",
        "interruption_source": "runtime-approval",
    }
    assert visible_runs._classify_visible_run_interruption("worker died during process restart") == {
        "interruption_reason": "process-restart",
        "interruption_source": "runtime-process",
    }
    assert visible_runs._classify_visible_run_interruption("unhandled traceback crash") == {
        "interruption_reason": "runtime-crash",
        "interruption_source": "runtime-process",
    }


def test_agentic_watchdog_prefers_silence_over_total_timeout(isolated_runtime) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)

    assert visible_runs._agentic_watchdog_timeout_reason(
        started_at=0.0,
        last_progress_at=200.0,
        now=260.0,
        max_total_s=300.0,
        max_silence_s=75.0,
    ) is None
    assert visible_runs._agentic_watchdog_timeout_reason(
        started_at=0.0,
        last_progress_at=10.0,
        now=90.1,
        max_total_s=300.0,
        max_silence_s=75.0,
    ) == "provider-silence-timeout"
    assert visible_runs._agentic_watchdog_timeout_reason(
        started_at=0.0,
        last_progress_at=290.0,
        now=305.0,
        max_total_s=300.0,
        max_silence_s=75.0,
    ) == "provider-round-timeout"
