"""Tests for app mounts — MCP server and OpenAI compat router."""
from __future__ import annotations

import importlib


def test_app_has_openai_compat_route():
    """The /v1/chat/completions route must be registered."""
    mod = importlib.import_module("apps.api.jarvis_api.app")
    mod = importlib.reload(mod)
    routes = [r.path for r in mod.app.routes if hasattr(r, "path")]
    assert "/v1/chat/completions" in routes


def test_app_has_mcp_mount():
    """The /mcp mount must exist."""
    mod = importlib.import_module("apps.api.jarvis_api.app")
    mod = importlib.reload(mod)
    mount_paths = [r.path for r in mod.app.routes if hasattr(r, "path")]
    assert "/mcp" in mount_paths
