"""Operator-side tools — execute on operator's desktop via JarvisX bridge.

These tools route via `core.services.jarvisx_bridge` to the JarvisX
Electron-app running on the operator's local machine. They fail with
`bridge_not_connected` if the app is not running.

Phase 1 (this file): operator_read_file only. Spec:
docs/superpowers/specs/2026-05-26-jarvisx-tool-bridge.md
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S = 30.0


async def operator_read_file_async(
    *,
    path: str,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> str:
    """Read a file from the operator's desktop via JarvisX bridge.

    Raises RuntimeError if the bridge is not connected or the read fails.
    Returns the file contents on success.
    """
    from core.services.jarvisx_bridge import bridge_registry

    result = await bridge_registry.dispatch(
        user_id=user_id,
        tool="operator_read_file",
        args={"path": str(path)},
        timeout_s=timeout_s,
    )

    if result.get("status") != "ok":
        err = str(result.get("error") or "unknown")
        raise RuntimeError(f"operator_read_file failed: {err}")

    return str(result.get("result") or "")


def operator_read_file(*, path: str, user_id: str, timeout_s: float = _DEFAULT_TIMEOUT_S) -> str:
    """Synchronous wrapper for tool-loop callers that aren't async-native."""
    return asyncio.run(
        operator_read_file_async(path=path, user_id=user_id, timeout_s=timeout_s)
    )
