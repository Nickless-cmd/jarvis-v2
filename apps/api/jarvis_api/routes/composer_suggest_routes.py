"""`/composer/suggest` — hvad der kunne skrives videre i komponisten.

Fladen er med vilje tynd: al logik bor i `core.services.composer_suggest`, så
mobil og desk får nøjagtig samme forslag. To flader der foreslår forskelligt
ville føles som to forskellige assistenter.

## Hvad der ALDRIG sker her

Udkastet gemmes ikke. Halvskrevne sætninger er det mest private i en samtale —
de indeholder det man fortryder, omformulerer eller sletter igen — og de går
kun til den lokale model. Der er ingen hovedbogs-række, fordi der ikke er nogen
udgift: det er ollama på egen GPU.

## Hvorfor et tomt svar er et gyldigt svar

Et forslag er en bekvemmelighed, ikke en funktion man kan miste. Ruten svarer
altid 200 med `{"forslag": "..."}` — tom streng når der intet er at foreslå,
når modellen er nede, eller når udkastet ikke indbyder til det. En klient der
skulle håndtere fejlkoder for at kunne skrive videre, ville være en klient der
holdt op med at virke når GPU'en var optaget.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/composer", tags=["composer"])


class Udkast(BaseModel):
    udkast: str = ""
    #: Tomt udkast + en samtale = «hvad kunne jeg skrive nu?». Uden session
    #: er der intet at bygge forslaget på, og svaret er tomt.
    session_id: str = ""


@router.post("/suggest")
def suggest(krop: Udkast) -> dict[str, str]:
    """Et forslag, eller tom streng. Fejler aldrig.

    To tilstande, ét endpoint, fordi det er det samme spørgsmål stillet to
    steder i skrivningen:

    * **Med udkast** → fortsættelsen af det (mobilens linje man trykker på).
    * **Uden udkast** → et bud på den næste besked, ud fra samtalen. Det er
      den form desk viser, hvor pladsholderen står.
    """
    try:
        from core.services.composer_suggest import foreslaa, foreslaa_naeste
        udkast = (krop.udkast or "").strip()
        if udkast:
            return {"forslag": foreslaa(krop.udkast or "")}
        return {"forslag": foreslaa_naeste(krop.session_id or "")}
    except Exception:
        logger.debug("composer/suggest fejlede", exc_info=True)
        return {"forslag": ""}
