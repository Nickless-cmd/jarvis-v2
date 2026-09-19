"""Enheder — list, fjern, registrér denne computer, og tænd/sluk reglen.

Codex' «Administrer forbindelser» (codex-remote-control.md §6): hver enhed kan
fjernes for sig, og fjernelsen slår igennem med det samme. Logikken bor i
`core.runtime.db_devices`; reglen i `core.identity.kode_adgang`.

Alt kræver den indloggede bruger og gælder KUN brugerens egne enheder. At
registrere en computer og at tænde/slukke reglen kræver totrinskoden — det er
dér adgangen til code mode bliver givet.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _bruger() -> str:
    from core.identity.workspace_context import current_user_id
    uid = (current_user_id() or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Ikke logget ind")
    return uid


def _totp(uid: str, kode: str) -> None:
    from core.services.device_pairing import TotpFejl, kraev_totp
    try:
        kraev_totp(uid, kode)
    except TotpFejl as e:
        raise HTTPException(status_code=e.kode, detail=str(e)) from e


def _denne() -> dict:
    """Er klienten der spørger, selv en tilføjet enhed?"""
    from core.identity.kode_adgang import kode_tilladt
    from core.identity.workspace_context import current_token_enhed
    enhed, app_id = current_token_enhed()
    art = "telefon" if enhed else ("computer" if app_id and app_id != "jarvis-mobile" else "ukendt")
    from core.runtime.db_devices import maa_bruge_kode
    from core.identity.workspace_context import current_user_id
    return {
        "type": art,
        "tilfoejet": maa_bruge_kode(current_user_id() or "", enhed=enhed, app_id=app_id),
        "kode_tilladt": kode_tilladt(),
    }


@router.get("/enheder")
def enheder() -> dict:
    """Mine enheder, om reglen er tændt, og om DENNE klient er tilføjet."""
    from core.runtime.db_devices import kraev_aktivt, liste
    uid = _bruger()
    return {"enheder": liste(uid), "kraev_aktivt": kraev_aktivt(), "denne": _denne()}


@router.delete("/enheder/{enheds_id}")
def fjern_enhed(enheds_id: str) -> dict:
    """Fjern én af mine enheder. En telefon mister al adgang med det samme."""
    from core.runtime.db_devices import fjern
    if not fjern(enheds_id, _bruger()):
        raise HTTPException(status_code=404, detail="Enheden findes ikke (eller er allerede fjernet)")
    return {"ok": True}


class TotpReq(BaseModel):
    totp: str = ""
    navn: str = ""


@router.post("/enheder/denne-computer")
def registrer_denne_computer(req: TotpReq) -> dict:
    """Tilføj den desk-installation der spørger (dens app_id) — med totrinskode."""
    from core.identity.workspace_context import current_token_enhed
    from core.runtime.db_devices import registrer_computer
    uid = _bruger()
    _, app_id = current_token_enhed()
    _totp(uid, req.totp)
    try:
        return registrer_computer(uid, app_id, navn=req.navn or "Computer")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class KravReq(BaseModel):
    aktiv: bool
    totp: str = ""
    navn: str = ""


@router.put("/enheds-krav")
def saet_enheds_krav(req: KravReq) -> dict:
    """Tænd/sluk reglen «code mode kræver en tilføjet enhed». Kun ejeren.

    Tændes den fra en desk, registreres DEN computer først — ellers ville man
    låse sig selv ude af code mode i samme øjeblik.
    """
    from core.identity.workspace_context import current_role, current_token_enhed
    from core.runtime.db_devices import registrer_computer, saet_kraev
    uid = _bruger()
    if (current_role() or "") != "owner":
        raise HTTPException(status_code=403, detail="Kun ejeren kan ændre reglen")
    _totp(uid, req.totp)
    if req.aktiv:
        _, app_id = current_token_enhed()
        try:
            registrer_computer(uid, app_id, navn=req.navn or "Denne computer")
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"{e} — tænd reglen fra desk på din computer, så den selv bliver tilføjet.",
            ) from e
    saet_kraev(req.aktiv, af=uid)
    return {"ok": True, "kraev_aktivt": req.aktiv}
