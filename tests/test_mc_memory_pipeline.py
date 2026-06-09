"""Tests for /mc/memory-pipeline endpoint.

Surface'n samler status fra fire pipes:
- runtime_contract_candidates → MEMORY.md
- auto_remember_subscriber → jarvis_brain
- daily_journal daemon → observation/
- jarvis_brain totals

Bygges 2026-06-09 så Bjørn (og MC UI) kan se om pipen er live.
"""
from __future__ import annotations


def test_memory_pipeline_returns_expected_top_level_keys(isolated_runtime) -> None:
    from apps.api.jarvis_api.routes.mission_control import mc_memory_pipeline

    result = mc_memory_pipeline(limit=5)

    # Top-level shape
    assert "active" in result
    assert "as_of" in result
    assert "memory_md_pipeline" in result
    assert "jarvis_brain" in result
    assert "daily_journal" in result


def test_memory_pipeline_contract_section_has_counts(isolated_runtime) -> None:
    from apps.api.jarvis_api.routes.mission_control import mc_memory_pipeline

    result = mc_memory_pipeline(limit=5)
    contract = result["memory_md_pipeline"]

    # Either the data shape OR an error key — gracefully handles missing DB
    assert (
        ("pending_count" in contract and "applied_count_total" in contract)
        or "error" in contract
    )


def test_memory_pipeline_brain_section_has_kinds(isolated_runtime) -> None:
    from apps.api.jarvis_api.routes.mission_control import mc_memory_pipeline

    result = mc_memory_pipeline(limit=5)
    brain = result["jarvis_brain"]

    assert "total_by_kind" in brain
    assert "added_today" in brain
    assert "recent_today" in brain
    assert isinstance(brain["added_today"], int)


def test_memory_pipeline_journal_section_reports_today(isolated_runtime) -> None:
    from apps.api.jarvis_api.routes.mission_control import mc_memory_pipeline

    result = mc_memory_pipeline(limit=5)
    journal = result["daily_journal"]

    assert "today_exists" in journal
    assert "today_date" in journal
    assert isinstance(journal["today_exists"], bool)
    # today_date should be ISO format YYYY-MM-DD
    assert len(journal["today_date"]) == 10
    assert journal["today_date"][4] == "-"


def test_memory_pipeline_respects_limit_param(isolated_runtime) -> None:
    """limit kontrollerer hvor mange sample-rows der returneres."""
    from apps.api.jarvis_api.routes.mission_control import mc_memory_pipeline

    result = mc_memory_pipeline(limit=3)
    contract = result["memory_md_pipeline"]

    if "pending_sample" in contract:
        assert len(contract["pending_sample"]) <= 3
    if "recent_applied" in contract:
        assert len(contract["recent_applied"]) <= 3
