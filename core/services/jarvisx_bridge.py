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
logger.setLevel(logging.DEBUG)  # DIAGNOSTIC: enable bridge debug logging

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
    # Pending entries: correlation_id → (future, owning_loop). The
    # owning_loop is needed because dispatch() may run from a worker
    # thread with its own event loop, while deliver_result() runs on
    # the main loop (where the WS handler lives). Without recording
    # the loop, set_result() fires on the wrong loop and the awaiter
    # never wakes up — tool-handler times out even though the bridge
    # replied correctly. See test_dispatch_cross_loop_safe.
    _pending: dict[str, tuple[asyncio.Future, asyncio.AbstractEventLoop]] = field(default_factory=dict)
    _send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def send_raw(self, data: dict, *, timeout_s: float = 10.0) -> None:
        """Send raw JSON over WS with lock and timeout.

        Uses _send_lock to prevent concurrent sends (heartbeat vs
        tool_invoke) and a timeout on the actual send to prevent
        permanent deadlock when the TCP connection is zombie (client
        disappeared without closing). Without this timeout,
        _send_lock is held forever, blocking ALL subsequent dispatches
        — the 'one-shot bug'.
        """
        if self.ws is None:
            raise RuntimeError("bridge_no_transport")
        async with self._send_lock:
            try:
                await asyncio.wait_for(
                    self.ws.send_json(data),
                    timeout=timeout_s,
                )
            except asyncio.TimeoutError:
                raise RuntimeError("bridge_send_timeout")

    async def send_invoke(
        self,
        *,
        correlation_id: str,
        tool: str,
        args: dict[str, Any],
        timeout_ms: int,
    ) -> None:
        """Send tool_invoke over WS and register the pending future."""
        # §17.6.1: medsend nuværende mode så broen kun eksekverer operator tools
        # lokalt i code mode. Tom scope → broen behandler det som legacy (tillader).
        try:
            from core.tools.tool_scoping import current_tool_scope
            mode = current_tool_scope() or ""
        except Exception:
            mode = ""
        await self.send_raw({
            "type": "tool_invoke",
            "correlation_id": correlation_id,
            "tool": tool,
            "args": args,
            "timeout_ms": timeout_ms,
            "mode": mode,
        })

    async def deliver_result(
        self,
        *,
        correlation_id: str,
        status: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        """Complete the pending future for this correlation_id.

        Marshals set_result onto the future's owning loop so cross-loop
        dispatch (e.g. tool-handler running in a worker thread with its
        own loop, while WS handler runs on the main loop) actually wakes
        the awaiter.
        """
        entry = self._pending.pop(correlation_id, None)
        if entry is None:
            logger.warning(
                "[bridge-dispatch] DELIVER_UNKNOWN corr=%s status=%s (no pending future)",
                correlation_id, status,
            )
            return
        fut, owning_loop = entry
        if fut.done():
            logger.warning(
                "[bridge-dispatch] DELIVER_ALREADY_DONE corr=%s status=%s",
                correlation_id, status,
            )
            return
        logger.debug(
            "[bridge-dispatch] DELIVER corr=%s status=%s pending=%d",
            correlation_id, status, len(self._pending),
        )
        payload = {"status": status, "result": result, "error": error}
        if owning_loop is asyncio.get_event_loop():
            fut.set_result(payload)
        else:
            # Cross-loop: schedule the set_result on the owning loop so
            # the worker-thread awaiter actually receives the wake-up.
            try:
                owning_loop.call_soon_threadsafe(fut.set_result, payload)
            except RuntimeError:
                # Loop closed already — drop result silently
                pass

    def cancel_all_pending(self, *, reason: str = "bridge_disconnected") -> None:
        """Cancel all in-flight calls (e.g. on WS disconnect)."""
        payload = {"status": "error", "result": None, "error": reason}
        for cid, entry in list(self._pending.items()):
            fut, owning_loop = entry
            if fut.done():
                continue
            try:
                if owning_loop.is_closed():
                    continue
                owning_loop.call_soon_threadsafe(
                    lambda f=fut, p=payload: (f.set_result(p) if not f.done() else None),
                )
            except RuntimeError:
                pass
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

    def list_user_ids(self) -> list[str]:
        """user_id'er med en aktiv bro (til bro_broker / override-switch)."""
        return list(self._by_user.keys())

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
        # Pair future with its owning loop so deliver_result can marshal
        # set_result correctly when WS handler runs on a different loop.
        bridge._pending[correlation_id] = (fut, loop)

        logger.debug(
            "[bridge-dispatch] START corr=%s tool=%s user=%s timeout=%.1fs pending=%d",
            correlation_id, tool, user_id, timeout_s, len(bridge._pending),
        )

        try:
            await bridge.send_invoke(
                correlation_id=correlation_id,
                tool=tool,
                args=args,
                timeout_ms=int(timeout_s * 1000),
            )
            logger.info("[bridge-dispatch] SENT corr=%s", correlation_id)
        except Exception as exc:
            bridge._pending.pop(correlation_id, None)
            logger.error("[bridge-dispatch] SEND_FAIL corr=%s err=%s", correlation_id, exc)
            return {
                "status": "error",
                "result": None,
                "error": f"bridge_send_failed: {exc!s}"[:200],
            }

        try:
            result = await asyncio.wait_for(fut, timeout=timeout_s)
            logger.debug(
                "[bridge-dispatch] RECV corr=%s status=%s pending=%d",
                correlation_id, result.get("status"), len(bridge._pending),
            )
            return result
        except asyncio.CancelledError:
            bridge._pending.pop(correlation_id, None)
            logger.warning(
                "[bridge-dispatch] CANCELLED corr=%s pending=%d",
                correlation_id, len(bridge._pending),
            )
            return {
                "status": "error",
                "result": None,
                "error": "bridge_call_cancelled",
            }
        except asyncio.TimeoutError:
            bridge._pending.pop(correlation_id, None)
            logger.error(
                "[bridge-dispatch] TIMEOUT corr=%s after %.1fs pending=%d",
                correlation_id, timeout_s, len(bridge._pending),
            )
            return {
                "status": "error",
                "result": None,
                "error": f"bridge_timeout after {timeout_s}s",
            }


# Module-level singleton — one registry per Python process
bridge_registry = BridgeRegistry()


# ── Main-loop reference (for thread-safe coroutine submission) ──────────
#
# The bridge's WebSocket lives on uvicorn's main asyncio loop. When sync
# tool-handlers want to call dispatch() from a worker thread, they need
# to run the coroutine ON the main loop (not on a thread-local loop) —
# otherwise ws.send_json races with concurrent traffic and the result
# delivery never wakes the awaiter.
#
# Use asyncio.run_coroutine_threadsafe(coro, get_main_loop()) from sync
# code, then call .result(timeout=...) on the returned concurrent.futures.
# Future. This gives us a clean thread → main-loop bridge.

_main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Register the main uvicorn loop. Called from app startup."""
    global _main_loop
    _main_loop = loop


def get_main_loop() -> Optional[asyncio.AbstractEventLoop]:
    """Return the registered main loop, or None if not set yet."""
    return _main_loop
