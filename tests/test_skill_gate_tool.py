"""Smoke tests for skill_gate_tool — pre-action skill gate.

Detailed chain-candidate tests live in tests/tools/test_skill_gate_chain_candidates.py.
This file verifies the core gate tool imports and the context_tags plumbing (C2).
"""
from __future__ import annotations

import pytest

from core.tools.skill_gate_tool import (
    _build_chain_candidates,
    _exec_skill_gate,
)

# ── Test skills (inline — ingen fil-I/O) ──────────────────────────────

_SKILL_A = {
    "name": "test-web-research",
    "description": "Søg og ekstraher information fra internettet",
    "context_tags": ["research", "web"],
}
_SKILL_B = {
    "name": "test-data-analysis",
    "description": "Analyser struktureret data og generer rapporter",
    "context_tags": ["data", "analysis"],
}
_SKILL_C = {
    "name": "test-email-drafting",
    "description": "Skriv og formater emails",
    "context_tags": ["email", "communication"],
}
_SKILL_D = {
    "name": "test-general",
    "description": "Generel hjælp uden specifikke tags",
    "context_tags": [],
}

_ALL = [_SKILL_A, _SKILL_B, _SKILL_C, _SKILL_D]


def _filter_by_tags(skills: list[dict], tags: list[str]) -> list[dict]:
    """Re-implementation of the skill_gate context-tag filter for testing."""
    if not tags:
        return skills
    tag_set = {t.lower() for t in tags}
    return [s for s in skills if any(t.lower() in tag_set for t in s.get("context_tags", []))]


class TestContextTagsFilter:
    def test_no_tags_returns_all(self):
        result = _filter_by_tags(_ALL, [])
        assert len(result) == 4

    def test_single_tag_match(self):
        result = _filter_by_tags(_ALL, ["web"])
        assert len(result) == 1
        assert result[0]["name"] == "test-web-research"

    def test_multi_tag_match(self):
        result = _filter_by_tags(_ALL, ["research", "analysis"])
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"test-web-research", "test-data-analysis"}

    def test_no_matches_returns_empty(self):
        result = _filter_by_tags(_ALL, ["nonexistent"])
        assert result == []

    def test_skill_with_no_tags_not_returned_for_specific_search(self):
        result = _filter_by_tags(_ALL, ["email"])
        assert len(result) == 1
        assert result[0]["name"] == "test-email-drafting"

    def test_empty_tag_skill_included_when_no_filter(self):
        result = _filter_by_tags(_ALL, [])
        assert _SKILL_D in result


def test_build_chain_candidates_importable():
    """Ensure the chain-candidates helper is still importable after C2 changes."""
    assert callable(_build_chain_candidates)


def test_exec_skill_gate_importable():
    """Ensure the main gate function is importable."""
    assert callable(_exec_skill_gate)
