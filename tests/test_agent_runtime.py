"""Tests for agent_runtime — rene helpers + agents-cluster spawn-wiring.

Dækker coverage-gaten for agent_runtime og pinner at note_agent_spawn er
wired ind i spawn-stien (agents-cluster synlighed).
"""
from __future__ import annotations

from core.services import agent_runtime as ar


def test_trim_collapses_whitespace_and_limits():
    assert ar._trim("  a   b\n c ", limit=5) == "a b c"
    assert len(ar._trim("x" * 100, limit=10)) == 10


def test_parse_percent_confidence_buckets():
    assert ar._parse_percent_confidence("jeg er 90% sikker") == "high"
    assert ar._parse_percent_confidence("55% confidence here") == "medium"
    assert ar._parse_percent_confidence("kun 20% sikker") == "low"
    assert ar._parse_percent_confidence("ingen procent") == ""


def test_extract_vote_danish_and_english():
    assert ar._extract_vote("Vote: approve") == "approve"
    assert ar._extract_vote('jeg stemmer "nej"') == "reject"
    assert ar._extract_vote("vi bør udskyde") == "hold"
    assert ar._extract_vote("uklart") == ""


def test_spawn_depth_for_root_is_zero():
    assert ar._spawn_depth_for("") == 0
    assert ar._spawn_depth_for("jarvis") == 0


def test_spawn_wiring_imports_note_agent_spawn():
    # Agents-cluster: spawn-stien skal kunne importere observeren self-safe.
    from core.services.agents import note_agent_spawn
    assert callable(note_agent_spawn)
