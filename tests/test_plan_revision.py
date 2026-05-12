from __future__ import annotations

from datetime import UTC, datetime

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated state_store so plans don't pollute across tests."""
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


def test_propose_plan_seeds_new_phase2_fields(clean_state):
    """propose_plan now seeds revised_from/revision_reason/superseded_by=None."""
    from core.services.plan_proposals import propose_plan, _load_all

    r = propose_plan(
        session_id="s1", title="Original plan", why="x",
        steps=["step 1", "step 2"],
    )
    plans = _load_all()
    rec = plans[r["plan_id"]]
    assert rec.get("revised_from") is None
    assert rec.get("revision_reason") is None
    assert rec.get("superseded_by") is None


def test_revise_plan_errors_on_unknown_plan(clean_state):
    from core.services.plan_proposals import revise_plan

    result = revise_plan(
        plan_id="plan-does-not-exist",
        session_id="s1",
        reason="x",
        new_steps=["a"],
    )
    assert result["status"] == "error"
    assert "unknown" in result["error"].lower() or "not found" in result["error"].lower()


def test_revise_plan_errors_on_non_approved(clean_state):
    from core.services.plan_proposals import propose_plan, revise_plan

    r1 = propose_plan(
        session_id="s1", title="Still awaiting", why="x", steps=["a"],
    )
    result = revise_plan(
        plan_id=r1["plan_id"],
        session_id="s1",
        reason="changed mind",
        new_steps=["b"],
    )
    assert result["status"] == "error"
    assert "approved" in result["error"].lower()


def test_revise_plan_errors_on_empty_new_steps(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan

    r1 = propose_plan(session_id="s1", title="P1", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="approved")

    result = revise_plan(
        plan_id=r1["plan_id"],
        session_id="s1",
        reason="x",
        new_steps=[],
    )
    assert result["status"] == "error"


def test_revise_plan_errors_on_empty_reason(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan

    r1 = propose_plan(session_id="s1", title="P1", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="approved")

    result = revise_plan(
        plan_id=r1["plan_id"],
        session_id="s1",
        reason="",
        new_steps=["b"],
    )
    assert result["status"] == "error"
    assert "reason" in result["error"].lower()


def test_revise_plan_creates_new_with_revised_from(clean_state):
    """Happy path: revise creates new plan with revised_from + reason set,
    progress reset, skill_data=None, status=awaiting_approval."""
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan, _load_all, _save_all

    r1 = propose_plan(
        session_id="s1", title="Original", why="initial",
        steps=["step A", "step B", "step C"],
    )
    old_id = r1["plan_id"]
    resolve_plan(old_id, decision="approved")

    # Mark step 0 completed so we can verify progress resets
    plans = _load_all()
    plans[old_id]["completed_step_indices"] = [0]
    _save_all(plans)

    r2 = revise_plan(
        plan_id=old_id,
        session_id="s1",
        reason="context changed — different approach",
        new_steps=["new A", "new B"],
    )
    assert r2["status"] == "ok"
    new_id = r2["plan_id"]
    assert new_id != old_id

    plans_after = _load_all()
    new_rec = plans_after[new_id]
    assert new_rec["revised_from"] == old_id
    assert new_rec["revision_reason"] == "context changed — different approach"
    assert new_rec["completed_step_indices"] == []  # progress reset
    assert new_rec["status"] == "awaiting_approval"
    assert new_rec["steps"] == ["new A", "new B"]
    assert new_rec.get("skill_data") is None


def test_revise_plan_does_not_supersede_old_at_propose(clean_state):
    """Old plan remains approved until new revision is approved."""
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan, _load_all

    r1 = propose_plan(session_id="s1", title="P1", why="x", steps=["a"])
    old_id = r1["plan_id"]
    resolve_plan(old_id, decision="approved")

    revise_plan(
        plan_id=old_id,
        session_id="s1",
        reason="x",
        new_steps=["b"],
    )

    plans = _load_all()
    old_rec = plans[old_id]
    assert old_rec["status"] == "approved"  # unchanged
    assert old_rec.get("superseded_by") is None


def test_revise_plan_dedupe_returns_existing_pending(clean_state):
    """Second revise_plan of same plan_id returns the existing pending revision."""
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan

    r1 = propose_plan(session_id="s1", title="P1", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="approved")

    rev_a = revise_plan(
        plan_id=r1["plan_id"], session_id="s1",
        reason="reason a", new_steps=["new a"],
    )
    rev_b = revise_plan(
        plan_id=r1["plan_id"], session_id="s1",
        reason="reason b", new_steps=["new b"],
    )
    assert rev_b["status"] == "skipped_duplicate"
    assert rev_b["existing_plan_id"] == rev_a["plan_id"]


def test_revise_plan_respects_killswitch(clean_state, monkeypatch):
    from core.services import plan_proposals as pp
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan

    r1 = propose_plan(session_id="s1", title="P1", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="approved")

    class FakeSettings:
        plan_revision_enabled = False
        plan_todo_auto_create_enabled = True

    monkeypatch.setattr(pp, "load_settings", lambda: FakeSettings())

    result = revise_plan(
        plan_id=r1["plan_id"], session_id="s1",
        reason="x", new_steps=["b"],
    )
    assert result["status"] == "error"
    assert "disabled" in result["error"].lower()


def test_revise_plan_does_not_inherit_skill_data(clean_state):
    """If original plan had skill_data, revision MUST NOT inherit it."""
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan, _load_all

    skill_data = {
        "name": "test-skill",
        "description": "x",
        "instructions": "y",
        "use_when": "z",
        "tags": [],
    }
    r1 = propose_plan(
        session_id="s1", title="Install skill", why="x",
        steps=["install"], skill_data=skill_data,
    )
    resolve_plan(r1["plan_id"], decision="approved")

    r2 = revise_plan(
        plan_id=r1["plan_id"], session_id="s1",
        reason="change my mind on the skill",
        new_steps=["different step"],
    )
    new_rec = _load_all()[r2["plan_id"]]
    assert new_rec.get("skill_data") is None


def test_approving_revision_supersedes_old(clean_state):
    """When the revised plan is approved, old plan transitions to superseded."""
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, revise_plan, _load_all,
    )

    r1 = propose_plan(session_id="s1", title="Original", why="x", steps=["a", "b"])
    old_id = r1["plan_id"]
    resolve_plan(old_id, decision="approved")

    r2 = revise_plan(
        plan_id=old_id, session_id="s1",
        reason="changed", new_steps=["x", "y"],
    )
    new_id = r2["plan_id"]

    resolve_plan(new_id, decision="approved")

    plans = _load_all()
    assert plans[old_id]["status"] == "superseded"
    assert plans[old_id]["superseded_by"] == new_id
    assert plans[new_id]["status"] == "approved"


def test_dismissing_revision_preserves_old(clean_state):
    """When the revised plan is dismissed, old plan stays approved."""
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, revise_plan, _load_all,
    )

    r1 = propose_plan(session_id="s1", title="P", why="x", steps=["a"])
    old_id = r1["plan_id"]
    resolve_plan(old_id, decision="approved")

    r2 = revise_plan(
        plan_id=old_id, session_id="s1",
        reason="x", new_steps=["b"],
    )
    new_id = r2["plan_id"]

    resolve_plan(new_id, decision="dismissed")

    plans = _load_all()
    assert plans[old_id]["status"] == "approved"
    assert plans[old_id].get("superseded_by") is None
    assert plans[new_id]["status"] == "dismissed"


