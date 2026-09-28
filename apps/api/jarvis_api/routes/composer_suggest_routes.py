"""`/composer/suggest` — hvad der kunne skrives videre i komponisten.

Fladen er med vilje tynd: al logik bor i `core.services.composer_suggest`, så
mobil og desk får nøjagtig samme forslag. To flader der foreslår forskelligt
ville føles som to forskellige assistenter.

## Hvad der ALDRIG sker her

Der sendes intet udkast. Siden 28/9-2026 bygges forslaget udelukkende på
samtalen og kommer fra Jarvis selv — den vej der fuldførte en halvskreven
sætning er fjernet, og begge klienter sender et tomt felt. Halvskrevne
sætninger er det mest private i en samtale; de forlader ikke maskinen, fordi
der ikke er noget at sende. Der er ingen hovedbogs-række, fordi der ingen
udgift er: der kaldes ikke længere nogen model.

## Hvorfor et tomt svar er et gyldigt svar

Et forslag er en bekvemmelighed, ikke en funktion man kan miste. Ruten svarer
altid 200 med `{"forslag": "..."}` — tom streng når Jarvis ikke selv har lagt
et forslag ned, eller når der ikke er noget at bygge det på. En klient der
skulle håndtere fejlkoder for at kunne skrive videre, ville være en klient der
holdt op med at virke af en grund der ikke rager den.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/composer", tags=["composer"])


class Udkast(BaseModel):
    #: En samtale = «hvad kunne jeg skrive nu?». Uden session er der intet at
    #: bygge forslaget på, og svaret er tomt.
    #:
    #: Feltet `udkast` stod her indtil 28/9-2026. Ingen flade sendte andet end
    #: en tom streng, og fortsættelses-formen er fjernet — et gammelt kald der
    #: stadig sender feltet ignoreres, hvilket er præcis det rigtige.
    session_id: str = ""


class Valg(BaseModel):
    """Hvad der skete med et forslag. Se `core.runtime.db_composer_choice`."""
    forslag_id: str = ""
    session_id: str = ""
    #: Forslagets EGEN ordlyd — serverens egne ord, ikke brugerens.
    forslag: str = ""
    #: Den assistent-besked forslaget blev udledt af.
    kilde_besked_id: str = ""
    #: «vist» opretter rækken; «accepteret», «afvist» og «eget» afslutter den.
    valg: str = "vist"


@router.post("/suggest")
def suggest(krop: Udkast) -> dict[str, str]:
    """Et forslag, eller tom streng. Fejler aldrig.

    Ét spørgsmål: hvad kunne han skrive nu? Kilden er samtalen, og svaret
    kommer fra Jarvis selv gennem `suggest_next_message`. Har han ikke lagt et
    forslag ned, er svaret tomt — et tomt felt er ærligere end et gæt.

    Fortsættelses-formen (et halvskrevet udkast) stod her indtil 28/9-2026.
    Ingen flade brugte den; mobilen gik 24/9-2026 over til samme form som desk,
    netop fordi et gæt på resten af hans sætning føltes forkert.
    """
    try:
        from core.services.composer_suggest import foreslaa_naeste_detaljer
        return foreslaa_naeste_detaljer(krop.session_id or "")
    except Exception:
        logger.debug("composer/suggest fejlede", exc_info=True)
        return {"forslag": "", "forslag_id": "", "kilde_besked_id": ""}


@router.get("/moenster")
def moenster() -> dict[str, object]:
    """Hvad forslaget har lært af hans valg — i klartekst.

    Et mønster der former hans forslag, skal han kunne SE. Ruten svarer med
    den linje der faktisk står i prompten, hvor mange valg den bygger på, og
    om kontakten er tændt. Er der intet mønster endnu, er linjen tom — det er
    et gyldigt svar, ikke en fejl.
    """
    try:
        from core.services.composer_moenster import (
            MIN_VALG, VINDUE_DAGE, _valg_i_vinduet, er_taendt, moenster as byg,
        )
        valg = _valg_i_vinduet()
        return {
            "linje": byg() if er_taendt() else "",
            "taendt": er_taendt(),
            "valg_i_vinduet": len(valg),
            "kraever_mindst": MIN_VALG,
            "vindue_dage": VINDUE_DAGE,
        }
    except Exception:
        logger.debug("composer/moenster fejlede", exc_info=True)
        return {"linje": "", "taendt": True, "valg_i_vinduet": 0,
                "kraever_mindst": 0, "vindue_dage": 0}


@router.post("/choice")
def choice(krop: Valg) -> dict[str, bool]:
    """Registrér hvad der skete med et forslag. Fejler aldrig.

    Samme regel som `/suggest`: svaret er altid 200. En komponist der holdt op
    med at virke fordi en telemetri-skrivning fejlede, ville være en dårlig
    handel — vi gemmer det her for at gøre forslaget bedre, ikke for at gøre
    skrivefeltet skrøbeligere.

    `vist` opretter rækken. Det er dét der opfylder kravet om at et forslag
    der ALDRIG kom på skærmen ikke tælles med: blev det hentet og kasseret,
    ringer klienten aldrig.
    """
    try:
        from core.runtime.db_composer_choice import noter_valg, noter_vist
        valg = (krop.valg or "").strip().lower()
        if valg == "vist":
            noter_vist(
                forslag_id=krop.forslag_id or "",
                session_id=krop.session_id or "",
                forslag=krop.forslag or "",
                kilde_besked_id=krop.kilde_besked_id or "",
            )
        else:
            noter_valg(forslag_id=krop.forslag_id or "", valg=valg)
    except Exception:
        logger.debug("composer/choice fejlede", exc_info=True)
    return {"ok": True}
