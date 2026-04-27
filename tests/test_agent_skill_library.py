"""Unit tests for agent_skill_library."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import core.services.agent_skill_library as asl


def test_get_skills_for_unknown_role(tmp_path, monkeypatch):
    monkeypatch.setattr(asl, "_SKILLS_ROOT", tmp_path)
    result = asl.get_skills("nonexistent")
    assert result["exists"] is False
    assert result["content"] == ""


def test_append_creates_file_with_section(tmp_path, monkeypatch):
    monkeypatch.setattr(asl, "_SKILLS_ROOT", tmp_path)
    monkeypatch.setattr(asl, "load_json", lambda *a, **k: [])
    monkeypatch.setattr(asl, "save_json", lambda k, v: None)
    result = asl.append_skill_observation(
        role="researcher", section="Workflows",
        observation="grep with type=py is fastest for imports",
    )
    assert result["status"] == "ok"
    assert "smut-" in result["mutation_id"]
    path = tmp_path / "researcher" / "skills.md"
    assert path.exists()
    content = path.read_text()
    assert "## Workflows" in content
    assert "grep with type=py" in content


def test_append_to_existing_section(tmp_path, monkeypatch):
    monkeypatch.setattr(asl, "_SKILLS_ROOT", tmp_path)
    monkeypatch.setattr(asl, "load_json", lambda *a, **k: [])
    monkeypatch.setattr(asl, "save_json", lambda k, v: None)
    asl.append_skill_observation(role="r", section="Workflows", observation="first one")
    asl.append_skill_observation(role="r", section="Workflows", observation="second one")
    content = (tmp_path / "r" / "skills.md").read_text()
    assert "first one" in content
    assert "second one" in content
    # Both should be under the same section header
    assert content.count("## Workflows") == 1


def test_append_to_new_section(tmp_path, monkeypatch):
    monkeypatch.setattr(asl, "_SKILLS_ROOT", tmp_path)
    monkeypatch.setattr(asl, "load_json", lambda *a, **k: [])
    monkeypatch.setattr(asl, "save_json", lambda k, v: None)
    asl.append_skill_observation(role="r", section="Workflows", observation="W")
    asl.append_skill_observation(role="r", section="Pitfalls", observation="P")
    content = (tmp_path / "r" / "skills.md").read_text()
    assert "## Workflows" in content
    assert "## Pitfalls" in content


def test_validates_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(asl, "_SKILLS_ROOT", tmp_path)
    result = asl.append_skill_observation(role="", section="x", observation="y")
    assert result["status"] == "error"
    result = asl.append_skill_observation(role="r", section="", observation="y")
    assert result["status"] == "error"


def test_rollback_restores_before_content(tmp_path, monkeypatch):
    monkeypatch.setattr(asl, "_SKILLS_ROOT", tmp_path)
    target = tmp_path / "r" / "skills.md"
    target.parent.mkdir()
    target.write_text("AFTER content", encoding="utf-8")
    fake_record = {
        "mutation_id": "smut-test",
        "role": "r",
        "target_path": str(target),
        "before_content": "BEFORE content",
        "after_content": "AFTER content",
        "rolled_back": False,
    }
    state = [fake_record]
    monkeypatch.setattr(asl, "load_json", lambda *a, **k: list(state))
    monkeypatch.setattr(asl, "save_json", lambda k, v: state.clear() or state.extend(v))
    result = asl.rollback_skill_mutation("smut-test")
    assert result["status"] == "ok"
    assert target.read_text() == "BEFORE content"


def test_list_known_roles_returns_dirs_with_skills_file(tmp_path, monkeypatch):
    monkeypatch.setattr(asl, "_SKILLS_ROOT", tmp_path)
    (tmp_path / "researcher").mkdir()
    (tmp_path / "researcher" / "skills.md").write_text("test")
    (tmp_path / "critic").mkdir()  # no skills file
    (tmp_path / "planner").mkdir()
    (tmp_path / "planner" / "skills.md").write_text("test")
    roles = asl.list_known_roles()
    assert "researcher" in roles
    assert "planner" in roles
    assert "critic" not in roles


def test_list_known_roles_handles_missing_root(tmp_path, monkeypatch):
    fake_root = tmp_path / "does_not_exist"
    monkeypatch.setattr(asl, "_SKILLS_ROOT", fake_root)
    assert asl.list_known_roles() == []
