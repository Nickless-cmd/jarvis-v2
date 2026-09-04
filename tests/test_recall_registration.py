"""Task 4 (memory repair 2026-09-04): `recall` is registered in chat scope and unified_recall is gone."""
from __future__ import annotations


def test_recall_is_in_chat_scope():
    from core.tools.tool_scoping import CHAT_MODE_TOOLS_BASE, allowed_tool_names

    assert "recall" in CHAT_MODE_TOOLS_BASE
    allow = allowed_tool_names(role="owner", scope="chat", all_names=["recall", "bash"])
    assert "recall" in allow and "bash" not in allow


def test_unified_recall_module_is_gone():
    import importlib.util

    assert importlib.util.find_spec("core.services.unified_recall") is None
