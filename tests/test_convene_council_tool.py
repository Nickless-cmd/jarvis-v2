from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch, MagicMock
from core.tools.simple_tools import execute_tool, get_tool_definitions


def test_convene_council_tool_registered():
    names = [t["function"]["name"] for t in get_tool_definitions()]
    assert "convene_council" in names


def test_quick_council_check_tool_registered():
    names = [t["function"]["name"] for t in get_tool_definitions()]
    assert "quick_council_check" in names


def test_convene_council_requires_topic():
    result = execute_tool("convene_council", {})
    assert result["status"] == "error"
    assert "topic" in result["error"]


def test_quick_council_check_requires_action():
    result = execute_tool("quick_council_check", {})
    assert result["status"] == "error"
    assert "action" in result["error"]


def test_convene_council_calls_runtime():
    mock_session = {"council_id": "council-test123"}
    mock_result = {
        "council_id": "council-test123",
        "summary": "Proceed with caution.",
        "members": [{"role": "critic", "position_summary": "Risky but manageable."}],
    }
    with patch("core.tools.simple_tools.create_council_session_runtime", return_value=mock_session, create=True), \
         patch("core.tools.simple_tools.run_council_round", return_value=mock_result, create=True):
        # Patch inside the handler's lazy imports
        import apps.api.jarvis_api.services.agent_runtime as ar
        orig_create = ar.create_council_session_runtime
        orig_run = ar.run_council_round
        ar.create_council_session_runtime = lambda **kw: mock_session
        ar.run_council_round = lambda cid: mock_result
        try:
            result = execute_tool("convene_council", {"topic": "Should I rewrite my soul file?"})
            assert result["status"] == "ok"
            assert result["council_id"] == "council-test123"
            assert "caution" in result["summary"]
            assert result["member_count"] == 1
        finally:
            ar.create_council_session_runtime = orig_create
            ar.run_council_round = orig_run


def test_quick_council_check_returns_objection():
    mock_agent_result = {
        "agent_id": "agent-xyz",
        "messages": [
            {"direction": "jarvis->agent", "content": "task brief"},
            {"direction": "agent->jarvis", "content": "This is risky. PROCEED"},
        ],
    }
    import apps.api.jarvis_api.services.agent_runtime as ar
    orig_spawn = ar.spawn_agent_task
    ar.spawn_agent_task = lambda **kw: mock_agent_result
    try:
        result = execute_tool("quick_council_check", {"action": "edit workspace MEMORY.md"})
        assert result["status"] == "ok"
        assert "objection" in result
        assert result["escalate_to_council"] is False
    finally:
        ar.spawn_agent_task = orig_spawn
