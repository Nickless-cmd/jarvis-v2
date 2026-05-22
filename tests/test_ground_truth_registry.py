"""Tests for Lag 3 — Ground Truth Registry (ground_truth_registry.py).

Tests fall into two categories:
  1. Pure function tests that don't need external resources (isolation OK)
  2. Collector tests that DO touch subprocess/sqlite (skip in CI)
"""

from __future__ import annotations

import pytest

from core.services.ground_truth_registry import (
    _HOSTNAME_PATTERN,
    _IP_PATTERN,
    _NUMBER_PATTERN,
    get_ground_truth,
    ground_truth_summary,
    verify_system_claim,
    verify_stats_claim,
)


# ── Pattern tests (pure) ──────────────────────────────────────────────

def test_number_pattern_matches_expression():
    """NUMBER_PATTERN should match '42 expressions' (s outside capture)."""
    m = _NUMBER_PATTERN.search("42 expressions")
    assert m is not None
    assert m.group(1) == "42"
    assert m.group(2).lower() == "expression"  # s? outside capture group


def test_number_pattern_matches_daemon():
    """NUMBER_PATTERN should match '45 daemons'."""
    m = _NUMBER_PATTERN.search("45 daemons")
    assert m is not None
    assert m.group(1) == "45"


def test_number_pattern_matches_commit():
    """NUMBER_PATTERN should match '2500 commits'."""
    m = _NUMBER_PATTERN.search("2500 commits")
    assert m is not None
    assert m.group(1) == "2500"


def test_number_pattern_no_match():
    """NUMBER_PATTERN should NOT match text without numbers."""
    assert _NUMBER_PATTERN.search("ingen tal her") is None


def test_ip_pattern_matches_valid_ip():
    """IP_PATTERN should match a valid IPv4."""
    m = _IP_PATTERN.search("server 10.0.0.2")
    assert m is not None
    assert m.group(1) == "10.0.0.2"


def test_ip_pattern_no_match():
    """IP_PATTERN should NOT match non-IP text."""
    assert _IP_PATTERN.search("ingen ip her") is None


def test_hostname_pattern_matches_pve():
    """HOSTNAME_PATTERN should match 'pve'."""
    assert _HOSTNAME_PATTERN.search("kører på PVE") is not None


def test_hostname_pattern_matches_chefone():
    """HOSTNAME_PATTERN should match 'chefone'."""
    assert _HOSTNAME_PATTERN.search("chefone maskinen") is not None


def test_hostname_pattern_matches_jarvis():
    """HOSTNAME_PATTERN should match 'jarvis'."""
    assert _HOSTNAME_PATTERN.search("jarvis server") is not None


# ── verify_system_claim (pure logic, relies on cache) ───────────────

def test_verify_system_claim_returns_tuple():
    """verify_system_claim should always return a (bool, str|None) tuple."""
    result = verify_system_claim("10.0.0.2")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert result[1] is None or isinstance(result[1], str)


def test_verify_system_claim_unknown_passes():
    """Unknown system claims that don't match any pattern should pass (True)."""
    ok, _ = verify_system_claim("noget helt andet")
    assert ok is True


def test_verify_system_claim_model_mention_passes():
    """Model mentions should pass (fuzzy match with key words)."""
    ok, _ = verify_system_claim("deepseek v4 flash model")
    assert ok is True


# ── verify_stats_claim (pure logic with fallback) ────────────────────

def test_verify_stats_claim_returns_tuple():
    """verify_stats_claim should always return a (bool, str|None) tuple."""
    result = verify_stats_claim("42 expressions")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_verify_stats_claim_no_stats_pass():
    """Text without stats patterns should pass through."""
    ok, _ = verify_stats_claim("helt almindelig tekst")
    assert ok is True


def test_verify_stats_claim_empty():
    """Empty string should pass through."""
    ok, _ = verify_stats_claim("")
    assert ok is True


# ── get_ground_truth (cached collector) ──────────────────────────────

def test_get_ground_truth_returns_dict():
    """get_ground_truth should return a dict with expected keys."""
    gt = get_ground_truth()
    assert isinstance(gt, dict)
    # Core keys should exist
    expected_keys = {"repo_path", "head_sha", "collected_at", "os_info"}
    assert expected_keys.issubset(gt.keys()), f"Missing keys: {expected_keys - gt.keys()}"


def test_get_ground_truth_key_access():
    """get_ground_truth with a specific key should return the value."""
    repo = get_ground_truth("repo_path")
    assert repo is not None
    assert "jarvis-v2" in str(repo)


def test_get_ground_truth_nonexistent_key():
    """get_ground_truth with nonexistent key should return None."""
    val = get_ground_truth("ikke-eksisterende-nøgle")
    assert val is None


# ── ground_truth_summary ─────────────────────────────────────────────

def test_ground_truth_summary_returns_string():
    """ground_truth_summary should return a non-empty string."""
    summary = ground_truth_summary()
    assert isinstance(summary, str)
    assert len(summary) > 10


def test_ground_truth_summary_contains_keys():
    """Summary should contain key labels."""
    summary = ground_truth_summary()
    assert "Model" in summary
    assert "Repository" in summary or "Host" in summary


class TestDbPathPointsToRuntimeDb:
    """2026-05-22 (Claude): regression test for Codex' finding that
    DB_PATH pointed at /media/projects/jarvis-v2/state/jarvis.db (0 bytes)
    instead of ~/.jarvis-v2/state/jarvis.db (the live runtime DB)."""

    def test_db_path_under_jarvis_home(self):
        from core.services.ground_truth_registry import DB_PATH, JARVIS_HOME
        # Path must be relative to JARVIS_HOME, not REPO_PATH
        assert str(DB_PATH).startswith(str(JARVIS_HOME)), (
            f"DB_PATH={DB_PATH} must live under JARVIS_HOME={JARVIS_HOME}, "
            f"not under the repo path (stale empty file)"
        )

    def test_db_path_filename_is_jarvis_db(self):
        from core.services.ground_truth_registry import DB_PATH
        assert DB_PATH.name == "jarvis.db"


class TestProviderHealthSectionStable:
    """2026-05-22 (Claude): timestamp removed from health_section since
    it broke DeepSeek's prompt cache. Lives in provider_health_check,
    tested here to keep watchdog over cache-stability invariants near
    the GTR file (related concept).
    """

    def test_health_section_has_no_clock_timestamp(self):
        """Section text must not contain HH:MM:SS clock pattern."""
        import re
        from core.services.provider_health_check import health_section
        section = health_section()
        if section is None:
            return  # nothing to check when all providers reachable
        # Pattern \d{1,2}:\d{2}:\d{2} = clock timestamp; must not appear
        assert not re.search(r"\d{1,2}:\d{2}:\d{2}", section), (
            f"Health section must not contain a clock timestamp "
            f"(breaks prompt cache): {section!r}"
        )
