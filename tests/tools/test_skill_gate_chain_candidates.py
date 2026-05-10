"""Tests for skill_gate's new chain_candidates / chain_hint fields."""
from __future__ import annotations

import pytest


# ── Pure helpers ───────────────────────────────────────────────────


def test_build_chain_candidates_empty_input():
    from core.tools.skill_gate_tool import _build_chain_candidates
    assert _build_chain_candidates([]) == []
    assert _build_chain_candidates([{"name": "x", "score": 0.5}]) == []


def test_build_chain_candidates_top_below_threshold():
    """Top score below 0.30 → no chain candidates (chain doesn't help weak match)."""
    from core.tools.skill_gate_tool import _build_chain_candidates
    suggestions = [
        {"name": "a", "score": 0.20},
        {"name": "b", "score": 0.18},
    ]
    assert _build_chain_candidates(suggestions) == []


def test_build_chain_candidates_only_top_within_window():
    """If only top-1 is within 0.10, no chain candidates returned."""
    from core.tools.skill_gate_tool import _build_chain_candidates
    suggestions = [
        {"name": "a", "score": 0.45},
        {"name": "b", "score": 0.20},  # 0.25 below — outside 0.10 window
    ]
    assert _build_chain_candidates(suggestions) == []


def test_build_chain_candidates_two_close_matches():
    from core.tools.skill_gate_tool import _build_chain_candidates
    suggestions = [
        {"name": "fact-checker", "score": 0.42},
        {"name": "markdown-helper", "score": 0.38},
        {"name": "deep-research", "score": 0.21},
    ]
    result = _build_chain_candidates(suggestions)
    assert len(result) == 2
    assert result[0]["name"] == "fact-checker"
    assert result[1]["name"] == "markdown-helper"


def test_build_chain_candidates_three_close_matches():
    from core.tools.skill_gate_tool import _build_chain_candidates
    suggestions = [
        {"name": "a", "score": 0.40},
        {"name": "b", "score": 0.36},
        {"name": "c", "score": 0.34},
        {"name": "d", "score": 0.20},
    ]
    result = _build_chain_candidates(suggestions)
    assert len(result) == 3
    assert [r["name"] for r in result] == ["a", "b", "c"]


def test_build_chain_candidates_caps_at_three():
    from core.tools.skill_gate_tool import _build_chain_candidates
    suggestions = [
        {"name": "a", "score": 0.40},
        {"name": "b", "score": 0.39},
        {"name": "c", "score": 0.38},
        {"name": "d", "score": 0.37},
    ]
    result = _build_chain_candidates(suggestions)
    assert len(result) == 3


def test_build_chain_hint_empty_returns_empty_string():
    from core.tools.skill_gate_tool import _build_chain_hint
    assert _build_chain_hint([]) == ""


def test_build_chain_hint_renders_skill_names():
    from core.tools.skill_gate_tool import _build_chain_hint
    candidates = [
        {"name": "fact-checker", "score": 0.42},
        {"name": "markdown-helper", "score": 0.38},
    ]
    hint = _build_chain_hint(candidates)
    assert "2 skills matched closely" in hint
    assert "fact-checker" in hint
    assert "markdown-helper" in hint
    assert "skill_chain(plan=" in hint


# ── Gate output integration ────────────────────────────────────────


def test_skill_gate_output_includes_chain_candidates_field(monkeypatch):
    from core.tools import skill_gate_tool

    class _FakeSettings:
        skill_gate_enabled = True
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: _FakeSettings(),
    )
    monkeypatch.setattr(
        skill_gate_tool, "_suggest_skills_for_query",
        lambda **kw: [
            {"name": "fact-checker", "score": 0.42, "candidate": "x"},
            {"name": "markdown-helper", "score": 0.38, "candidate": "y"},
        ],
    )

    from core.services import skill_engine
    monkeypatch.setattr(
        skill_engine, "get_skill_instructions",
        lambda name: {
            "status": "ok",
            "skill_name": name,
            "description": f"desc {name}",
            "use_when": "",
            "tags": [],
            "instructions": "test instructions",
        },
    )

    result = skill_gate_tool._exec_skill_gate({"query": "fact-check and format"})
    assert "chain_candidates" in result
    assert "chain_hint" in result
    assert len(result["chain_candidates"]) == 2
    assert "fact-checker" in result["chain_hint"]


def test_skill_gate_output_chain_candidates_empty_when_single_match(monkeypatch):
    from core.tools import skill_gate_tool

    class _FakeSettings:
        skill_gate_enabled = True
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: _FakeSettings(),
    )
    monkeypatch.setattr(
        skill_gate_tool, "_suggest_skills_for_query",
        lambda **kw: [
            {"name": "youtube-downloader", "score": 0.55, "candidate": "x"},
            {"name": "web-scraper", "score": 0.18, "candidate": "y"},
        ],
    )
    from core.services import skill_engine
    monkeypatch.setattr(
        skill_engine, "get_skill_instructions",
        lambda name: {
            "status": "ok",
            "skill_name": name,
            "description": "x",
            "use_when": "",
            "tags": [],
            "instructions": "x",
        },
    )

    result = skill_gate_tool._exec_skill_gate({"query": "download video"})
    assert result["chain_candidates"] == []
    assert result["chain_hint"] == ""


def test_skill_gate_output_chain_candidates_present_in_no_match(monkeypatch):
    from core.tools import skill_gate_tool

    class _FakeSettings:
        skill_gate_enabled = True
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: _FakeSettings(),
    )
    monkeypatch.setattr(
        skill_gate_tool, "_suggest_skills_for_query",
        lambda **kw: [],
    )

    result = skill_gate_tool._exec_skill_gate({"query": "what's the weather"})
    assert result["gate_result"] == "no_match"
    assert "chain_candidates" in result
    assert "chain_hint" in result
    assert result["chain_candidates"] == []
    assert result["chain_hint"] == ""
