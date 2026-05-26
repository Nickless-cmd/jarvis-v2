"""JarvisX tool-bridge — bidirectional dispatch over WebSocket.

When JarvisX-app (Electron, on operator's desktop) opens a WebSocket to
Jarvis-runtime, it registers as a "bridge" for its user. Runtime can then
dispatch tool invocations over that WS — JarvisX executes them locally
on the operator's desktop and returns results.

Spec: docs/superpowers/specs/2026-05-26-jarvisx-tool-bridge.md

Design notes:
  - One active bridge per user_id; newer registration replaces older.
  - Dispatch matches tool-invoke with tool-result via correlation_id
    (uuid4 generated per call, stored in pending-futures map).
  - Timeout per call (default 30s); on timeout the pending future is
    cancelled and result is {status: error, error: "bridge_timeout"}.
  - Bridge disconnect cancels all pending futures with bridge_disconnected.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S = 30.0


@dataclass
class BridgeConnection:
    """One live bridge connection. WS object is platform-dependent."""

    user_id: str
    client: str = "unknown"
    version: str = ""
    platform: str = ""
    capabilities: list[str] = field(default_factory=list)
    ws: Any = None  # FastAPI WebSocket, or a fake in tests
    _pending: dict[str, asyncio.Future] = field(default_factory=dict)

    async def send_invoke(
        self,
        *,
        correlation_id: str,
        tool: str,
        args: dict[str, Any],
        timeout_ms: int,
    ) -> None:
        """Send tool_invoke over WS and register the pending future."""
        if self.ws is None:
            raise RuntimeError("bridge_no_transport")
        await self.ws.send_json({
            "type": "tool_invoke",
            "correlation_id": correlation_id,
            "tool": tool,
            "args": args,
            "timeout_ms": timeout_ms,
        })

    async def deliver_result(
        self,
        *,
        correlation_id: str,
        status: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        """Complete the pending future for this correlation_id."""
        fut = self._pending.pop(correlation_id, None)
        if fut is None or fut.done():
            # Result for an unknown / already-completed correlation — drop
            return
        fut.set_result({"status": status, "result": result, "error": error})

    def cancel_all_pending(self, *, reason: str = "bridge_disconnected") -> None:
        """Cancel all in-flight calls (e.g. on WS disconnect)."""
        for cid, fut in list(self._pending.items()):
            if not fut.done():
                fut.set_result({"status": "error", "result": None, "error": reason})
        self._pending.clear()


class BridgeRegistry:
    """Process-local registry of active bridges, keyed by user_id."""

    def __init__(self) -> None:
        self._by_user: dict[str, BridgeConnection] = {}

    def register(self, conn: BridgeConnection) -> None:
        existing = self._by_user.get(conn.user_id)
        if existing is not None and existing is not conn:
            # Older bridge for same user: tear it down first.
            existing.cancel_all_pending(reason="bridge_replaced")
            logger.info(
                "jarvisx_bridge: replacing existing bridge user=%s", conn.user_id,
            )
        self._by_user[conn.user_id] = conn
        logger.info(
            "jarvisx_bridge: registered user=%s client=%s capabilities=%s",
            conn.user_id, conn.client, conn.capabilities,
        )

    def unregister(self, conn: BridgeConnection) -> None:
        """Remove ONLY if the registered bridge for this user IS this conn.
        (Prevents tearing down a newer bridge when an older WS cleans up.)"""
        current = self._by_user.get(conn.user_id)
        if current is conn:
            conn.cancel_all_pending()
            del self._by_user[conn.user_id]
            logger.info("jarvisx_bridge: unregistered user=%s", conn.user_id)

    def get_bridge(self, user_id: str) -> Optional[BridgeConnection]:
        return self._by_user.get(user_id)

    def clear(self) -> None:
        """Test helper — drop all registrations."""
        for conn in self._by_user.values():
            conn.cancel_all_pending(reason="registry_cleared")
        self._by_user.clear()

    async def dispatch(
        self,
        *,
        user_id: str,
        tool: str,
        args: dict[str, Any],
        timeout_s: float = _DEFAULT_TIMEOUT_S,
    ) -> dict[str, Any]:
        """Send tool_invoke to user's bridge, await result or timeout.

        Returns {"status": "ok"|"error", "result": ..., "error": ...}.
        Never raises — errors are returned in the dict.
        """
        bridge = self.get_bridge(user_id)
        if bridge is None:
            return {
                "status": "error",
                "result": None,
                "error": "bridge_not_connected",
            }

        correlation_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        fut: asyncio.Future = loop.create_future()
        bridge._pending[correlation_id] = fut

        try:
            await bridge.send_invoke(
                correlation_id=correlation_id,
                tool=tool,
                args=args,
                timeout_ms=int(timeout_s * 1000),
            )
        except Exception as exc:
            bridge._pending.pop(correlation_id, None)
            return {
                "status": "error",
                "result": None,
                "error": f"bridge_send_failed: {exc!s}"[:200],
            }

        try:
            return await asyncio.wait_for(fut, timeout=timeout_s)
        except asyncio.TimeoutError:
            bridge._pending.pop(correlation_id, None)
            return {
                "status": "error",
                "result": None,
                "error": f"bridge_timeout after {timeout_s}s",
            }


# Module-level singleton — one registry per Python process
bridge_registry = BridgeRegistry()
