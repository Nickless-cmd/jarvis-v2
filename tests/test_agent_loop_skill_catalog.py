"""Tests for the skill catalog injection into the /v1/agent/step system prompt
(Fase 3, Task 3). Injection is governed by skill_autosurface: with the flag
off or nothing approved, the catalog is empty and the prompt is unchanged
from today.
"""
from apps.api.jarvis_api.routes import agent_loop


def test_catalog_empty_when_flag_off(monkeypatch):
    monkeypatch.setattr(agent_loop.skill_autosurface, "filter_to_approved", lambda names: [])
    assert agent_loop._skill_catalog() == ""


def test_catalog_lists_approved_skills(monkeypatch):
    fake_skills = [
        {"name": "tdd", "use_when": "writing code", "tags": ["coding"]},
        {"name": "brand", "use_when": "brand voice", "tags": ["marketing"]},
    ]
    monkeypatch.setattr(agent_loop.skill_engine, "list_skills", lambda: fake_skills)
    monkeypatch.setattr(
        agent_loop.skill_autosurface, "filter_to_approved",
        lambda names: list(names))
    text = agent_loop._skill_catalog()
    assert "tdd" in text
    assert "writing code" in text
    assert "TILGÆNGELIGE SKILLS" in text
    assert len(text) < 1200


def test_catalog_respects_allowlist(monkeypatch):
    fake_skills = [
        {"name": "tdd", "use_when": "writing code", "tags": ["coding"]},
        {"name": "brand", "use_when": "brand voice", "tags": ["marketing"]},
    ]
    monkeypatch.setattr(agent_loop.skill_engine, "list_skills", lambda: fake_skills)
    monkeypatch.setattr(
        agent_loop.skill_autosurface, "filter_to_approved",
        lambda names: ["tdd"])
    text = agent_loop._skill_catalog()
    assert "tdd" in text
    assert "brand" not in text


def test_system_prompt_includes_catalog_and_instruction(monkeypatch):
    fake_skills = [{"name": "tdd", "use_when": "writing code", "tags": ["coding"]}]
    monkeypatch.setattr(agent_loop.skill_engine, "list_skills", lambda: fake_skills)
    monkeypatch.setattr(
        agent_loop.skill_autosurface, "filter_to_approved",
        lambda names: ["tdd"])
    prompt = agent_loop._build_system_prompt("identity", "fix a bug")
    assert "TILGÆNGELIGE SKILLS" in prompt
    assert "kald skill_gate" in prompt
    assert "Write → write_file" in prompt


def test_system_prompt_none_context_still_gets_catalog(monkeypatch):
    fake_skills = [{"name": "tdd", "use_when": "writing code", "tags": ["coding"]}]
    monkeypatch.setattr(agent_loop.skill_engine, "list_skills", lambda: fake_skills)
    monkeypatch.setattr(
        agent_loop.skill_autosurface, "filter_to_approved",
        lambda names: ["tdd"])
    prompt = agent_loop._build_system_prompt("none", "x")
    assert "TILGÆNGELIGE SKILLS" in prompt
