from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

_MAX_BESKED = 8192


@router.websocket("/ws/desktop")
async def desktop_stream(ws: WebSocket) -> None:
    """Jarvis' Linux-desktop som JPEG-frames (binære beskeder) + input tilbage.

    Owner-only. Tokenet kommer via subprotokollen (se core/runtime/ws_auth).
    """
    from core.runtime import ws_auth

    token, bad_om_sub = ws_auth.token_fra_handshake(ws.headers)
    krav = ws_auth.verificer(token)
    if krav is None and ws_auth.kraeves_auth():
        await ws.close(code=1008, reason="auth_required")
        return
    # Desktoppen er et styrehåndtag, ikke en læsestrøm: kun ejeren.
    if not ws_auth.er_ejer(krav):
        await ws.close(code=1008, reason="owner_required")
        return

    if bad_om_sub:
        await ws.accept(subprotocol=bad_om_sub)
    else:
        await ws.accept()

    from core.desktop.x_session import XSession

    sess = XSession()
    try:
        res = await asyncio.to_thread(sess.start)
    except Exception as exc:
        logger.warning("desktop_stream: kunne ikke starte desktop: %s", exc)
        await ws.close(code=1011, reason="desktop_unavailable")
        return
    if res.get("status") != "ok":
        logger.warning("desktop_stream: desktop utilgængelig: %s", res.get("error"))
        await ws.close(code=1011, reason="desktop_unavailable")
        return

    stop = asyncio.Event()

    async def _send_frames() -> None:
        while not stop.is_set():
            frame = await asyncio.to_thread(sess.frame)
            if isinstance(frame, (bytes, bytearray)):
                await ws.send_bytes(bytes(frame))
                await asyncio.sleep(0.12)
            else:
                await ws.send_json({"type": "error", "code": frame.get("code"), "error": frame.get("error")})
                await asyncio.sleep(1.0)

    async def _receive() -> None:
        while True:
            raw = await ws.receive_text()
            if len(raw) > _MAX_BESKED:
                continue
            try:
                msg = json.loads(raw)
            except ValueError:  # ugyldig JSON fra klienten: ignorer beskeden
                continue
            try:
                await asyncio.to_thread(sess.input, msg)
            except WebSocketDisconnect:  # klienten lukkede fanen: afslut lydigt
                return
            except Exception as exc:
                logger.debug("desktop_stream: input fejlede: %s", exc)

    tasks = [asyncio.create_task(c()) for c in (_send_frames, _receive)]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        stop.set()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.to_thread(sess.stop)
