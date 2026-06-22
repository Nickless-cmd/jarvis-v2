"""Tests for the compact tool catalog (2026-06-22 redesign)."""
from unittest.mock import patch

from core.services import tool_catalog


def _fake_defs(names):
    return [{"function": {"name": n, "description": f"desc for {n}"}} for n in names]


def test_lists_core_tools_with_hint():
    defs = _fake_defs(
        ["read_file", "write_file", "bash", "db_query", "obscure_a", "obscure_b"]
    )
    with patch.object(tool_catalog, "get_tool_definitions", return_value=defs):
        tool_catalog.invalidate_cache()
        text = tool_catalog.build_catalog_text()
    # core tools listed individually
    assert "- read_file:" in text
    assert "- bash:" in text
    # non-core tools are NOT individually listed (that was the 445-line bloat)
    assert "obscure_a" not in text
    # discoverability preserved via the pointer
    assert "load_more_tools" in text
    assert "flere" in text  # "+N flere værktøjer"


def test_catalog_is_compact():
    defs = _fake_defs([f"tool_{i}" for i in range(400)] + ["read_file", "bash"])
    with patch.object(tool_catalog, "get_tool_definitions", return_value=defs):
        tool_catalog.invalidate_cache()
        text = tool_catalog.build_catalog_text()
    # only the curated core set is itemised, not all 402
    bullet_lines = [ln for ln in text.splitlines() if ln.startswith("- ")]
    assert len(bullet_lines) <= len(tool_catalog._CORE_TOOLS)


def test_token_estimate_positive():
    defs = _fake_defs(["read_file", "bash"])
    with patch.object(tool_catalog, "get_tool_definitions", return_value=defs):
        tool_catalog.invalidate_cache()
        assert tool_catalog.catalog_token_estimate() > 0
