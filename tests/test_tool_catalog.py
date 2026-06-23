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


def test_includes_self_management_and_operator_tools():
    # Bjørn 2026-06-23: Jarvis skal kunne huske sine self-styrings- + operator-værktøjer.
    defs = _fake_defs([
        "read_file", "restart_self", "schedule_self_wakeup", "operator_bash",
        "operator_screenshot", "operator_reminder",
    ])
    with patch.object(tool_catalog, "get_tool_definitions", return_value=defs):
        tool_catalog.invalidate_cache()
        text = tool_catalog.build_catalog_text()
    for must in ("restart_self", "schedule_self_wakeup", "operator_bash",
                 "operator_screenshot", "operator_reminder"):
        assert f"- {must}:" in text, must
    # grupperet med kategori-overskrifter
    assert "Selv-styring:" in text
    assert "Operator" in text


def test_core_tools_are_real_registered_names():
    # katalogen skjuler stille et tool hvis navnet ikke matcher en registreret def —
    # vagter mod at en omdøbning efterlader self/operator-tools usynlige igen.
    from core.tools.simple_tools import get_tool_definitions as _real
    registered = {
        ((d.get("function") or {}).get("name") or d.get("name") or "")
        for d in (_real() or [])
    }
    missing = [n for n in tool_catalog._CORE_TOOLS if n not in registered]
    assert missing == [], f"katalog-navne uden registreret tool: {missing}"


def test_token_estimate_positive():
    defs = _fake_defs(["read_file", "bash"])
    with patch.object(tool_catalog, "get_tool_definitions", return_value=defs):
        tool_catalog.invalidate_cache()
        assert tool_catalog.catalog_token_estimate() > 0
