"""Livscyklus-gate omkring en synlig async stream.

Holdes uden for ``visible_runs`` så kernestrømmen ikke også ejer prioriterings-
gateens enter/exit-protokol.
"""
from __future__ import annotations

from collections.abc import AsyncIterator


async def gate_visible_stream(inner_stream: AsyncIterator[str]) -> AsyncIterator[str]:
    """Hold visible-stream-gaten fra første iteration til generatorens exit."""
    try:
        from core.services.visible_stream_gate import (
            enter_visible_stream,
            exit_visible_stream,
        )
    except Exception:
        async for chunk in inner_stream:
            yield chunk
        return

    enter_visible_stream()
    try:
        async for chunk in inner_stream:
            yield chunk
    finally:
        exit_visible_stream()
