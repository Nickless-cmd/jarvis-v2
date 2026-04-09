"""Tests for Jarvis MCP server tools."""
from __future__ import annotations

import asyncio
import importlib


def _get_mcp_server():
    mod = importlib.import_module("apps.api.jarvis_api.mcp_server")
    return importlib.reload(mod)


def _tool_names():
    mod = _get_mcp_server()
    tools = asyncio.run(mod.mcp.list_tools())
    return [t.name for t in tools]


def test_mcp_server_module_imports():
    """MCP server module imports without error."""
    mod = _get_mcp_server()
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "create_mcp_app")


def test_all_nine_tools_registered():
    names = _tool_names()
    expected = {
        "jarvis_memory_read",
        "jarvis_memory_write",
        "jarvis_chat_sessions",
        "jarvis_chat_history",
        "jarvis_identity",
        "jarvis_cognitive_state",
        "jarvis_retained_memories",
        "jarvis_events",
        "jarvis_chat",
    }
    assert expected.issubset(set(names)), f"Missing: {expected - set(names)}"
