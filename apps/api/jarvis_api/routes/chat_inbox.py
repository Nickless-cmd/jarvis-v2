"""Bjørns egen vej ind i indbakken — den fjerde skriver.

Udskilt som sin egen rute-flade fra starten. `chat.py` står på 2.030 linjer, og
Boy Scout-reglen gælder: en ny rute er mere end 20 linjer. Samme mønster som
`chat_workspace_trust.py` fik 3/10 — ruten bor her, og `app.py` inkluderer den.

## Hvorfor der ikke bygges et nyt endpoint-system

Indbakken HAVDE tre skrivere: Jarvis gennem verificeret proveniens, huset
gennem `paastaaet_ejer="huset"`, og `ukendt` når intet kunne bevises. Det der
manglede var ikke en kø — det var en vej hvor en **menneskelig handling**
opretter en post.

Huset har i forvejen seks køer (instrument-fund, autonomi-forslag,
godkendelser, USER.md- og MEMORY.md-forslag, side-tasks, `inbox_items`), og
mønstret målt fire gange 3.-4./10 er at en kø uden skriver, læser eller lukker
er tavst ubrugelig. En syvende ville arve den risiko. Indbakken har allerede
id'er, proveniens, terminale tilstande, retention, et loft med «+N mere», tre
værktøjer, en prompt-sektion og et hændelses-spor.

## Gater ikke som standard

Bjørns afgørelse 4/10: «synlig men gater ikke som standard». `bloker` er falsk
med mindre han beder om det, og så er det et valg frem for en bivirkning.

Faren ved det modsatte er målt samme dag: en post der gater kan spærre for
netop de værktøjer der skulle rette den — dead-locken i
`mark_wakeup_consumed`, hvor `inbox_done` nægtede og vejen ud gik gennem det
værktøj gaten blokerede.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class InboxFlagRequest(BaseModel):
    """Det et menneske flagger.

    Ingen `bruger_id`. Den kommer fra den autentificerede kontekst, aldrig fra
    kaldet — et felt kalderen vælger er en påstand, ikke proveniens, og det er
    hele grunden til at `registrer_kilde` findes i den form den har.
    """
    titel: str = ""
    beskrivelse: str = ""
    #: Må denne post nægte Jarvis en mutation? Falsk som standard.
    bloker: bool = False


@router.post("/inbox/flag")
def flag_i_indbakken(req: InboxFlagRequest) -> dict[str, object]:
    """Opret en post i den autentificerede brugers indbakke.

    Svarer typet. En tom titel afvises med 400 frem for at blive en stum post:
    skrive-kontraktens betingelse 2 siger at en post der ikke kan navngives i
    visningen ikke må gate, og en post uden titel kan ikke navngives.
    """
    titel = (req.titel or "").strip()
    if not titel:
        raise HTTPException(status_code=400, detail="titel kraeves")

    from core.identity.workspace_context import (
        current_user_id,
        current_workspace_name,
    )
    # Samme asymmetri som resten af indbakken: et token uden bruger-id er
    # ejerens egen, ubundne vej, og 882 af 4.462 beskeder paa to doegn bar
    # praecis den form. Falder vi tilbage til workspacet, rammer posten den
    # indbakke visningen ogsaa laeser.
    bruger = (str(current_user_id() or "").strip()
              or str(current_workspace_name() or "").strip())
    if not bruger:
        raise HTTPException(status_code=401, detail="ingen autentificeret bruger")

    from core.services.inbox_state import flag_fra_bruger
    r = flag_fra_bruger(bruger_id=bruger, titel=titel,
                        beskrivelse=(req.beskrivelse or "").strip(),
                        bloker=bool(req.bloker))
    if r.get("status") != "ok":
        raise HTTPException(status_code=500, detail=str(r.get("error") or "ukendt fejl"))
    return {"status": "ok", "id": r.get("id"), "bloker": r.get("bloker")}
