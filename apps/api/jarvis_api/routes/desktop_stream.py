from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

_MAX_BESKED = 8192


def _bruger_id(krav: dict | None, privilege: str) -> str:
    """Hvem sessionen tilhører. Uden token (auth slået fra) er det ejeren."""
    if krav is not None:
        return str(krav.get("sub") or "")
    if privilege == "owner":
        try:
            from core.identity.users import get_owner

            o = get_owner()
            return str(getattr(o, "discord_id", "") or "") if o else ""
        except Exception:  # ingen ejer at finde: tomt id -> workspace_unavailable
            return ""
    return ""


@router.websocket("/ws/desktop")
async def desktop_stream(ws: WebSocket) -> None:
    """Jarvis' Linux-desktop som JPEG-frames (binære beskeder) + input tilbage.

    Hver bruger får sin EGEN session i eget workspace (`session_for`). Ejeren
    er ikke indespærret; alle andre er låst til deres workspace. Kan workspace
    ikke opløses, lukkes forbindelsen med `workspace_unavailable` — aldrig et
    fald til en fælles session. Tokenet kommer via subprotokollen.
    """
    from core.runtime import ws_auth

    token, bad_om_sub = ws_auth.token_fra_handshake(ws.headers)
    krav = ws_auth.verificer(token)
    if krav is None and ws_auth.kraeves_auth():
        await ws.close(code=1008, reason="auth_required")
        return
    privilege = "owner" if ws_auth.er_ejer(krav) else "member"
    bruger = _bruger_id(krav, privilege)

    if bad_om_sub:
        await ws.accept(subprotocol=bad_om_sub)
    else:
        await ws.accept()

    from core.desktop.x_session import WorkspaceUnavailable, session_for

    try:
        sess = session_for(bruger, privilege)
    except (WorkspaceUnavailable, ValueError) as exc:
        logger.warning("desktop_stream: workspace utilgængeligt: %s", exc)
        await ws.close(code=1008, reason="workspace_unavailable")
        return
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
        sidste_markor: tuple[int, int] | None = None
        tael = 0
        while not stop.is_set():
            frame = await asyncio.to_thread(sess.frame)
            if isinstance(frame, (bytes, bytearray)):
                await ws.send_bytes(bytes(frame))
                tael += 1
                # Markøren ligger IKKE i skærmgrebet: X11 tegner den uden for
                # billedbufferen. Uden positionen kan klienten ikke vise hvor
                # man peger, og så ser musen død ud selv om den flytter sig.
                pos = await asyncio.to_thread(sess.cursor)
                if pos.get("status") == "ok":
                    nu = (pos["x"], pos["y"])
                    # Ved hver flytning — og ellers en gang i sekundet, så en
                    # klient der lige er kommet til ikke står uden markør.
                    if nu != sidste_markor or tael % 10 == 0:
                        sidste_markor = nu
                        await ws.send_json({"type": "cursor", "x": nu[0], "y": nu[1]})
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
        # Desktoppen stoppes IKKE her: den er delt og en tilstand, ikke en
        # forbindelse. Ellers forsvandt vinduerne hver gang man skiftede fane.
