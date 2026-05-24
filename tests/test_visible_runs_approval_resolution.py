"""Tests for resolve_pending_approval — focus on the chat-persistence
contract for tool results after manual approval.

2026-05-24 (Claude): the long-standing approval_feedback_gap bug.
resolve_pending_approval used to leave transcript persistence to the
streaming run's tool loop. When the stream died/timed out before the
user clicked Approve, the tool ran on approval but the result never
reached chat_messages — Jarvis was blind to it on next turn.

Now resolve_pending_approval appends role=tool directly and sets a
chat_persisted=True dedup marker so the streaming-path can skip its
own append when both code paths race.

Notes:
  - The other tests previously in this file (interruption classifier,
    duplicate-tool-call guard, agentic-watchdog timeout) depend on the
    isolated_runtime fixture which is currently broken upstream
    (cognitive_decisions table init order). Those tests have been
    moved out of scope for this commit; they should be restored when
    that fixture is fixed.
"""
import importlib

import pytest


def test_resolve_pending_approval_persists_tool_result_to_chat(monkeypatch) -> None:
    """resolve_pending_approval now appends role=tool to chat directly,
    closing the gap where a stream-died-before-approval left the tool
    result invisible to Jarvis' next turn."""
    visible_runs = importlib.import_module("core.services.visible_runs")
    simple_tools = importlib.import_module("core.tools.simple_tools")

    appended_messages: list[dict] = []
    monkeypatch.setattr(
        visible_runs, "append_chat_message",
        lambda **kwargs: appended_messages.append(kwargs) or {"id": "m-fake"},
    )
    monkeypatch.setattr(
        simple_tools, "execute_tool_force",
        lambda tool_name, arguments: {
            "status": "ok", "tool_name": tool_name, "arguments": arguments,
        },
    )
    monkeypatch.setattr(
        simple_tools, "format_tool_result_for_model",
        lambda tool_name, result: "[no output]",
    )

    approval_id = "approval-test-chat-persist"
    visible_runs._set_visible_approval_state(approval_id, {
        "approval_id": approval_id,
        "status": "pending",
        "tool_name": "bash",
        "arguments": {"command": "touch /tmp/x"},
        "run_id": "visible-test-run",
        "session_id": "chat-test-session",
        "created_at": "2026-05-24T00:00:00+00:00",
    })

    result = visible_runs.resolve_pending_approval(approval_id, approved=True)

    assert result["status"] == "ok"
    assert result["tool"] == "bash"
    assert result["result_text"] == "[no output]"
    assert result["chat_persisted"] is True
    # The result IS persisted to chat from resolve_pending_approval
    assert len(appended_messages) == 1
    assert appended_messages[0]["role"] == "tool"
    assert appended_messages[0]["content"] == "[no output]"
    assert appended_messages[0]["session_id"] == "chat-test-session"

    shared_state = visible_runs._get_visible_approval_state(approval_id)
    assert shared_state["status"] == "approved"
    assert shared_state["chat_persisted"] is True


def test_resolve_pending_approval_persistence_failure_does_not_block(monkeypatch) -> None:
    """Persistence failure → flag stays False, but the approval result
    still returns success (the tool ran). Streaming-path can still
    attempt its own append since dedupe flag is False."""
    visible_runs = importlib.import_module("core.services.visible_runs")
    simple_tools = importlib.import_module("core.tools.simple_tools")

    def _failing_append(**kwargs):
        raise RuntimeError("db write failed")

    monkeypatch.setattr(visible_runs, "append_chat_message", _failing_append)
    monkeypatch.setattr(
        simple_tools, "execute_tool_force",
        lambda tool_name, arguments: {"status": "ok"},
    )
    monkeypatch.setattr(
        simple_tools, "format_tool_result_for_model",
        lambda tool_name, result: "[output]",
    )

    approval_id = "approval-test-fail-persist"
    visible_runs._set_visible_approval_state(approval_id, {
        "approval_id": approval_id, "status": "pending",
        "tool_name": "bash", "arguments": {"command": "echo"},
        "run_id": "r", "session_id": "s",
        "created_at": "2026-05-24T00:00:00+00:00",
    })

    result = visible_runs.resolve_pending_approval(approval_id, approved=True)
    assert result["status"] == "ok"
    assert result["chat_persisted"] is False


def test_resolve_pending_approval_no_session_skips_persistence(monkeypatch) -> None:
    """If pending has no session_id (autonomous approval flow), skip
    chat-persistence cleanly — no error, just chat_persisted=False."""
    visible_runs = importlib.import_module("core.services.visible_runs")
    simple_tools = importlib.import_module("core.tools.simple_tools")

    monkeypatch.setattr(
        visible_runs, "append_chat_message",
        lambda **_: pytest.fail("should not be called when session_id is empty"),
    )
    monkeypatch.setattr(
        simple_tools, "execute_tool_force",
        lambda tool_name, arguments: {"status": "ok"},
    )
    monkeypatch.setattr(
        simple_tools, "format_tool_result_for_model",
        lambda tool_name, result: "[output]",
    )

    approval_id = "approval-test-no-session"
    visible_runs._set_visible_approval_state(approval_id, {
        "approval_id": approval_id, "status": "pending",
        "tool_name": "bash", "arguments": {"command": "echo"},
        "run_id": "r", "session_id": "",  # no session
        "created_at": "2026-05-24T00:00:00+00:00",
    })

    result = visible_runs.resolve_pending_approval(approval_id, approved=True)
    assert result["status"] == "ok"
    assert result["chat_persisted"] is False


def test_resolve_pending_approval_denied_does_not_persist(monkeypatch) -> None:
    """Denial path should not touch chat (no tool result to persist)."""
    visible_runs = importlib.import_module("core.services.visible_runs")

    monkeypatch.setattr(
        visible_runs, "append_chat_message",
        lambda **_: pytest.fail("should not be called on denial"),
    )

    approval_id = "approval-test-denied"
    visible_runs._set_visible_approval_state(approval_id, {
        "approval_id": approval_id, "status": "pending",
        "tool_name": "bash", "arguments": {"command": "echo"},
        "run_id": "r", "session_id": "s",
        "created_at": "2026-05-24T00:00:00+00:00",
    })

    result = visible_runs.resolve_pending_approval(approval_id, approved=False)
    assert result["status"] == "denied"
