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
import hashlib
import hmac
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # DIAGNOSTIC: enable bridge debug logging

_DEFAULT_TIMEOUT_S = 30.0

# ── Cross-process dispatch (runtime-proces → api-proces) ────────────────
#
# bridge_registry er PER-PROCES. Desk-broens WS forbinder til jarvis-api
# (port 8080) og registreres KUN dér. Autonome/wakeup-runs kører i
# jarvis-runtime (port 8011) med sit EGET tomme registry → dispatch
# returnerer bridge_not_connected. Løsning: når en proces ikke har en
# lokal bro, HTTP-forwarder den dispatchen til api-procesen over localhost,
# beskyttet af localhost-only + shared-secret-header.

_INTERNAL_DISPATCH_PATH = "/api/internal/jarvisx-bridge/dispatch"
_INTERNAL_TOKEN_HEADER = "X-Jarvis-Internal-Token"


def internal_dispatch_token() -> str:
    """Shared-secret som BEGGE processer kan udlede ens.

    Foretræk en eksplicit konfigureret top-level ``internal_dispatch_token``
    i runtime.json. Hvis den mangler, udled en stabil token via HMAC over
    ``jarvisx_auth_secret`` (som begge processer allerede deler) — så ingen
    fil-skrivning er nødvendig og api/runtime når frem til SAMME værdi.
    """
    try:
        from core.runtime.secrets import read_runtime_key

        explicit = str(
            read_runtime_key(
                "internal_dispatch_token",
                env_override="JARVIS_INTERNAL_DISPATCH_TOKEN",
            )
        ).strip()
        if explicit:
            return explicit
    except Exception:
        pass

    # Udled stabilt fra et eksisterende delt secret.
    try:
        from core.runtime.secrets import read_runtime_key

        base = str(read_runtime_key("jarvisx_auth_secret")).strip()
    except Exception:
        base = ""
    if not base:
        # Sidste udvej: env (sat af opstart) eller tomt → dispatch fail-safe.
        base = os.environ.get("JARVIS_INTERNAL_DISPATCH_TOKEN", "")
    if not base:
        return ""
    return hmac.new(
        base.encode("utf-8"),
        b"jarvisx-internal-dispatch-v1",
        hashlib.sha256,
    ).hexdigest()


