from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services.chat_sessions import append_chat_message, create_chat_session
from core.services.tool_result_store import (
    cleanup_old_results,
    get_tool_result,
    parse_tool_result_reference,
    save_tool_result,
    summarize_result,
)
from core.services.visible_model import _build_visible_input
from core.tools.simple_tools import execute_tool


def test_tool_result_store_round_trip(isolated_runtime) -> None:
    result_id = save_tool_result(
        "bash",
        {"command": "git status"},
        "line 1\nline 2\nline 3",
    )

    stored = get_tool_result(result_id)

    assert stored is not None
    assert stored["result_id"] == result_id
    assert stored["tool_name"] == "bash"
    assert stored["arguments"] == {"command": "git status"}
    assert stored["result"] == "line 1\nline 2\nline 3"


def test_summarize_result_is_bounded() -> None:
    summary = summarize_result("x" * 900, max_length=120)

    assert len(summary) == 120
    assert summary.endswith("…")


def test_append_chat_message_externalizes_tool_result(isolated_runtime) -> None:
    session = create_chat_session(title="Tool history")

    message = append_chat_message(
        session_id=str(session["id"]),
        role="tool",
        content="runtime event memory.end_of_run_consolidation missing",
        tool_name="bash",
        tool_arguments={"command": "rg memory.end_of_run_consolidation ."},
    )

    ref = parse_tool_result_reference(message["content"])

    assert ref is not None
    assert "[tool_result:" in message["content"]
    assert "Use read_tool_result" in message["content"]
    stored = get_tool_result(ref["result_id"])
    assert stored is not None
    assert stored["result"] == "runtime event memory.end_of_run_consolidation missing"
    assert stored["tool_name"] == "bash"


def test_build_visible_input_expands_recent_tool_result_reference(isolated_runtime) -> None:
    session = create_chat_session(title="Expanded tools")
    session_id = str(session["id"])
    full_result = "prefix " + ("detail " * 120) + "TAIL_MARKER_FOR_EXPANSION"

    append_chat_message(session_id=session_id, role="user", content="check the runtime")
    append_chat_message(
        session_id=session_id,
        role="tool",
        content=full_result,
        tool_name="bash",
        tool_arguments={"command": "journalctl -u jarvis-api"},
    )

    items = _build_visible_input(
        "what did the tool find?",
        session_id=session_id,
        provider="ollama",
        model="qwen3.5:9b",
    )

    texts = [
        part["text"]
        for item in items
        for part in item.get("content", [])
        if isinstance(part, dict) and "text" in part
    ]

    assert any("TAIL_MARKER_FOR_EXPANSION" in text for text in texts)


def test_read_tool_result_tool_returns_full_result(isolated_runtime) -> None:
    session = create_chat_session(title="Tool recall")
    message = append_chat_message(
        session_id=str(session["id"]),
        role="tool",
        content="full output from tool result",
        tool_name="bash",
        tool_arguments={"command": "echo hi"},
    )
    ref = parse_tool_result_reference(message["content"])

    result = execute_tool("read_tool_result", {"result_id": ref["result_id"]})

    assert result["status"] == "ok"
    assert result["text"] == "full output from tool result"
    assert result["tool_name"] == "bash"


def test_cleanup_old_results_removes_expired_files(isolated_runtime) -> None:
    stale_id = save_tool_result(
        "bash",
        {"command": "old"},
        "stale output",
        created_at="2020-01-01T00:00:00+00:00",
    )
    fresh_id = save_tool_result(
        "bash",
        {"command": "new"},
        "fresh output",
    )

    removed = cleanup_old_results(max_age_days=7)

    assert removed >= 1
    assert get_tool_result(stale_id) is None
    assert get_tool_result(fresh_id) is not None
