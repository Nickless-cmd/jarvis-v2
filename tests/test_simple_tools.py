"""Smoke tests for simple_tools — focus on tool-registration invariants.

Specifically guards that operator_read_file remains registered in both
the TOOL_DEFINITIONS list (what the LLM sees) and the _TOOL_HANDLERS
dispatch map (what runs when invoked). Pre-2026-05-26 there was no
bridge-aware tool; this prevents accidental removal.
"""
from __future__ import annotations


def test_operator_read_file_registered():
    from core.tools.simple_tools import _TOOL_HANDLERS, get_tool_definitions
    assert "operator_read_file" in _TOOL_HANDLERS, (
        "operator_read_file must be in _TOOL_HANDLERS — see "
        "docs/superpowers/specs/2026-05-26-jarvisx-tool-bridge.md"
    )
    tools = get_tool_definitions() or []
    names = [t.get("function", {}).get("name", "") for t in tools]
    assert "operator_read_file" in names, (
        "operator_read_file must appear in TOOL_DEFINITIONS so the LLM "
        "can discover it. See jarvisx-tool-bridge spec."
    )


def test_phase2_operator_tools_registered():
    """All Phase 2 operator_* tools have both a TOOL_DEFINITIONS entry
    AND a _TOOL_HANDLERS handler."""
    from core.tools.simple_tools import _TOOL_HANDLERS, get_tool_definitions
    tools = get_tool_definitions() or []
    names = {t.get("function", {}).get("name", "") for t in tools}
    expected = {
        "operator_read_file",
        "operator_write_file",
        "operator_edit_file",
        "operator_glob",
        "operator_grep",
        "operator_list_dir",
    }
    missing_defs = expected - names
    missing_handlers = expected - set(_TOOL_HANDLERS.keys())
    assert not missing_defs, f"Missing in TOOL_DEFINITIONS: {missing_defs}"
    assert not missing_handlers, f"Missing in _TOOL_HANDLERS: {missing_handlers}"


def test_tool_definitions_well_formed():
    """Every tool def has function.name + function.description."""
    from core.tools.simple_tools import get_tool_definitions
    tools = get_tool_definitions() or []
    assert len(tools) > 0
    for t in tools[:10]:  # sample first 10 — full validation elsewhere
        assert t.get("type") == "function"
        fn = t.get("function") or {}
        assert fn.get("name"), f"missing name: {t}"
        assert fn.get("description"), f"missing description: {fn.get('name')}"
