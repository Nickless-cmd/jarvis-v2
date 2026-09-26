# apps/api/jarvis_api/routes/notifikationer.py
"""Notifikations-feeden. Scoper til den auth'ede bruger.

Ruten LUKKER ikke selv en raekke naar den er afgjort — det goer hydreringen
ved naeste laesning. Ét sted der bestemmer: lukkede ruten ogsaa, kunne den
lukke en raekke hvis ejer stadig venter, og saa var kortet vaek uden at vaere
besvaret.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.services import notifikationer as _lager
from core.services import notifikationer_hydrering as _hyd

router = APIRouter(prefix="/notifikationer", tags=["notifikationer"])


class AfgoerBody(BaseModel):
    approved: bool


# De to udgange fra resolve_pending_approval() der endnu er paa engelsk —
# resten af funktionens fejltekster er allerede dansk og sendes uaendret.
_ENGELSK_TIL_DANSK = {
    "Approval not found or expired": "Kortet findes ikke laengere, eller det er udloebet.",
    "Approval already resolved": "Kortet er allerede besvaret.",
}


def _oversaet_fejl(raa_fejl: str) -> str:
    """Oversaet en teknisk/engelsk fejltekst til noget en almindelig bruger
    forstaar. Ukendte tekster (allerede dansk, eller nye udgange vi ikke
    har set endnu) sendes uaendret videre frem for at blive tavse."""
    return _ENGELSK_TIL_DANSK.get(raa_fejl.strip(), raa_fejl)


def _nuvaerende_bruger() -> tuple[str | None, bool]:
    """(user_id, er_owner).

    Owner afgoeres af bruger-ROLLEN (find_user_by_discord_id().role ==
    "owner"), IKKE en streng-sammenligning mod user_id — Bjoerns user_id er
    hans Discord-ID, ikke "owner".

    Ubundet (no-auth) giver uid=None og er_owner=True i returvaerdien — MEN
    det andet felt bruges aldrig i praksis: alle tre handlere nedenfor har
    `if not uid: return ...` FOER er_owner laeses, saa en ubundet kalder
    faar et tomt feed uanset hvad feltet siger. Det er med vilje, ikke en
    kopieret fejl fra cowork.py's tilsvarende funktion (som RENT FAKTISK
    behandler ubundet som owner): denne flade kan GODKENDE vaerktoejskald,
    og at fejle lukket er sikrere end at give en uautentificeret kalder
    ejerens feed.
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
async def feed(aktiv: str = "") -> dict:
    """Feedet. `aktiv` = den samtale klienten SIDDER I lige nu.

    Svar fra den springes over (se `notifikationer_hydrering.feed`): man
    laeser dem allerede i vinduet ved siden af. Klienten sender sit eget
    sessions-id — serveren kan ikke vide hvilken samtale der er aaben paa
    skaermen, og en gaetning her ville skjule det forkerte.

    To tal, ikke ét: `antal` er alt der er aabent (klokkens «der er nyt»),
    `venter` er dem der kraever et SVAR. Forskellen er de klarede svar —
    maalt 26/9-2026 stod 100 `run_done` aabne samtidig, og et enkelt tal
    gjorde klokken til en konstant «9+» uden at noget ventede.
    """
    uid, er_owner = _nuvaerende_bruger()
    if not uid:
        # V6 (2026-09-22): svarede foer 200 OK med {"poster": [], "antal": 0}
        # — praecis samme form som en AEGTE tom feed. Klienterne viser saa
        # «Ingen notifikationer — alt er klaret», og et udloebet token ser
        # ud som «du er helt ajour». 401 lader klienten skelne "intet at
        # vise" fra "jeg kunne ikke spoerge".
        raise HTTPException(status_code=401, detail="Ikke logget ind.")
    poster = _hyd.feed(uid, er_owner=er_owner, aktiv_session=aktiv or None)
    return {"poster": poster, "antal": len(poster),
            "venter": sum(1 for p in poster if p["slags"] != "run_done")}


@router.get("/tidligere")
async def tidligere_feed() -> dict:
    """Historikken. Samme form som feed() — én klient-type, to lister.

    Egen rute frem for et flag paa feed(): de to lister har forskellige
    levetider. Aabne poster hydreres og kan forsvinde MIDT i en laesning;
    klarede er frosne og skal bare laeses. Et flag ville lave feed() til to
    funktioner i én krop — og den slags bliver til to fejl der skal rettes
    hver for sig.
    """
    uid, er_owner = _nuvaerende_bruger()
    if not uid:
        raise HTTPException(status_code=401, detail="Ikke logget ind.")
    poster = _hyd.tidligere(uid, er_owner=er_owner)
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
        resultat = approval_runtime.decide(ref, approved=body.approved, answered_by=uid)
    except Exception as fejl:
        # decide() kan fejle af mange grunde (kortet vaek, netvaerk, forkert
        # tilstand) — vis fejlen til brugeren i stedet for et 500 uden hoved eller hale.
        return {"ok": False, "fejl": f"Svaret kunne ikke sendes: {fejl}"}
    # decide() REJSER ikke ved de almindelige fejl (kortet vaek, allerede
    # besvaret, forkert ejer, udloebet, kaldet aendret, broen sagde nej) —
    # den returnerer roligt {"status": "error", "error": ...}. Ignoreres
    # returvaerdien, faar klienten {"ok": true} for et svar der ALDRIG blev
    # sendt. Tjek paa "status", ikke en bestemt fejltekst, saa alle disse
    # udgange fra resolve_pending_approval() daekkes ens.
    if isinstance(resultat, dict) and resultat.get("status") == "error":
        raa_fejl = str(resultat.get("error") or resultat.get("result_text")
                       or "Ukendt fejl.")
        return {"ok": False, "fejl": _oversaet_fejl(raa_fejl)}
    # Udfaldet skrives HER — men foerst efter decide() har svaret ok.
    #
    # Modulet ovenfor siger at ruten ikke maa lukke en raekke hvis ejer stadig
    # venter. Det er praecis derfor linjen ligger EFTER fejl-grenen: er kortet
    # afgjort, venter ejeren ikke laengere. Lukkede vi ogsaa naar decide()
    # svarede error, ville et fejlet svar fjerne kortet fra den der stadig
    # venter — den fejl ruten er bygget til at undgaa.
    #
    # Uden udfaldet her kunne historikken ikke skelne «godkendt» fra «afvist»:
    # begge blev lukket af hydreringen som «superseded», og fladen ville vise
    # det samme ord for to modsatte svar.
    _lager.luk(notif_id, "godkendt" if body.approved else "afvist")
    # Raekken lukkes i OEVrigt af hydreringen ved naeste laesning.
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
