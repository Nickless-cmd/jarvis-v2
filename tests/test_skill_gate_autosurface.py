"""Tests for skill_gate's optional `autosurface` arg (Fase 3, Task 4).

When true, candidates are narrowed to the owner-approved allowlist BEFORE
selection — used only by jarvis-code's client-driven first-turn auto-call.
Default false: every other caller (the model calling skill_gate directly)
is unchanged.
"""
from core.tools import skill_gate_tool
from core.services import skill_autosurface


def _fake_suggestions(**kwargs):
    return [
        {"name": "brand", "score": 0.6},
        {"name": "tdd", "score": 0.5},
    ]


def test_autosurface_false_unchanged(monkeypatch):
    monkeypatch.setattr(skill_gate_tool, "_suggest_skills_for_query", _fake_suggestions)
    monkeypatch.setattr(
        skill_gate_tool.skill_engine, "get_skill_instructions",
        lambda name: {"status": "ok", "instructions": "do X", "description": "", "use_when": "", "tags": []})
    monkeypatch.setattr(skill_gate_tool.skill_engine, "record_skill_usage", lambda *a, **kw: None)
    result = skill_gate_tool._exec_skill_gate({"query": "x"})
    assert result["gate_result"] == "invoked"
    assert result["skill_name"] == "brand"


def test_autosurface_filters_to_allowlist(monkeypatch):
    monkeypatch.setattr(skill_gate_tool, "_suggest_skills_for_query", _fake_suggestions)
    monkeypatch.setattr(skill_autosurface, "filter_to_approved", lambda names: ["tdd"])
    monkeypatch.setattr(
        skill_gate_tool.skill_engine, "get_skill_instructions",
        lambda name: {"status": "ok", "instructions": "do Y", "description": "", "use_when": "", "tags": []})
    monkeypatch.setattr(skill_gate_tool.skill_engine, "record_skill_usage", lambda *a, **kw: None)
    result = skill_gate_tool._exec_skill_gate({"query": "x", "autosurface": True})
    assert result["gate_result"] == "invoked"
    assert result["skill_name"] == "tdd"


def test_autosurface_empty_allowlist_no_match(monkeypatch):
    monkeypatch.setattr(skill_gate_tool, "_suggest_skills_for_query", _fake_suggestions)
    monkeypatch.setattr(skill_autosurface, "filter_to_approved", lambda names: [])
    result = skill_gate_tool._exec_skill_gate({"query": "x", "autosurface": True})
    assert result["gate_result"] == "no_match"
    assert result["status"] == "ok"


def test_schema_has_autosurface():
    props = skill_gate_tool.SKILL_GATE_TOOL_DEFINITIONS[0]["function"]["parameters"]["properties"]
    assert "autosurface" in props
