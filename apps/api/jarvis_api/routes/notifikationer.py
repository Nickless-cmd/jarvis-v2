# apps/api/jarvis_api/routes/notifikationer.py
"""Notifikations-feeden. Scoper til den auth'ede bruger.

Ruten LUKKER ikke selv en raekke naar den er afgjort — det goer hydreringen
ved naeste laesning. Ét sted der bestemmer: lukkede ruten ogsaa, kunne den
lukke en raekke hvis ejer stadig venter, og saa var kortet vaek uden at vaere
besvaret.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from core.services import notifikationer as _lager
from core.services import notifikationer_hydrering as _hyd

router = APIRouter(prefix="/notifikationer", tags=["notifikationer"])


class AfgoerBody(BaseModel):
    approved: bool


def _nuvaerende_bruger() -> tuple[str | None, bool]:
    """(user_id, er_owner).

    Owner afgoeres af bruger-ROLLEN (find_user_by_discord_id().role ==
    "owner"), IKKE en streng-sammenligning mod user_id — Bjoerns user_id er
    hans Discord-ID, ikke "owner". Samme moenster som cowork.py:_role_owner().
    Ubundet (no-auth) = owner.
    """
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    if uid is None:
        return None, True
    from core.identity.users import find_user_by_discord_id
    try:
        u = find_user_by_discord_id(str(uid))
    except Exception:
        # DB-fejl ved rolleopslag maa ikke vaelte feeden — antag ikke-owner
        # frem for at lade en 500 skjule notifikationerne helt.
        return uid, False
    return uid, (getattr(u, "role", "") == "owner")


def _min_raekke(notif_id: str, user_id: str) -> dict | None:
    """Raekken — kun hvis den er brugerens egen. Et gaettet id fra en anden
    bruger maa ikke kunne afgoeres herfra."""
    for r in _lager.aabne(user_id, er_owner=False):
        if str(r["id"]) == notif_id:
            return r
    return None


@router.get("")
async def feed() -> dict:
    uid, er_owner = _nuvaerende_bruger()
    if not uid:
        return {"poster": [], "antal": 0}
    poster = _hyd.feed(uid, er_owner=er_owner)
    return {"poster": poster, "antal": len(poster)}


@router.post("/{notif_id}/afgoer")
async def afgoer(notif_id: str, body: AfgoerBody) -> dict:
    uid, _ = _nuvaerende_bruger()
    if not uid:
        return {"ok": False, "fejl": "Ikke logget ind."}
    raekke = _min_raekke(notif_id, uid)
    if raekke is None:
        return {"ok": False, "fejl": "Notifikationen findes ikke."}
    slags = str(raekke["slags"])
    if slags not in _hyd.AFGOERBARE:
        # Herunder `question`: et pause_and_ask besvares med en tekst i
        # samtalen, ikke med ja/nej. Fladen sender dig derhen i stedet.
        return {"ok": False, "fejl": "Den slags kan ikke godkendes eller afvises."}
    ref = str(raekke["ref"] or "")
    from core.services import approval_runtime
    try:
        approval_runtime.decide(ref, approved=body.approved, answered_by=uid)
    except Exception as fejl:
        # decide() kan fejle af mange grunde (kortet vaek, netvaerk, forkert
        # tilstand) — vis fejlen til brugeren i stedet for et 500 uden hoved eller hale.
        return {"ok": False, "fejl": f"Svaret kunne ikke sendes: {fejl}"}
    # Raekken lukkes af hydreringen ved naeste laesning — ikke her.
    return {"ok": True, "fejl": ""}


@router.post("/{notif_id}/set")
async def set_(notif_id: str) -> dict:
    uid, _ = _nuvaerende_bruger()
    if not uid:
        return {"ok": False}
    if _min_raekke(notif_id, uid) is None:
        return {"ok": False}
    _lager.luk(notif_id, "seen")
    return {"ok": True}
