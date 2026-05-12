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


def test_resolve_plan_approved_calls_create_skill(clean_plan_state, isolated_skills_root):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.skill_engine import skill_exists

    r = propose_plan(
        session_id="s1",
        title="Ny skill: install-this",
        why="testing",
        steps=["Install skill 'install-this' (auto on approval)"],
        skill_data={
            "name": "install-this",
            "description": "Does the install",
            "instructions": "When triggered, install something.",
            "use_when": "When asked",
            "tags": ["test"],
        },
    )
    plan_id = r["plan_id"]

    res = resolve_plan(plan_id, decision="approved")
    assert res["status"] == "ok"

    assert skill_exists("install-this") is True


def test_resolve_plan_dismissed_does_not_install_skill(clean_plan_state, isolated_skills_root):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.skill_engine import skill_exists

    r = propose_plan(
        session_id="s1",
        title="Ny skill: dont-install",
        why="x",
        steps=["x"],
        skill_data={
            "name": "dont-install",
            "description": "x",
            "instructions": "x",
            "use_when": "x",
            "tags": [],
        },
    )
    resolve_plan(r["plan_id"], decision="dismissed")
    assert skill_exists("dont-install") is False


def test_resolve_plan_without_skill_data_no_install_attempted(clean_plan_state, isolated_skills_root):
    """Backwards compat: plans without skill_data behave exactly as before."""
    from core.services.plan_proposals import propose_plan, resolve_plan

    r = propose_plan(
        session_id="s1",
        title="Regular plan",
        why="x",
        steps=["x"],
    )
    res = resolve_plan(r["plan_id"], decision="approved")
    assert res["status"] == "ok"


def test_resolve_plan_install_io_failure_logged_not_raised(
    clean_plan_state, isolated_skills_root, monkeypatch, caplog,
):
    """If create_skill raises at install time, resolve_plan logs but does
    not raise. Plan stays approved."""
    from core.services.plan_proposals import propose_plan, resolve_plan, _load_all
    import core.services.skill_engine as se

    def boom(**kwargs):
        raise IOError("disk full")
    monkeypatch.setattr(se, "create_skill", boom)

    r = propose_plan(
        session_id="s1",
        title="x",
        why="x",
        steps=["x"],
        skill_data={
            "name": "will-fail",
            "description": "x",
            "instructions": "x",
            "use_when": "x",
            "tags": [],
        },
    )
    plan_id = r["plan_id"]

    with caplog.at_level("ERROR"):
        res = resolve_plan(plan_id, decision="approved")
    assert res["status"] == "ok"

    plan = _load_all()[plan_id]
    assert plan["status"] == "approved"


def test_propose_new_skill_killswitch_returns_error(
    clean_plan_state, isolated_skills_root, monkeypatch,
):
    from core.tools import skill_engine_tools as set_

    class FakeSettings:
        tool_invention_enabled = False

    monkeypatch.setattr(set_, "load_settings", lambda: FakeSettings())

    result = set_._exec_propose_new_skill({
        "name": "x",
        "description": "x",
        "instructions": "x",
        "session_id": "s1",
    })
    assert result["status"] == "error"
    assert "disabled" in result["error"].lower()


def test_propose_new_skill_validation_failure_returns_error(
    clean_plan_state, isolated_skills_root,
):
    from core.tools import skill_engine_tools as set_

    result = set_._exec_propose_new_skill({
        "name": "BAD!NAME",
        "description": "x",
        "instructions": "x",
        "session_id": "s1",
    })
    assert result["status"] == "error"


def test_propose_new_skill_valid_proposal_creates_plan(
    clean_plan_state, isolated_skills_root,
):
    from core.tools import skill_engine_tools as set_
    from core.services.plan_proposals import _load_all

    result = set_._exec_propose_new_skill({
        "name": "auto-renamer",
        "description": "Renames files based on content",
        "instructions": "When given a file, rename it based on its content.",
        "use_when": "When user asks for batch rename",
        "tags": ["filesystem"],
        "session_id": "s1",
    })
    assert result["status"] == "ok"
    plan_id = result["plan_id"]

    plans = _load_all()
    assert plans[plan_id]["status"] == "awaiting_approval"
    assert plans[plan_id]["skill_data"]["name"] == "auto-renamer"


def test_propose_new_skill_registered_in_tool_definitions():
    """The new tool is exposed via SKILL_ENGINE_TOOL_DEFINITIONS
    and SKILL_ENGINE_TOOL_HANDLERS."""
    from core.tools.skill_engine_tools import (
        SKILL_ENGINE_TOOL_DEFINITIONS,
        SKILL_ENGINE_TOOL_HANDLERS,
    )

    names = [
        (entry.get("function") or {}).get("name")
        for entry in SKILL_ENGINE_TOOL_DEFINITIONS
        if isinstance(entry, dict)
    ]
    assert "propose_new_skill" in names
    assert "propose_new_skill" in SKILL_ENGINE_TOOL_HANDLERS