def _api_port() -> int:
    """Port for jarvis-api-procesen (hvor broen lever). Default 8080."""
    raw = os.environ.get("JARVIS_API_PORT", "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return 8080


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
        self._publish_presence()

    def unregister(self, conn: BridgeConnection) -> None:
        """Remove ONLY if the registered bridge for this user IS this conn.
        (Prevents tearing down a newer bridge when an older WS cleans up.)"""
        current = self._by_user.get(conn.user_id)
        if current is conn:
            conn.cancel_all_pending()
            del self._by_user[conn.user_id]
            logger.info("jarvisx_bridge: unregistered user=%s", conn.user_id)
            self._publish_presence()

    def _publish_presence(self) -> None:
        """Publicér dette registrys bro'er til shared_cache, så DEN ANDEN proces (og
        diagnosen) kan se hvilke user_id'er har en levende bro og hvor. Self-safe."""
        try:
            from core.services import bridge_presence
            bridge_presence.publish({
                uid: {
                    "client": c.client, "platform": c.platform, "version": c.version,
                    "capabilities": list(c.capabilities),
                }
                for uid, c in self._by_user.items()
            })
        except Exception:  # pragma: no cover - presence er blødt
            pass

    def _diagnose_no_bridge(self, user_id: str, *, stage: str) -> dict[str, Any]:
        """Fastslå HVORFOR der ikke er en bro for user_id (i stedet for et blindt
        'bridge_not_connected'): user_id-mismatch, ingen bro nogen steder, eller
        forward-fejl. Observeres i Centralen + logges, så vi ser den ægte grund når
        Bjørn reproducerer fra mobil. Self-safe."""
        try:
            from core.services import bridge_presence
            presence = bridge_presence.all_presence()
        except Exception:
            presence = {}
        local = list(self._by_user.keys())
        token = bool(internal_dispatch_token())
        if presence and user_id not in presence:
            reason = "user_id_mismatch"   # bro FINDES, men under et andet user_id
        elif not presence and not local:
            reason = "no_bridge_anywhere"  # ingen bro overhovedet (desk ikke forbundet)
        else:
            reason = "forward_failed"      # bro burde være nåelig, men rundturen fejlede
        detail = {
            "reason": reason, "stage": stage, "requesting_user_id": user_id,
            "token_present": token, "local_bridges": local,
            "presence_user_ids": list(presence.keys()),
        }
        try:
            from core.services.central_core import central
            central().observe({
                "cluster": "channel", "nerve": "bridge_dispatch_fail", "kind": "observe",
                "decision": "degraded", "reason": reason, **detail,
            })
        except Exception:  # pragma: no cover
            pass
        logger.warning(
            "[bridge-dispatch] NO_BRIDGE reason=%s stage=%s user=%s local=%s presence=%s token=%s",
            reason, stage, user_id, local, list(presence.keys()), token,
        )
        return detail

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
        allow_cross_process: bool = True,
    ) -> dict[str, Any]:
        """Send tool_invoke to user's bridge, await result or timeout.

        Returns {"status": "ok"|"error", "result": ..., "error": ...}.
        Never raises — errors are returned in the dict.

        ``allow_cross_process``: når der ikke findes en LOKAL bro for
        user_id, forward'es dispatchen over localhost-HTTP til api-procesen
        (hvor desk-broen lever). Det interne endpoint kalder dispatch med
        allow_cross_process=False, så api ALDRIG forwarder videre → ingen
        uendelig løkke. Fail-safe: enhver forward-fejl degraderer til
        bridge_not_connected (uændret adfærd når api reelt mangler broen).
        """
        bridge = self.get_bridge(user_id)
        if bridge is None:
            if allow_cross_process:
                # Deterministisk forward MEN konservativ: spring KUN forward over hvis
                # presence er populeret OG user_id definitivt fraværende (ægte mismatch/
                # ingen bro). Er presence tom/utilgængelig → bevar gammel adfærd (forward
                # til api), så den fungerende autonome-forward ikke brækkes.
                try:
                    from core.services import bridge_presence
                    presence = bridge_presence.all_presence()
                except Exception:
                    presence = {}
                if presence and user_id not in presence:
                    diag = self._diagnose_no_bridge(user_id, stage="pre_forward")
                    return {"status": "error", "result": None,
                            "error": "bridge_not_connected", "diagnosis": diag}
                return await self._forward_cross_process(
                    user_id=user_id,
                    tool=tool,
                    args=args,
                    timeout_s=timeout_s,
                )
            # api-siden (allow_cross_process=False): definitiv registry-opslag fejlede.
            diag = self._diagnose_no_bridge(user_id, stage="api_lookup")
            return {
                "status": "error",
                "result": None,
                "error": "bridge_not_connected",
                "diagnosis": diag,
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

    async def _forward_cross_process(
        self,
        *,
        user_id: str,
        tool: str,
        args: dict[str, Any],
        timeout_s: float,
    ) -> dict[str, Any]:
        """HTTP-forward dispatch til api-procesens interne endpoint.

        Self-safe: fanger ALT og degraderer til bridge_not_connected, så en
        forward-fejl (api nede, connection refused, timeout) aldrig hænger
        den autonome løkke og bevarer uændret adfærd når broen reelt mangler.
        """
        token = internal_dispatch_token()
        if not token:
            # Uden delt secret kan vi ikke forwarde sikkert → uændret adfærd.
            logger.warning(
                "[bridge-dispatch] CROSS_PROCESS_NO_TOKEN user=%s — bridge_not_connected",
                user_id,
            )
            return {"status": "error", "result": None, "error": "bridge_not_connected"}

        url = f"http://127.0.0.1:{_api_port()}{_INTERNAL_DISPATCH_PATH}"
        # Læse-timeout en anelse længere end operator-timeouten, så bro-rundturen
        # i api-procesen kan nå at fuldføre før vores HTTP-klient giver op.
        read_timeout = float(timeout_s) + 10.0
        try:
            import httpx

            timeout = httpx.Timeout(connect=3.0, read=read_timeout, write=5.0, pool=3.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    url,
                    json={
                        "user_id": user_id,
                        "tool": tool,
                        "args": args,
                        "timeout_s": timeout_s,
                    },
                    headers={_INTERNAL_TOKEN_HEADER: token},
                )
            if resp.status_code != 200:
                logger.warning(
                    "[bridge-dispatch] CROSS_PROCESS_HTTP_%s user=%s — bridge_not_connected",
                    resp.status_code, user_id,
                )
                return {"status": "error", "result": None, "error": "bridge_not_connected"}
            data = resp.json()
            if not isinstance(data, dict) or "status" not in data:
                return {"status": "error", "result": None, "error": "bridge_not_connected"}
            logger.info(
                "[bridge-dispatch] CROSS_PROCESS_OK user=%s tool=%s status=%s",
                user_id, tool, data.get("status"),
            )
            return data
        except Exception as exc:
            logger.warning(
                "[bridge-dispatch] CROSS_PROCESS_FAIL user=%s err=%s — bridge_not_connected",
                user_id, exc,
            )
            return {"status": "error", "result": None, "error": "bridge_not_connected"}


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
