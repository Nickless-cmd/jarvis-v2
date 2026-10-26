"""Durable mechanical mandate rows and side-effect ordering."""
from __future__ import annotations


def test_mandate_roundtrip_and_ordering(isolated_runtime):
    from core.runtime import db_agent_mandate as m

    row = m.record(assignment_id="asg-test", mandate={
        "mandate_id": "mnd-test", "owner_user_id": "bjorn",
        "origin_session_id": "session-test", "parent_run_id": "run-parent",
        "original_mandate_id": "origin:session-test", "target": "runtime-container",
        "workspace_roots": ["/work/repo"], "allowed_tools": ["read_file"],
        "tool_policy": "read-only-runtime", "granted_side_effect": "read",
        "original_side_effect": "worktree-write", "budget_tokens": 8000,
        "max_turns": 8, "max_depth": 0, "max_fanout": 0,
        "deadline_at": "2099-01-01T00:00:00+00:00", "expected_result": "answer",
        "return_address": "agent-inbox:bjorn:session-test:run-parent",
    })
    assert row == m.get(assignment_id="asg-test")
    assert row["allowed_tools"] == ["read_file"]
    assert m.side_effect_exceeds("worktree-write", "read") is True
    assert m.side_effect_exceeds("read", "worktree-write") is False

