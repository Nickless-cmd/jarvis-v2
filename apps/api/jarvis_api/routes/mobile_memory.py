"""«Brug denne besked som hukommelse» — fra telefonen ind i hans hjerne.

Mobilen kunne laese hukommelse, men ikke skrive. Bjoerns liste 6/9-2026:
«Use this as memory paa en besked». Uden et endpoint var det kun en knap der
ikke kunne goere noget.

Ruten er bevidst SMAL. `remember_this` tager tretten felter — kind, visibility,
domain, tags, importance, kaeder til andre poster. Et telefon-tryk paa en
besked har ikke den kontekst, og at lade klienten vaelge dem ville goere en
etlinjes-handling til en formular. Serveren vaelger derfor de faste:

  kind=observation   det er noget der BLEV sagt, ikke en konklusion han drog
  visibility=personal  en samtale mellem ham og Bjoern er ikke public_safe
  domain=samtale

Titlen udledes af teksten selv, saa man ikke skal navngive en huskeseddel for
at gemme den.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/mobile", tags=["mobile-memory"])

_MAKS_INDHOLD = 4000
_MAKS_TITEL = 80


class GemSomHukommelse(BaseModel):
    content: str
    session_id: str = ""
    message_id: str = ""
    note: str = ""          # brugerens egen tilfoejelse, hvis han skrev en


def _titel_af(tekst: str) -> str:
    """Foerste meningsfulde linje, klippet. En huskeseddel skal kunne skimmes."""
    for linje in str(tekst or "").splitlines():
        r = linje.strip().lstrip("#>-*• ").strip()
        if len(r) >= 3:
            return r[:_MAKS_TITEL]
    return "Fra en samtale"


@router.post("/memory")
def gem_som_hukommelse(body: GemSomHukommelse) -> dict:
    """Gem en besked som en post i hjernen. Owner-only via global auth."""
    indhold = str(body.content or "").strip()
    if not indhold:
        raise HTTPException(status_code=400, detail="content required")
    if len(indhold) > _MAKS_INDHOLD:
        indhold = indhold[:_MAKS_INDHOLD] + "\n…(afkortet)"

    note = str(body.note or "").strip()
    if note:
        # Brugerens egen note foerst: den siger HVORFOR det var vaerd at gemme.
        indhold = f"{note}\n\n---\n{indhold}"

    from core.tools.jarvis_brain_tools import remember_this

    svar = remember_this(
        kind="observation",
        title=_titel_af(note or indhold),
        content=indhold,
        visibility="personal",
        domain="samtale",
        session_id=str(body.session_id or ""),
        turn_id=str(body.message_id or ""),
        tags=["mobil", "gemt-af-bjørn"],
    )
    if str(svar.get("status")) != "ok":
        raise HTTPException(status_code=502, detail=str(svar.get("error") or "kunne ikke gemme"))
    return {"status": "ok", "id": svar.get("id"), "title": _titel_af(note or indhold)}
