"""`GET/PUT /chat/sessions/{id}/view` — samtalens visningstilstand.

Egen fil fordi `routes/chat.py` allerede er på ~1950 linjer. Logikken bor i
`core.services.session_view`.

Adgang: `kraev_adgang` — samme regel som alle samtale-ruterne
(`core.identity.session_access`).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class SessionViewRequest(BaseModel):
    view: str


def kraev_adgang(session_id: str) -> None:
    """403 hvis den nuværende bruger ikke må røre samtalen.

    Reglen bor i `core.identity.session_access` — fælles for alle
    samtale-ruterne (Bjørn 19/9-2026: «luk hullet i de gamle»).
    """
    from core.identity.session_access import maa_tilgaa_session
    if not maa_tilgaa_session(session_id):
        raise HTTPException(status_code=403, detail="Ikke din samtale")


@router.get("/sessions/{session_id}/view")
def chat_session_view(session_id: str) -> dict:
    """Samtalens visningstilstand: normal, thinking eller verbose."""
    from core.services.session_view import hent_visning
    kraev_adgang(session_id)
    return {"id": session_id, "view": hent_visning(session_id)}


@router.put("/sessions/{session_id}/view")
def chat_set_session_view(session_id: str, request: SessionViewRequest) -> dict:
    """Skift samtalens visningstilstand. Gælder fra næste runde, også midt i et svar."""
    from core.services.session_view import saet_visning
    kraev_adgang(session_id)
    svar = saet_visning(session_id, request.view)
    if svar.get("status") != "ok":
        fejl = str(svar.get("error") or "")
        raise HTTPException(status_code=404 if "ukendt samtale" in fejl else 400, detail=fejl)
    return svar
