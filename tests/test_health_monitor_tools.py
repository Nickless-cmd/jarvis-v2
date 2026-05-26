"""Smoke tests for health_monitor_tools.

Specifically guards against the ollama preset URL reverting from
127.0.0.1 back to the old 10.0.0.25 LXC.
"""
from __future__ import annotations


def test_ollama_preset_uses_localhost():
    """The 'ollama' preset endpoint must point at 127.0.0.1, not the
    pre-2026-05-26 LXC 107 (10.0.0.25)."""
    from core.tools.health_monitor_tools import _PRESET_ENDPOINTS
    assert "ollama" in _PRESET_ENDPOINTS
    url = _PRESET_ENDPOINTS["ollama"]
    assert url == "http://127.0.0.1:11434/api/tags", (
        f"ollama preset must be localhost, got {url!r}. See "
        "MEMORY.md reference_ollama_host.md for migration context."
    )
    assert "10.0.0.25" not in url


def test_module_imports_clean():
    from core.tools import health_monitor_tools  # noqa: F401
