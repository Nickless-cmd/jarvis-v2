"""The Task facade derives authority from fixed runtime profiles."""
from __future__ import annotations


def test_read_task_derives_every_authority_field(monkeypatch):
    from core.services import agent_task_facade as task

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("container", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    plan = task.derive(
        owner_user_id="bjorn", origin_session_id="session-1", parent_run_id="run-1",
        parent_agent_id="jarvis", description="A cited answer", prompt="Inspect the source",
        subagent_type="researcher", model="", run_in_background=True,
    )
    assert plan["target"] == "runtime-container"
    assert plan["budget_tokens"] == 8000 and plan["max_turns"] == 8
    assert plan["expected_result"] == "A cited answer"
    assert "bash" not in plan["allowed_tools"] and "write_file" not in plan["allowed_tools"]
    assert plan["mandate"]["granted_side_effect"] == "read"
    assert plan["mandate"]["original_side_effect"] == "worktree-write"
    assert plan["mandate"]["return_address"] == "agent-inbox:bjorn:session-1:run-1"

