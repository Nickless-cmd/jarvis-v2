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


def test_resolve_plan_approved_creates_todos(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.agent_todos import list_todos

    r1 = propose_plan(
        session_id="s1", title="Build feature", why="needed",
        steps=["step 1", "step 2"],
    )
    plan_id = r1["plan_id"]

    r2 = resolve_plan(plan_id, decision="approved")
    assert r2["status"] == "ok"

    todos = list_todos("s1")
    assert len(todos) == 2
    assert all(t["plan_id"] == plan_id for t in todos)


def test_resolve_plan_approved_idempotent_on_retry(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.agent_todos import list_todos

    r1 = propose_plan(
        session_id="s1", title="Build", why="x", steps=["a", "b"],
    )
    plan_id = r1["plan_id"]

    resolve_plan(plan_id, decision="approved")
    r2 = resolve_plan(plan_id, decision="approved")
    assert r2["status"] == "error"
    todos = list_todos("s1")
    assert len(todos) == 2


def test_resolve_plan_dismissed_does_not_create_todos(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.agent_todos import list_todos

    r1 = propose_plan(session_id="s1", title="X", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="dismissed")
    assert list_todos("s1") == []


def test_resolve_plan_respects_killswitch(clean_state, monkeypatch):
    from core.services import plan_proposals as pp
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.agent_todos import list_todos

    class FakeSettings:
        plan_todo_auto_create_enabled = False

    monkeypatch.setattr(pp, "load_settings", lambda: FakeSettings())

    r1 = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    resolve_plan(r1["plan_id"], decision="approved")
    assert list_todos("s1") == []


def test_resolve_plan_uses_original_session_not_default(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.agent_todos import list_todos

    r1 = propose_plan(
        session_id="original-session-xyz",
        title="X", why="x", steps=["a", "b"],
    )
    resolve_plan(r1["plan_id"], decision="approved")
    assert len(list_todos("original-session-xyz")) == 2
    assert list_todos("_default") == []
    assert list_todos("some-other-session") == []


def test_mark_step_completed_appends_and_sorts(clean_state):
    from core.services.plan_proposals import propose_plan, mark_step_completed, _load_all

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b", "c"])
    plan_id = r["plan_id"]

    mark_step_completed(plan_id, 2)
    mark_step_completed(plan_id, 0)
    plan = _load_all()[plan_id]
    assert plan["completed_step_indices"] == [0, 2]


def test_mark_step_completed_idempotent(clean_state):
    from core.services.plan_proposals import propose_plan, mark_step_completed, _load_all

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    plan_id = r["plan_id"]

    mark_step_completed(plan_id, 0)
    mark_step_completed(plan_id, 0)
    plan = _load_all()[plan_id]
    assert plan["completed_step_indices"] == [0]


def test_mark_step_completed_auto_transitions_to_completed(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, mark_step_completed, _load_all,
    )

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    plan_id = r["plan_id"]
    resolve_plan(plan_id, decision="approved")

    mark_step_completed(plan_id, 0)
    assert _load_all()[plan_id]["status"] == "approved"

    mark_step_completed(plan_id, 1)
    assert _load_all()[plan_id]["status"] == "completed"


def test_set_todos_marks_step_completed_on_transition(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, _load_all,
    )
    from core.services.agent_todos import set_todos, list_todos

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    plan_id = r["plan_id"]
    resolve_plan(plan_id, decision="approved")

    todos = list_todos("s1")
    todos[0]["status"] = "completed"
    set_todos("s1", todos)

    plan = _load_all()[plan_id]
    assert 0 in plan["completed_step_indices"]


def test_update_todo_status_marks_step_completed(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, _load_all,
    )
    from core.services.agent_todos import update_todo_status, list_todos

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    plan_id = r["plan_id"]
    resolve_plan(plan_id, decision="approved")

    todos = list_todos("s1")
    update_todo_status("s1", todos[0]["id"], "completed")

    plan = _load_all()[plan_id]
    assert 0 in plan["completed_step_indices"]


def test_set_todos_does_not_double_mark_already_completed(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, _load_all,
    )
    from core.services.agent_todos import set_todos, list_todos

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    plan_id = r["plan_id"]
    resolve_plan(plan_id, decision="approved")

    todos = list_todos("s1")
    todos[0]["status"] = "completed"
    set_todos("s1", todos)
    todos2 = list_todos("s1")
    set_todos("s1", todos2)

    plan = _load_all()[plan_id]
    assert plan["completed_step_indices"].count(0) == 1
