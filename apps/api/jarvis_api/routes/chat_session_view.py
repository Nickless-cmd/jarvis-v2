"""`GET/PUT /chat/sessions/{id}/view` — samtalens visningstilstand.

Egen fil fordi `routes/chat.py` allerede er på ~1950 linjer. Logikken bor i
`core.services.session_view`.

Ejer-tjek: kun den bruger samtalen tilhører må læse eller skifte dens
visning. (De ældre samtale-ruter — omdøb, flag, slet — har intet sådant
tjek; det er et kendt hul, ikke et forbillede.)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class SessionViewRequest(BaseModel):
    view: str


def _tjek_ejer(session_id: str) -> None:
    from core.identity.workspace_context import current_user_id
    from core.services.chat_sessions import get_session_owner
    ejer = get_session_owner(session_id)
    bruger = current_user_id()
    # Ustemplede (legacy) samtaler har ingen ejer at tjekke imod.
    if ejer and bruger and ejer != bruger:
        raise HTTPException(status_code=403, detail="Ikke din samtale")


@router.get("/sessions/{session_id}/view")
def chat_session_view(session_id: str) -> dict:
    """Samtalens visningstilstand: normal, thinking eller verbose."""
    from core.services.session_view import hent_visning
    _tjek_ejer(session_id)
    return {"id": session_id, "view": hent_visning(session_id)}


@router.put("/sessions/{session_id}/view")
def chat_set_session_view(session_id: str, request: SessionViewRequest) -> dict:
    """Skift samtalens visningstilstand. Gælder fra næste runde, også midt i et svar."""
    from core.services.session_view import saet_visning
    _tjek_ejer(session_id)
    svar = saet_visning(session_id, request.view)
    if svar.get("status") != "ok":
        fejl = str(svar.get("error") or "")
        raise HTTPException(status_code=404 if "ukendt samtale" in fejl else 400, detail=fejl)
    return svar
