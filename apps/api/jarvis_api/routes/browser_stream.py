from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

_MAX_BESKED = 8192


@router.websocket("/ws/browser")
async def browser_stream(ws: WebSocket) -> None:
    """Jarvis' browser som JPEG-frames (binære beskeder) + input tilbage.

    Owner-only. Tokenet kommer via subprotokollen (se core/runtime/ws_auth) —
    aldrig ?token=, fordi uvicorns adgangslog skriver hele stien.
    """
    from core.runtime import ws_auth

    token, bad_om_sub = ws_auth.token_fra_handshake(ws.headers)
    krav = ws_auth.verificer(token)
    if krav is None and ws_auth.kraeves_auth():
        await ws.close(code=1008, reason="auth_required")
        return
    # Browseren er et styrehåndtag, ikke en læsestrøm: kun ejeren.
    if not ws_auth.er_ejer(krav):
        await ws.close(code=1008, reason="owner_required")
        return

    if bad_om_sub:
        await ws.accept(subprotocol=bad_om_sub)
    else:
        await ws.accept()

    from core.browser import screencast as sc

    sess = sc.ScreencastSession()
    try:
        await asyncio.to_thread(sess.start)
    except Exception as exc:
        logger.warning("browser_stream: kunne ikke starte screencast: %s", exc)
        await ws.close(code=1011, reason="browser_unavailable")
        return

    stop = asyncio.Event()

    async def _pump() -> None:
        while not stop.is_set():
            try:
                await asyncio.to_thread(sess.pump)
            except Exception as exc:
                logger.warning("browser_stream: pump fejlede: %s", exc)
                await asyncio.sleep(0.5)

    async def _send_frames() -> None:
        while not stop.is_set():
            frame = await asyncio.to_thread(sess.next_frame, 0.2)
            if frame is not None:
                await ws.send_bytes(frame)

    async def _send_tabs() -> None:
        from core.browser.playwright_session import run_in_playwright
        while not stop.is_set():
            try:
                faner = await asyncio.to_thread(run_in_playwright, sc.hent_faner, 10.0)
            except WebSocketDisconnect:  # klienten lukkede fanen: afslut lydigt
                return
            except Exception:  # fanelisten er kosmetisk; en fejl maa ikke draebe streamen
                faner = None
            if faner is not None:
                await ws.send_json({"type": "tabs", "tabs": faner})
            await asyncio.sleep(2.0)

    async def _receive() -> None:
        from core.browser.playwright_session import run_in_playwright
        while True:
            raw = await ws.receive_text()
            if len(raw) > _MAX_BESKED:
                continue
            try:
                fn = sc.bygg_input(json.loads(raw))
            except ValueError:  # ugyldig JSON fra klienten: ignorer beskeden
                continue
            if fn is None:
                continue
            try:
                await asyncio.to_thread(run_in_playwright, fn, 15.0)
            except Exception as exc:
                logger.debug("browser_stream: input fejlede: %s", exc)

    tasks = [asyncio.create_task(c()) for c in (_pump, _send_frames, _send_tabs, _receive)]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        stop.set()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.to_thread(sess.stop)
