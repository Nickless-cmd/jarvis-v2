from __future__ import annotations

import inspect

import pytest

from core.services.routine_types import AccessScope, RoutineExecutionContext


class RecordingSink:
    def __init__(self):
        self.fragments = []
        self.requests = []
        self.results = []
        self.usages = []
        self.approvals = []
        self.terminals = []

    def model_fragment(self, text):
        self.fragments.append(text)

    def tool_requested(self, call):
        self.requests.append(call)

    def tool_result(self, result):
        self.results.append(result)

    def usage(self, usage):
        self.usages.append(usage)

    def approval_requested(self, call):
        self.approvals.append(call)

    def terminal(self, result):
        self.terminals.append(result)

    @property
    def terminal_count(self):
        return len(self.terminals)


class AlwaysCurrent:
    def __init__(self):
        self.before_effect = 0
        self.between_rounds = 0

    def check_before_effect(self):
        self.before_effect += 1

    def check_between_rounds(self):
        self.between_rounds += 1


@pytest.fixture
def routine_execution_context():
    return RoutineExecutionContext(
        run_id="run-1",
        routine_id="routine-1",
        routine_version=3,
        owner_user_id="member-a",
        access_scope=AccessScope.USER_PRIVATE,
        instruction_ref="sealed:instruction",
        instruction_hash="sha256:test",
        trigger_inputs={"date": "2026-10-12"},
        workspace_name="",
        workspace_kind="",
        workspace_root="",
        capability_scope="chat",
        permission_policy={"tools": ["clock"]},
        approval_policy={},
        provider="fake-provider",
        model="fake-model",
        lease_generation=1,
    )


class TwoRoundDriver:
    def __init__(self):
        self.calls = []

    def complete(self, request):
        from core.services.agentic_execution import AgenticTurn, ToolCall, UsageRecord

        self.calls.append(request)
        if len(self.calls) == 1:
            return AgenticTurn(
                text="Jeg undersøger.",
                tool_calls=(ToolCall("call-1", "clock", {"zone": "UTC"}),),
                usage=UsageRecord(10, 2, 0.001),
                provider="fake-provider",
                model="fake-model",
            )
        return AgenticTurn(
            text="Klokken er 12.",
            usage=UsageRecord(7, 4, 0.002),
            provider="fake-provider",
            model="fake-model",
        )


def test_routine_adapter_has_no_session_surface(
    monkeypatch, routine_execution_context
):
    from core.services.agentic_execution import RoutineExecutionAdapter, execute_agentic

    def forbidden(*_args, **_kwargs):
        raise AssertionError("session surface reached")

    monkeypatch.setattr("core.services.chat_sessions.append_chat_message", forbidden)
    monkeypatch.setattr("core.services.local_tool_broker.register", forbidden)
    sink = RecordingSink()
    cancellation = AlwaysCurrent()
    result = execute_agentic(
        RoutineExecutionAdapter(
            routine_execution_context,
            instruction=b"Find tiden",
            driver=TwoRoundDriver(),
            tool_executor=lambda call: {"time": "12:00", "tool": call.name},
        ),
        sink=sink,
        cancellation=cancellation,
    )
    assert result.status == "succeeded"
    assert result.provider == "fake-provider"
    assert result.model == "fake-model"
    assert result.usage.input_tokens == 17
    assert result.usage.output_tokens == 6
    assert result.usage.cost_usd == pytest.approx(0.003)
    assert sink.terminal_count == 1
    assert [call.name for call in sink.requests] == ["clock"]
    assert cancellation.before_effect == 1
    assert cancellation.between_rounds == 1


def test_visible_adapter_preserves_provider_and_usage():
    from core.services.agentic_execution import VisibleExecutionAdapter, execute_agentic

    sink = RecordingSink()
    result = execute_agentic(
        VisibleExecutionAdapter(
            prompt="visible prompt",
            provider="fake-provider",
            model="fake-model",
            driver=TwoRoundDriver(),
            tool_executor=lambda _call: {"ok": True},
        ),
        sink,
        AlwaysCurrent(),
    )
    assert result.provider == "fake-provider"
    assert result.model == "fake-model"
    assert result.usage.input_tokens == 17
    assert result.usage.output_tokens == 6


def test_approval_stops_before_effect(routine_execution_context):
    from core.services.agentic_execution import (
        AgenticTurn,
        RoutineExecutionAdapter,
        ToolCall,
        execute_agentic,
    )

    class Driver:
        def complete(self, _request):
            return AgenticTurn(
                tool_calls=(ToolCall("danger", "bash", {"command": "x"}, True),),
                provider="p",
                model="m",
            )

    executed = []
    sink = RecordingSink()
    result = execute_agentic(
        RoutineExecutionAdapter(
            routine_execution_context,
            instruction=b"Run",
            driver=Driver(),
            tool_executor=lambda call: executed.append(call),
        ),
        sink,
        AlwaysCurrent(),
    )
    assert result.status == "waiting_approval"
    assert executed == []
    assert len(sink.approvals) == 1
    assert sink.terminal_count == 1


def test_round_limit_fails_with_one_terminal(routine_execution_context):
    from core.services.agentic_execution import (
        AgenticTurn,
        RoutineExecutionAdapter,
        ToolCall,
        execute_agentic,
    )

    class Endless:
        def complete(self, _request):
            return AgenticTurn(
                tool_calls=(ToolCall("again", "clock", {}),), provider="p", model="m"
            )

    sink = RecordingSink()
    result = execute_agentic(
        RoutineExecutionAdapter(
            routine_execution_context,
            instruction=b"Loop",
            driver=Endless(),
            tool_executor=lambda _call: {},
            max_rounds=2,
        ),
        sink,
        AlwaysCurrent(),
    )
    assert result.status == "failed"
    assert result.error_code == "round_limit"
    assert sink.terminal_count == 1


def test_routine_prompt_has_no_visible_session_builder():
    import core.services.routine_prompt as routine_prompt

    source = inspect.getsource(routine_prompt)
    assert "build_visible_chat_prompt_assembly" not in source
    assert "session_id" not in source
