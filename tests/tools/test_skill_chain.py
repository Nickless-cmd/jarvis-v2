"""Tests for the skill_chain tool."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def isolated_skills_root(monkeypatch, tmp_path):
    """Point SKILLS_ROOT at a fresh tmp dir + reset registry."""
    from core.services import skill_engine
    sk_root = tmp_path / "skills"
    sk_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(skill_engine, "SKILLS_ROOT", sk_root)
    monkeypatch.setattr(skill_engine, "_registry", {})
    monkeypatch.setattr(skill_engine, "_last_scan", "")
    return sk_root


def _write_skill(root: Path, name: str, body: str = "Test instructions.") -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test skill {name}\n---\n\n{body}\n",
        encoding="utf-8",
    )


# ── Validation tests ───────────────────────────────────────────────


def test_skill_chain_rejects_non_list_plan(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    result = _exec_skill_chain({"plan": "not-a-list"})
    assert result["status"] == "rejected"
    assert "must be a list" in result["reason"]


def test_skill_chain_rejects_too_short_plan(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    result = _exec_skill_chain({"plan": ["only-one"]})
    assert result["status"] == "rejected"
    assert "at least 2" in result["reason"]


def test_skill_chain_rejects_too_long_plan(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    result = _exec_skill_chain({"plan": ["a", "b", "c", "d", "e", "f"]})
    assert result["status"] == "rejected"
    assert "max length of 5" in result["reason"]


def test_skill_chain_rejects_empty_string_entry(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    result = _exec_skill_chain({"plan": ["valid", "  "]})
    assert result["status"] == "rejected"
    assert "non-empty strings" in result["reason"]


def test_skill_chain_rejects_non_string_entry(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    result = _exec_skill_chain({"plan": ["valid", 42]})
    assert result["status"] == "rejected"


def test_skill_chain_rejects_unknown_skills(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    _write_skill(isolated_skills_root, "real-skill")
    skill_engine.reload_skills()

    result = _exec_skill_chain({"plan": ["real-skill", "fake-foo", "fake-bar"]})
    assert result["status"] == "rejected"
    assert result["reason"] == "unknown skills in plan"
    assert set(result["missing"]) == {"fake-foo", "fake-bar"}
    assert "real-skill" in result["available"]


# ── Kill-switch ────────────────────────────────────────────────────


def test_skill_chain_returns_disabled_when_killswitched(monkeypatch, isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain

    class _FakeSettings:
        skill_chain_enabled = False

    monkeypatch.setattr(
        "core.tools.skill_chain_tool.load_settings",
        lambda: _FakeSettings(),
    )
    result = _exec_skill_chain({"plan": ["a", "b"]})
    assert result["status"] == "disabled"


# ── Successful chain ───────────────────────────────────────────────


def test_skill_chain_builds_combined_instructions(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    _write_skill(isolated_skills_root, "fact-checker", "Verify facts here.")
    _write_skill(isolated_skills_root, "markdown-helper", "Format as markdown.")
    skill_engine.reload_skills()

    result = _exec_skill_chain({
        "plan": ["fact-checker", "markdown-helper"],
        "rationale": "fact-check then format",
    })
    assert result["status"] == "ok"
    assert result["chain"] == ["fact-checker", "markdown-helper"]
    assert result["step_count"] == 2

    instructions = result["instructions"]
    assert "[skill_chain — 2 steps]" in instructions
    assert "## Step 1 of 2: fact-checker" in instructions
    assert "Verify facts here." in instructions
    assert "## Step 2 of 2: markdown-helper" in instructions
    assert "Format as markdown." in instructions
    assert "When you finish step 1, continue to step 2" in instructions


def test_skill_chain_normalizes_whitespace_in_names(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    _write_skill(isolated_skills_root, "fact-checker")
    _write_skill(isolated_skills_root, "markdown-helper")
    skill_engine.reload_skills()

    result = _exec_skill_chain({
        "plan": ["  fact-checker  ", " markdown-helper"],
    })
    assert result["status"] == "ok"
    assert result["chain"] == ["fact-checker", "markdown-helper"]


def test_skill_chain_allows_duplicate_skills_in_plan(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    _write_skill(isolated_skills_root, "fact-checker")
    skill_engine.reload_skills()

    result = _exec_skill_chain({"plan": ["fact-checker", "fact-checker"]})
    assert result["status"] == "ok"
    assert result["step_count"] == 2


def test_skill_chain_handles_max_length(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    for i in range(5):
        _write_skill(isolated_skills_root, f"skill-{i}")
    skill_engine.reload_skills()

    result = _exec_skill_chain({
        "plan": [f"skill-{i}" for i in range(5)],
    })
    assert result["status"] == "ok"
    assert result["step_count"] == 5


# ── Soft cap on instructions size ──────────────────────────────────


def test_skill_chain_warns_on_oversize_instructions(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    big_body = "x" * 20_000
    _write_skill(isolated_skills_root, "big-1", body=big_body)
    _write_skill(isolated_skills_root, "big-2", body=big_body)
    skill_engine.reload_skills()

    result = _exec_skill_chain({"plan": ["big-1", "big-2"]})
    assert result["status"] == "ok"
    assert "soft cap" in result["note"].lower() or "32000" in result["note"]


# ── Eventbus publication ───────────────────────────────────────────


def test_skill_chain_publishes_event_on_success(monkeypatch, isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    _write_skill(isolated_skills_root, "fact-checker")
    _write_skill(isolated_skills_root, "markdown-helper")
    skill_engine.reload_skills()

    published_events = []

    def _capture(family, payload):
        published_events.append((family, payload))

    monkeypatch.setattr(
        "core.tools.skill_chain_tool.event_bus",
        type("MockBus", (), {"publish": staticmethod(_capture)})(),
    )

    _exec_skill_chain({
        "plan": ["fact-checker", "markdown-helper"],
        "rationale": "this should not appear in event payload",
    })

    assert len(published_events) == 1
    family, payload = published_events[0]
    assert family == "cognitive_skill_chain.executed"
    assert payload["plan"] == ["fact-checker", "markdown-helper"]
    assert payload["step_count"] == 2
    assert "this should not appear" not in str(payload)
    assert payload["rationale_provided"] is True


def test_skill_chain_does_not_publish_on_rejection(monkeypatch, isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain

    published = []
    monkeypatch.setattr(
        "core.tools.skill_chain_tool.event_bus",
        type("MockBus", (), {"publish": staticmethod(lambda f, p: published.append((f, p)))})(),
    )

    _exec_skill_chain({"plan": ["only-one"]})
    assert len(published) == 0
