# apps/api/jarvis_api/routes/notifikations_valg.py
"""Push-valg per slags. Scoper til den auth'ede bruger."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.services import notifikations_valg as _valg

router = APIRouter(prefix="/notifikations-valg", tags=["notifikationer"])


class SaetBody(BaseModel):
    slags: str
    kanal: str


def _bruger() -> str | None:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or None


@router.get("")
async def hent() -> dict:
    uid = _bruger()
    if not uid:
        # V6 (2026-09-22): svarede foer 200 OK med {"valg": {}} — umuligt at
        # skelne fra en bruger der reelt ikke har sat noget. Se
        # notifikationer.py's feed() for samme rettelse og begrundelse.
        raise HTTPException(status_code=401, detail="Ikke logget ind.")
    return {"valg": _valg.alle(uid)}


@router.post("")
async def saet(body: SaetBody) -> dict:
    uid = _bruger()
    if not uid:
        return {"ok": False, "fejl": "Ikke logget ind."}
    try:
        _valg.saet(uid, body.slags, body.kanal)
    except ValueError:
        # Ikke en fejl der skal logges: en ukendt kanal er brugerinput,
        # ikke en systemfejl. Fejlen sendes tilbage til klienten i stedet.
        return {"ok": False, "fejl": f"Ukendt kanal: {body.kanal}"}
    return {"ok": True, "fejl": ""}
