"""Tests for operator_tools (JarvisX bridge tool wrappers).

Most of the dispatch logic lives in core.services.jarvisx_bridge (tested
in test_jarvisx_bridge.py). These tests cover the thin wrapper layer.
"""
from __future__ import annotations

import pytest


def test_operator_read_file_sync_wrapper_exists():
    """The sync wrapper is what _exec_operator_read_file ultimately calls."""
    from core.tools import operator_tools
    assert hasattr(operator_tools, "operator_read_file")
    assert hasattr(operator_tools, "operator_read_file_async")


@pytest.mark.asyncio
async def test_async_wrapper_raises_on_bridge_not_connected():
    """When no bridge is registered for the user, async wrapper raises."""
    from core.services.jarvisx_bridge import bridge_registry
    bridge_registry.clear()

    from core.tools.operator_tools import operator_read_file_async
    with pytest.raises(RuntimeError, match="bridge_not_connected"):
        await operator_read_file_async(
            path="/tmp/x.txt", user_id="nobody", timeout_s=0.5,
        )
