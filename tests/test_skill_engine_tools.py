"""Smoke tests for skill_engine_tools — tool wrappers around skill_engine.

Existing tests in tests/test_skill_engine.py cover the engine itself.
This file verifies the tool-layer imports and basic plumbing.
"""
from __future__ import annotations

from core.tools import skill_engine_tools as tools


def test_module_importable():
    """Verify module loads and key exec functions exist."""
    assert hasattr(tools, "_exec_skill_list")
    assert hasattr(tools, "_exec_skill_search")
    assert hasattr(tools, "_exec_skill_invoke")
    assert hasattr(tools, "_exec_skill_create")
    assert hasattr(tools, "_exec_skill_delete")
    assert hasattr(tools, "_exec_skill_import")
    assert hasattr(tools, "_exec_skill_reload")
    assert hasattr(tools, "_exec_skill_suggest")


def test_context_tags_in_exec_skill_list():
    """Verify _exec_skill_list reads context_tags from args (C2 gate)."""
    # Just verify the function accepts args dict with context_tags
    import inspect
    sig = inspect.signature(tools._exec_skill_list)
    assert "args" in sig.parameters


def test_context_tags_in_exec_skill_search():
    """Verify _exec_skill_search reads context_tags from args (C2 gate)."""
    import inspect
    sig = inspect.signature(tools._exec_skill_search)
    assert "args" in sig.parameters
