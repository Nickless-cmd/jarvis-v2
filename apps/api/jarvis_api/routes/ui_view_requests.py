"""`GET /ui/view-requests/pending` og `POST /ui/view-requests/{id}/svar`.

Desk-siden af Claude Desktops view-request-kanal (se
`core.runtime.db_view_requests` og `core.tools.desk_view_tools`): desk poller
de ubesvarede forespørgsler, udfører dem på sin skærm og svarer med indhold.

Adgang: en forespørgsel hører til en samtale, og kun den der må røre
samtalen, får den at se eller må svare på den (`core.identity.session_access`).
Ellers kunne ét vindue læse — eller besvare — en andens layout-forespørgsler.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/ui", tags=["ui"])


class ViewSvar(BaseModel):
    resultat: dict[str, Any]


def _ventende() -> list[dict[str, Any]]:
    from core.identity.session_access import maa_tilgaa_session
    from core.runtime.db_view_requests import ventende
    return [
        {"id": r["id"], "op": r["op"], "args": r.get("args") or {}, "session_id": r.get("session_id") or ""}
        for r in ventende() if maa_tilgaa_session(str(r.get("session_id") or ""))
    ]


@router.get("/view-requests/pending")
async def view_requests_pending() -> dict[str, Any]:
    """Ubesvarede visnings-forespørgsler for samtaler brugeren må røre."""
    return {"requests": await asyncio.to_thread(_ventende)}


@router.post("/view-requests/{request_id}/svar")
async def view_request_svar(request_id: str, body: ViewSvar) -> dict[str, Any]:
    """Desk's svar. Kun det første svar tæller."""
    from core.identity.session_access import maa_tilgaa_session
    from core.runtime.db_view_requests import hent, svar
    req = await asyncio.to_thread(hent, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Forespørgslen findes ikke")
    if not maa_tilgaa_session(str(req.get("session_id") or "")):
        raise HTTPException(status_code=403, detail="Ikke din samtale")
    ok = await asyncio.to_thread(svar, request_id, body.resultat)
    return {"ok": ok}
