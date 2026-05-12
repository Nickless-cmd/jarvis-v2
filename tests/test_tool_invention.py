from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def isolated_skills_root(tmp_path, monkeypatch):
    """Point SKILLS_ROOT to an empty tmp dir, reload skills."""
    import core.services.skill_engine as se

    monkeypatch.setattr(se, "SKILLS_ROOT", tmp_path)
    se.reload_skills()
    return tmp_path


def test_validate_accepts_clean_proposal(isolated_skills_root):
    from core.services.skill_engine import validate_skill_proposal

    result = validate_skill_proposal(
        name="my-new-skill",
        description="Does X cleanly.",
        instructions="When triggered, do X by following these steps...",
        use_when="When user asks for X",
        tags=["productivity"],
    )
    assert result["status"] == "ok"


def test_validate_rejects_empty_name(isolated_skills_root):
    from core.services.skill_engine import validate_skill_proposal

    result = validate_skill_proposal(
        name="",
        description="x",
        instructions="x",
    )
    assert result["status"] == "error"
    assert "name" in result["error"].lower()


def test_validate_rejects_invalid_regex(isolated_skills_root):
    from core.services.skill_engine import validate_skill_proposal

    result = validate_skill_proposal(
        name="MyNewSkill!",
        description="x",
        instructions="x",
    )
    assert result["status"] == "error"


def test_validate_rejects_empty_description(isolated_skills_root):
    from core.services.skill_engine import validate_skill_proposal

    result = validate_skill_proposal(
        name="ok-name",
        description="",
        instructions="some instructions",
    )
    assert result["status"] == "error"


def test_validate_rejects_empty_instructions(isolated_skills_root):
    from core.services.skill_engine import validate_skill_proposal

    result = validate_skill_proposal(
        name="ok-name",
        description="ok description",
        instructions="",
    )
    assert result["status"] == "error"


def test_validate_rejects_duplicate_name(isolated_skills_root):
    from core.services.skill_engine import (
        create_skill,
        validate_skill_proposal,
    )

    create_skill(
        name="already-here",
        description="existing skill",
        instructions="existing instructions",
    )
    result = validate_skill_proposal(
        name="already-here",
        description="another",
        instructions="more",
    )
    assert result["status"] == "error"
    assert "already" in result["error"].lower() or "exist" in result["error"].lower()


def test_validate_rejects_name_shadowing_existing_tool(isolated_skills_root, monkeypatch):
    """Skill name must not collide with a registered tool name."""
    from core.services import skill_engine

    monkeypatch.setattr(
        skill_engine,
        "_collect_registered_tool_names",
        lambda: {"approve_plan", "propose_plan", "bash"},
    )

    result = skill_engine.validate_skill_proposal(
        name="approve-plan",
        description="x",
        instructions="x",
    )
    assert result["status"] == "error"
    assert "tool" in result["error"].lower() or "shadow" in result["error"].lower()


def test_create_skill_still_validates_via_helper(isolated_skills_root):
    """Regression: create_skill must still reject invalid input (it now
    delegates to validate_skill_proposal internally — single source of truth)."""
    from core.services.skill_engine import create_skill

    result = create_skill(
        name="BAD!NAME",
        description="x",
        instructions="x",
    )
    assert result["status"] == "error"


@pytest.fixture()
def clean_plan_state(tmp_path, monkeypatch):
    """Isolated state_store so plans don't pollute."""
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


def test_propose_plan_accepts_skill_data(clean_plan_state):
    from core.services.plan_proposals import propose_plan, _load_all

    skill_data = {
        "name": "my-skill",
        "description": "x",
        "instructions": "y",
        "use_when": "z",
        "tags": ["a"],
    }
    result = propose_plan(
        session_id="s1",
        title="Ny skill: my-skill",
        why="x",
        steps=["Install skill 'my-skill' (auto on approval)"],
        skill_data=skill_data,
    )
    assert result["status"] == "ok"
    plan_id = result["plan_id"]

    plans = _load_all()
    assert plans[plan_id]["skill_data"] == skill_data


def test_propose_plan_without_skill_data_works_unchanged(clean_plan_state):
    """Backwards compat: existing callers don't pass skill_data."""
    from core.services.plan_proposals import propose_plan, _load_all

    result = propose_plan(
        session_id="s1",
        title="Regular plan",
        why="x",
        steps=["step 1"],
    )
    assert result["status"] == "ok"
    plan_id = result["plan_id"]

    plans = _load_all()
    assert plans[plan_id].get("skill_data") is None
