"""spawn_agent_task-vaerktoejet: herkomst fra turen (agent-contract-v1 B)."""
from __future__ import annotations

import pytest


def test_spawn_tool_forwards_run_provenance_as_context(monkeypatch):
    import core.services.agent_runtime as ar
    from core.tools.simple_tools_agent_spawn import _exec_spawn_agent_task

    seen = {}
    monkeypatch.setattr(ar, "spawn_agent_task",
                        lambda **kw: seen.update(kw) or {"agent_id": "a", "messages": []})
    _exec_spawn_agent_task({"goal": "x", "_runtime_session_id": "s9",
                            "_runtime_turn_id": "run-9", "_runtime_user_id": "bjorn"})
    assert seen["context"] == {"parent_session_id": "s9", "parent_run_id": "run-9",
                               "user_id": "bjorn"}
    seen.clear()
    _exec_spawn_agent_task({"goal": "x"})
    assert seen["context"] == {}


@pytest.mark.parametrize("args,expected", [
    ({"_runtime_session_id": " s ", "_runtime_turn_id": "r", "_runtime_user_id": "u"},
     {"parent_session_id": "s", "parent_run_id": "r", "user_id": "u"}),
    ({"_runtime_session_id": "s"}, {"parent_session_id": "s"}),
    ({"_runtime_user_id": None, "_runtime_turn_id": ""}, {}),
])
def test_herkomst_drops_empty_values_and_never_invents_an_owner(args, expected):
    from core.tools.simple_tools_agent_spawn import _herkomst

    assert _herkomst(args) == expected


def test_reexported_from_simple_tools_native():
    from core.tools import simple_tools_agent_spawn as new
    from core.tools import simple_tools_native as old

    assert old._exec_spawn_agent_task is new._exec_spawn_agent_task