def test_approving_revision_creates_fresh_todos(clean_state):
    """The Phase 1 todo-creation hook still fires for revised plans."""
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan
    from core.services.agent_todos import list_todos

    r1 = propose_plan(session_id="s1", title="P", why="x", steps=["old-step"])
    resolve_plan(r1["plan_id"], decision="approved")

    r2 = revise_plan(
        plan_id=r1["plan_id"], session_id="s1",
        reason="x", new_steps=["new-step-1", "new-step-2"],
    )
    resolve_plan(r2["plan_id"], decision="approved")

    todos = list_todos("s1")
    new_todo_contents = [t["content"] for t in todos if t.get("plan_id") == r2["plan_id"]]
    assert "new-step-1" in new_todo_contents
    assert "new-step-2" in new_todo_contents


def test_approval_when_old_already_not_approved_is_graceful(clean_state):
    """Race condition: old plan manually moved out of approved before revision approved.
    Revision still approves; supersede hook no-ops on non-approved old."""
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, revise_plan, _load_all, _save_all,
    )

    r1 = propose_plan(session_id="s1", title="P", why="x", steps=["a"])
    old_id = r1["plan_id"]
    resolve_plan(old_id, decision="approved")

    r2 = revise_plan(
        plan_id=old_id, session_id="s1",
        reason="x", new_steps=["b"],
    )
    new_id = r2["plan_id"]

    # Manually mark old plan as completed (race condition)
    data = _load_all()
    data[old_id]["status"] = "completed"
    _save_all(data)

    result = resolve_plan(new_id, decision="approved")
    assert result["status"] == "ok"

    plans = _load_all()
    assert plans[old_id]["status"] == "completed"
    assert plans[old_id].get("superseded_by") is None
    assert plans[new_id]["status"] == "approved"
