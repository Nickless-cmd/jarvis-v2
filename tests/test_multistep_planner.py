from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated state_store backed by tmp_path so plans/todos don't pollute."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import importlib
    import core.runtime.state_store as ss
    importlib.reload(ss)
    import core.services.plan_proposals as pp
    importlib.reload(pp)
    import core.services.agent_todos as at
    importlib.reload(at)
    return None


def test_propose_plan_seeds_completed_step_indices(clean_state):
    from core.services.plan_proposals import propose_plan, _load_all

    result = propose_plan(
        session_id="s1", title="Test plan", why="testing",
        steps=["step 1", "step 2", "step 3"],
    )
    assert result["status"] == "ok"
    plan_id = result["plan_id"]
    plans = _load_all()
    assert plans[plan_id]["completed_step_indices"] == []


def test_create_from_plan_appends_todos(clean_state):
    from core.services.agent_todos import create_from_plan, list_todos

    result = create_from_plan(
        plan_id="plan-abc",
        session_id="s1",
        steps=["step 1", "step 2", "step 3"],
    )
    assert result["status"] == "ok"
    assert result["count"] == 3

    todos = list_todos("s1")
    assert len(todos) == 3
    assert all(t["plan_id"] == "plan-abc" for t in todos)
    assert [t["plan_step_index"] for t in todos] == [0, 1, 2]
    assert all(t["status"] == "pending" for t in todos)
    assert todos[0]["content"] == "step 1"


def test_create_from_plan_is_idempotent(clean_state):
    from core.services.agent_todos import create_from_plan, list_todos

    create_from_plan(plan_id="plan-abc", session_id="s1", steps=["a", "b"])
    result2 = create_from_plan(plan_id="plan-abc", session_id="s1", steps=["a", "b"])
    assert result2["status"] == "ok"
    assert result2.get("skipped") is True
    todos = list_todos("s1")
    assert len(todos) == 2  # no duplicates


def test_create_from_plan_empty_steps_noop(clean_state):
    from core.services.agent_todos import create_from_plan, list_todos

    result = create_from_plan(plan_id="plan-abc", session_id="s1", steps=[])
    assert result["status"] == "ok"
    assert result.get("count") == 0
    assert list_todos("s1") == []


def test_create_from_plan_caps_content_length(clean_state):
    from core.services.agent_todos import create_from_plan, list_todos

    long_step = "x" * 500
    create_from_plan(plan_id="plan-abc", session_id="s1", steps=[long_step])
    todos = list_todos("s1")
    assert len(todos[0]["content"]) == 240
