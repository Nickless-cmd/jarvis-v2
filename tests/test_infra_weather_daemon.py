"""Smoke tests for infra_weather_daemon.

Specifically guards against the OLLAMA_HOST default reverting from
127.0.0.1 (post-migration localhost) back to the old 10.0.0.25 LXC.
"""
from __future__ import annotations

import os


def test_default_ollama_host_is_localhost():
    """Default OLLAMA_HOST in _network_latency must be 127.0.0.1.

    Was 10.0.0.25 before 2026-05-26 migration. Localhost is correct
    because Ollama now runs on the same host as Jarvis runtime.
    """
    src = open("core/services/infra_weather_daemon.py").read()
    assert 'os.environ.get("OLLAMA_HOST", "127.0.0.1")' in src, (
        "OLLAMA_HOST default must be 127.0.0.1 — see "
        "MEMORY.md reference_ollama_host.md for migration context"
    )
    assert '10.0.0.25' not in src, (
        "10.0.0.25 (defunct LXC 107) must not appear in infra_weather_daemon"
    )


def test_module_imports_clean():
    """Module imports without side-effects requiring runtime."""
    # Ensure clean import
    if "core.services.infra_weather_daemon" in list(__import__("sys").modules):
        del __import__("sys").modules["core.services.infra_weather_daemon"]
    from core.services import infra_weather_daemon  # noqa: F401
