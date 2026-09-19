"""`POST /chat/sessions/{id}/rewind` og `…/rewind/{rewind_id}/undo`.

Claude Desktops tilbagespoling (cc-desktop-chatview.md §8): beskederne kommer
tilbage, filerne røres ikke, og fortryd virker indtil næste besked. Logikken
bor i `core.runtime.db_chat_rewind`; ruten er kun adgang.

Ejer-tjek som visningsruten: kun den bruger samtalen tilhører må spole den.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.api.jarvis_api.routes.chat_session_view import _tjek_ejer

router = APIRouter(prefix="/chat", tags=["chat"])


class RewindRequest(BaseModel):
    message_id: str


@router.post("/sessions/{session_id}/rewind")
def chat_rewind(session_id: str, request: RewindRequest) -> dict:
    """Fjern en af dine beskeder og alt efter den. Svaret bærer beskedens tekst
    (til skrivefeltet) og et rewind-id til fortryd."""
    from core.runtime.db_chat_rewind import RewindFejl, spol_tilbage
    _tjek_ejer(session_id)
    try:
        return spol_tilbage(session_id, request.message_id)
    except RewindFejl as e:
        raise HTTPException(status_code=e.kode, detail=str(e)) from e


@router.post("/sessions/{session_id}/rewind/{rewind_id}/undo")
def chat_rewind_undo(session_id: str, rewind_id: str) -> dict:
    """Læg beskederne tilbage — kun så længe der ikke er skrevet siden."""
    from core.runtime.db_chat_rewind import RewindFejl, fortryd
    _tjek_ejer(session_id)
    try:
        return fortryd(session_id, rewind_id)
    except RewindFejl as e:
        raise HTTPException(status_code=e.kode, detail=str(e)) from e
