"""WebSocket endpoint for JarvisX tool-bridge.

JarvisX Electron-app connects here over WS, registers as a bridge for
its user_id, then receives tool_invoke messages and sends back
tool_result messages. Spec: docs/superpowers/specs/2026-05-26-jarvisx-tool-bridge.md
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from core.services.jarvisx_bridge import (
    BridgeConnection,
    bridge_registry,
    internal_dispatch_token,
    _INTERNAL_TOKEN_HEADER,
)

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

# Localhost-værter der må kalde det interne dispatch-endpoint. Endpointet
# kører bash/file-ops på ejerens maskine via broen → RCE-overflade. api'en
# binder 127.0.0.1:8080 (ikke eksternt nåbar), men vi tjekker host'en
# defensivt OGSÅ, så en fejlkonfigureret proxy/bind ikke eksponerer den.
_LOCALHOST_HOSTS = {"127.0.0.1", "::1", "localhost"}


@router.post("/api/internal/jarvisx-bridge/dispatch")
async def internal_dispatch(request: Request) -> JSONResponse:
    """Intern cross-process dispatch (runtime-proces → api-proces).

    Ligger under ``/api/internal/`` → fritaget bearer-token-middleware'en
    (jarvisx_user_routing._PUBLIC_PATHS): runtime-processen er en service,
    ikke en bruger, og kan ikke bære et bruger-token. Hver /api/internal/-
    rute håndhæver SELV loopback-only (konvention, jf. internal_discord.py).

    SIKKERHED (kritisk — kører bash på ejerens maskine):
      1. Localhost-only: afvis enhver klient-host ≠ 127.0.0.1/::1/localhost.
      2. Afvis proxy-forwarded (X-Forwarded-For/Forwarded) — ville betyde
         at Caddy/en proxy videresendte et eksternt kald.
      3. Shared-secret: kræv korrekt X-Jarvis-Internal-Token-header
         (constant-time-sammenligning). Begge processer udleder samme token.

    Kalder dispatch med allow_cross_process=False → api forwarder ALDRIG
    videre → ingen uendelig løkke. Returnerer dispatch-dict'en som JSON.
    """
    # 1) Localhost-only host-tjek.
    client_host = request.client.host if request.client else None
    if client_host not in _LOCALHOST_HOSTS:
        logger.warning(
            "internal-dispatch: rejected non-localhost host=%s", client_host,
        )
        return JSONResponse({"error": "forbidden"}, status_code=403)

    # 2) Afvis proxy-videresendte kald (loopback-bind alene narres af en
    # fejlkonfigureret proxy; X-Forwarded-For/Forwarded afslører den).
    if request.headers.get("x-forwarded-for") or request.headers.get("forwarded"):
        logger.warning("internal-dispatch: rejected proxy-forwarded request")
        return JSONResponse({"error": "forbidden"}, status_code=403)

    # 3) Shared-secret-header (constant-time).
    import hmac as _hmac

    expected = internal_dispatch_token()
    provided = request.headers.get(_INTERNAL_TOKEN_HEADER, "")
    if not expected or not provided or not _hmac.compare_digest(provided, expected):
        logger.warning("internal-dispatch: rejected bad/missing token")
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "bad_json"}, status_code=400)

    user_id = str(body.get("user_id") or "").strip()
    tool = str(body.get("tool") or "").strip()
    args = body.get("args") or {}
    if not user_id or not tool or not isinstance(args, dict):
        return JSONResponse({"error": "bad_request"}, status_code=400)
    try:
        timeout_s = float(body.get("timeout_s") or 30.0)
    except (TypeError, ValueError):
        timeout_s = 30.0

    # allow_cross_process=False → ingen videre-forward (løkke-spærre).
    result = await bridge_registry.dispatch(
        user_id=user_id,
        tool=tool,
        args=args,
        timeout_s=timeout_s,
        allow_cross_process=False,
    )
    return JSONResponse(result, status_code=200)

_KEEPALIVE_S = 25.0
# Server-side receive watchdog. If no message (incl. ping/pong) arrives
# within this window, treat the connection as dead and disconnect. Client
# sends ping every 25s; server sends ping every 25s; either should keep
# traffic flowing. Anything beyond 70s of silence = zombie TCP that
# silently broke (NAT timeout, laptop sleep, network drop without RST).
_RECEIVE_TIMEOUT_S = 70.0


@router.websocket("/api/jarvisx-bridge/ws")
async def jarvisx_bridge_ws(ws: WebSocket) -> None:
    """Accept WS from JarvisX-app, route messages between bridge and runtime.

    Protocol:
      1. WS handshake — auth via Authorization: Bearer <jarvisx_token>
         (existing core.runtime.jarvisx_auth verifies).
      2. First message MUST be {"type": "register", "user_id": "...", ...}.
      3. After registration, runtime can dispatch tool_invoke messages and
         the bridge replies with tool_result (matched by correlation_id).
    """
    # Auth — extract token from headers (case-insensitive).
    token: str | None = None
    for k, v in ws.headers.items():
        if k.lower() == "authorization":
            if v.startswith("Bearer "):
                token = v[7:].strip()
            break

    claims: dict[str, Any] | None = None
    if token:
        try:
            from core.runtime.jarvisx_auth import verify_token
            claims = verify_token(token)
        except Exception as exc:
            logger.warning("jarvisx_bridge: token verify failed: %s", exc)
            claims = None

    # Dev fallback: if no auth required (single-user localhost) accept w/o token.
    # In production, refuse without claims.
    try:
        from core.runtime.jarvisx_auth import auth_required
        require_auth = bool(auth_required())
    except Exception:
        require_auth = False

    if require_auth and claims is None:
        await ws.close(code=1008, reason="auth_required")
        return

    await ws.accept()

    # First message must be register.
    try:
        first_raw = await asyncio.wait_for(ws.receive_text(), timeout=10.0)
    except (asyncio.TimeoutError, WebSocketDisconnect):
        await ws.close(code=1002, reason="register_timeout")
        return

    try:
        first = json.loads(first_raw)
    except Exception:
        await ws.close(code=1002, reason="register_not_json")
        return

    if first.get("type") != "register":
        await ws.close(code=1002, reason="register_expected_first")
        return

    user_id = str(
        first.get("user_id")
        or (claims or {}).get("sub")
        or ""
    ).strip()
    if not user_id:
        await ws.close(code=1002, reason="user_id_missing")
        return

    # If auth was provided, the claim's user_id MUST match the registration's.
    if claims and str(claims.get("sub") or "") != user_id:
        await ws.close(code=1008, reason="user_id_mismatch")
        return

    conn = BridgeConnection(
        user_id=user_id,
        client=str(first.get("client") or "jarvisx"),
        version=str(first.get("version") or ""),
        platform=str(first.get("platform") or ""),
        capabilities=list(first.get("capabilities") or []),
        ws=ws,
    )
    bridge_registry.register(conn)

    try:
        await ws.send_json({"type": "registered", "user_id": user_id})
    except Exception:
        bridge_registry.unregister(conn)
        return

    # Main message loop — handle tool_result + pong + ping.
    async def _heartbeat() -> None:
        while True:
            await asyncio.sleep(_KEEPALIVE_S)
            try:
                await conn.send_raw({"type": "ping"}, timeout_s=8.0)
            except Exception:
                return
            # Hold bro-presence frisk mens broen er forbundet, så owner-chat-mode-
            # gaten (operator-tools kun-når-paret) ikke taber broen når desktop er idle.
            try:
                bridge_registry._publish_presence()
            except Exception:
                pass

    heartbeat_task = asyncio.create_task(_heartbeat())

    try:
        while True:
            # Watchdog: bound receive so silently-dead TCP gets cleaned up.
            # Without this, ws.receive_text() can hang forever on a zombie
            # connection — bridge stays "registered" but every tool_invoke
            # dispatched to it times out with bridge_timeout. Symptom:
            # Jarvis "loses contact" with JarvisX without anyone noticing.
            try:
                raw = await asyncio.wait_for(
                    ws.receive_text(), timeout=_RECEIVE_TIMEOUT_S
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "jarvisx_bridge: receive timeout user=%s — closing zombie ws",
                    user_id,
                )
                try:
                    await ws.close(code=1011, reason="receive_timeout")
                except Exception:
                    pass
                break
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            mtype = msg.get("type")
            if mtype == "tool_result":
                await conn.deliver_result(
                    correlation_id=str(msg.get("correlation_id") or ""),
                    status=str(msg.get("status") or "error"),
                    result=msg.get("result"),
                    error=msg.get("error"),
                )
            elif mtype == "ping":
                try:
                    await ws.send_json({"type": "pong"})
                except Exception:
                    break
            elif mtype == "pong":
                pass  # accepted, no-op
            else:
                logger.debug("jarvisx_bridge: unknown msg type=%s", mtype)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("jarvisx_bridge: ws error user=%s: %s", user_id, exc)
    finally:
        heartbeat_task.cancel()
        bridge_registry.unregister(conn)
