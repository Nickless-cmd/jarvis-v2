"""Fastlaast bro-dispatch til EN bestemt klient (agent-contract-v1 E, spec 8).

``bridge_registry.dispatch`` er bygget til chatten: den vaelger den bedste bro, proever en ANDEN klient hvis
sendingen fejler, og forwarder over til en anden proces. Det er praecis det en agents kald ikke maa:

* andre samtidige klienter for samme bruger er IKKE automatisk erstatninger,
* en broafbrydelse bliver aldrig stiltiende til et andet sted (heller ikke containeren),
* en svigtet sending maa ikke blive til et kald paa en anden maskine.

Derfor en egen vej: kaldet gaar til ``(user_id, client_id)`` eller ingen steder. Findes klienten ikke i
DENNE proces, forwardes kaldet kun til den proces presence siger holder netop den klient - og dér lander det
igen paa ``dispatch_pinned`` med ``allow_cross_process=False``.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

NOT_CONNECTED = "client_not_connected"
SEND_FAILED = "bridge_send_failed"
TIMEOUT = "bridge_timeout"
DISCONNECTED = "bridge_disconnected"


def _err(code: str, **extra: Any) -> dict[str, Any]:
    return {"status": "error", "result": None, "error": code, **extra}


def _local_conn(user_id: str, client_id: str):
    from core.services.jarvisx_bridge import bridge_registry
    return (bridge_registry._by_user.get(user_id) or {}).get(client_id)


def client_info(user_id: str, client_id: str) -> dict[str, Any] | None:
    """Klientens annoncerede tilstand (lokalt eller via presence fra den anden proces), eller None."""
    conn = _local_conn(user_id, client_id)
    if conn is not None:
        return {"process": "local", "client": conn.client, "platform": conn.platform,
                "version": conn.version, "capabilities": list(conn.capabilities or [])}
    try:
        from core.services import bridge_presence
        info = (bridge_presence.all_presence().get(str(user_id)) or {})
        c = (info.get("clients") or {}).get(client_id)
        if isinstance(c, dict):
            return {"process": info.get("process") or "", **c}
    except Exception:
        logger.warning("presence kunne ikke laeses for %s/%s", user_id, client_id, exc_info=True)
    return None


async def dispatch_pinned(*, user_id: str, client_id: str, tool: str, args: dict[str, Any],
                          timeout_s: float, extra: dict[str, Any] | None = None,
                          allow_cross_process: bool = True) -> dict[str, Any]:
    """Send ``tool`` til netop ``client_id``. Aldrig failover til en anden klient. Rejser ikke."""
    conn = _local_conn(user_id, client_id)
    if conn is None:
        if not allow_cross_process:
            return _err(NOT_CONNECTED)
        return await _forward(user_id=user_id, client_id=client_id, tool=tool, args=args,
                              timeout_s=timeout_s, extra=extra)
    correlation_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    conn._pending[correlation_id] = (fut, loop)
    try:
        await conn.send_invoke(correlation_id=correlation_id, tool=tool, args=args,
                               timeout_ms=int(timeout_s * 1000), extra=extra)
    except Exception as exc:
        conn._pending.pop(correlation_id, None)
        logger.warning("pinned dispatch kunne ikke sendes til %s/%s: %s", user_id, client_id, exc)
        # Intet forlod serveren: kalderen ved at sendingen ikke skete. INGEN anden klient proeves.
        return _err(SEND_FAILED, sent=False, detail=str(exc)[:160])
    try:
        out = await asyncio.wait_for(fut, timeout=timeout_s)
    except asyncio.TimeoutError:
        conn._pending.pop(correlation_id, None)
        return _err(TIMEOUT, sent=True)
    except asyncio.CancelledError:
        conn._pending.pop(correlation_id, None)
        return _err("bridge_call_cancelled", sent=True)
    if out.get("status") != "ok" and str(out.get("error") or "") in ("bridge_disconnected", "bridge_replaced",
                                                                      "registry_cleared"):
        return _err(DISCONNECTED, sent=True, reason=out.get("error"))
    return {**out, "sent": True}


async def _forward(*, user_id: str, client_id: str, tool: str, args: dict[str, Any],
                   timeout_s: float, extra: dict[str, Any] | None) -> dict[str, Any]:
    """Til den proces presence siger holder KLIENTEN. Ingen presence -> klienten er ikke forbundet."""
    from core.services import jarvisx_bridge as jb
    info = client_info(user_id, client_id)
    process = str((info or {}).get("process") or "")
    if not info or process in ("", "local"):
        return _err(NOT_CONNECTED)
    try:
        from core.services.central_xproc import process_role
        if process == process_role():
            return _err(NOT_CONNECTED, detail="presence peger paa egen proces uden lokal bro")
    except Exception:
        logger.debug("process_role utilgaengelig", exc_info=True)
    token = jb.internal_dispatch_token()
    if not token:
        return _err(NOT_CONNECTED, detail="intet delt internt token")
    url = f"http://127.0.0.1:{jb._port_for_process(process)}{jb._INTERNAL_DISPATCH_PATH}"
    try:
        import httpx
        timeout = httpx.Timeout(connect=3.0, read=float(timeout_s) + 10.0, write=5.0, pool=3.0)
        async with httpx.AsyncClient(timeout=timeout) as http:
            resp = await http.post(url, json={"user_id": user_id, "client_id": client_id, "tool": tool,
                                              "args": args, "timeout_s": timeout_s, "extra": extra or {}},
                                   headers={jb._INTERNAL_TOKEN_HEADER: token})
    except Exception as exc:
        # Forwarden naaede maaske aldrig frem - men den KAN vaere naaet. En skrivning er derfor
        # uafgjort, ikke "ikke sendt": kalderen faar sent=None og maa behandle det som ukendt.
        logger.warning("pinned forward fejlede for %s/%s: %s", user_id, client_id, exc)
        return _err("bridge_forward_failed", sent=None, detail=str(exc)[:160])
    if resp.status_code != 200:
        return _err("bridge_forward_failed", sent=None, detail=f"http {resp.status_code}")
    data = resp.json()
    return data if isinstance(data, dict) and "status" in data else _err("bridge_forward_failed", sent=None)
