"""Forslag i komponisten — hvad der kunne skrives videre, mens man skriver.

## Hvem der foreslår (ændret 28/9-2026)

Forslaget kommer udelukkende fra Jarvis selv, gennem værktøjet
`suggest_next_task`. Den lokale model (qwen3:4b) skrev tidligere et bud når
han ikke selv lagde et ned; den blev droppet efter Bjørns måling og dom: «drop
den anden models forslag og kun bruge dine... den anden model viser lorte
forslag». Af 428 viste forslag kom 411 fra modellen, og de blev valgt 2,9 % af
gangene mod 23,5 % for hans egne.

Den anden vej — fortsættelsen af en halvskreven sætning — stod her indtil
28/9-2026. Ingen flade brugte den: begge klienter sender et tomt udkast, fordi
et gæt på resten af hans sætning føltes forkert. Den er nu fjernet sammen med
model-kaldet, prompten og hele dens apparat. Modulet kalder ikke længere nogen
model overhovedet.

Det er et bevidst tab af dækning: uden et eget forslag står pladsholderen TOM.
Et tomt felt er ærligere end et dårligt forslag.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Final

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────── forslag til den NÆSTE besked
#
# Desk viser forslaget dér hvor pladsholderen står — i det TOMME felt, ikke
# som grå tekst der dukker op midt i en sætning man er i gang med at skrive.
# Bjørn 17/9-2026: «det kommer dumpende mens jeg skriver, det er virkelig
# træls». Et forslag der konkurrerer med hans egne ord er en afbrydelse; et
# forslag der står og venter i det tomme felt er et tilbud.
#
# Det ændrer hvad forslaget ER: ikke resten af en sætning, men et helt bud på
# hvad han kunne sige nu. Derfor er kilden samtalen og ikke udkastet — der er
# jo ikke noget udkast.

#: Hvor mange rækker der HENTES. Kun den sidste bruges — den bærer
#: kilde-beskeden; de øvrige afgør om turen er i gang.
MAKS_HISTORIK: Final[int] = 6

#: Under det er assistentens sidste besked en stump — «4.», «Generation
#: cancelled.», «OK» — og der er intet at bygge et næste skridt på. Målt
#: 17/9-2026: netop dér svarede modellen «Fire. Det er nemt.» og «Jeg forstår
#: ikke, hvad du mener», altså replikker i samtalen frem for forslag.
MIN_SVAR_TEGN: Final[int] = 40


def _samtale(session_id: str) -> list[dict[str, str]]:
    """De seneste beskeder. Egen funktion, så testene kan sætte dem."""
    from core.services.chat_sessions import recent_chat_session_messages
    return recent_chat_session_messages(session_id, limit=MAKS_HISTORIK)


#: Hvor mange assistent-svar der hentes naar foraeldelsen afgoeres. Vi skal
#: kun vide om der er 0, 1 eller 2+ — men tællingen maa ikke komme fra
#: `_samtale`s vindue. I en tool-tung session fylder `tool`-raekker vinduet, og
#: tællingen saa kun ÉT svar efter forslaget og kaldte et foraeldet bud for
#: aktuelt. Maalt 7/10-2026: et forslag skrevet 18:23 blev returneret som
#: «aktuelt» efter hver tur resten af aftenen, og raekken blev aldrig ryddet.
_FORAELDELSE_VINDUE: Final[int] = 50


def _til_tid(iso: str):
    """ISO-tid → `datetime`, uanset om den slutter paa `Z` eller `+00:00`.

    De to former blandes i huset: `composer_jarvis_forslag.skrevet_at` skrives
    med `Z`, mens `chat_messages.created_at` skrives med `+00:00`. En ren
    streng-sammenligning er derfor et gæt — `Z` sorterer EFTER `+`, saa en
    besked skrevet i samme mikrosekund ville blive laest som ældre end
    forslaget og talt med som «ikke efter».
    """
    if not iso:
        return None
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:  # ikke en ISO-tid — vi VED det ikke, og gaetter ikke
        return None


def _svar_efter(session_id: str, skrevet_at: str) -> int:
    """Antal assistent-svar NYERE end `skrevet_at` — talt i SQL, ikke i et vindue.

    Egen funktion, saa testene kan saette tallet direkte: reglen (0 = turen er
    ikke landet, 1 = forslaget hoerer til svaret nederst, 2+ = samtalen er
    koert videre) er dét der proves, og den skal ikke afhaenge af hvor mange
    `tool`-raekker der tilfaeldigt ligger i et vindue.
    """
    from core.runtime.db import connect
    graense = _til_tid(skrevet_at)
    if graense is None:
        return 0
    with connect() as conn:
        raekker = conn.execute(
            "SELECT created_at FROM chat_messages "
            "WHERE session_id = ? AND role = 'assistant' "
            "ORDER BY id DESC LIMIT ?",
            (session_id, _FORAELDELSE_VINDUE),
        ).fetchall()
    n = 0
    for raekke in raekker:
        tid = _til_tid(str(raekke["created_at"] or ""))
        if tid is not None and tid > graense:
            n += 1
    return n


def _tomt() -> dict[str, str]:
    """Intet forslag — og dermed intet at melde tilbage om."""
    return {"forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def foreslaa_naeste(session_id: str) -> str:
    """Et bud på brugerens næste besked, eller `""`.

    Kaster aldrig: komponisten skal virke uanset hvad der sker. Et forslag er
    en bekvemmelighed, ikke en funktion man kan miste.
    """
    return foreslaa_naeste_detaljer(session_id)["forslag"]


def foreslaa_naeste_detaljer(session_id: str) -> dict[str, str]:
    """Forslaget OG det klienten skal bruge for at kunne melde valget tilbage.

    Tre felter: `forslag`, `forslag_id` og `kilde_besked_id`. Id'et fødes her
    og gemmes IKKE — serveren husker ingenting om et forslag der måske aldrig
    kommer på skærmen (se `db_composer_choice`). Klienten sender de to id'er
    tilbage når forslaget vises og når det bliver valgt eller vraget.

    Tomt forslag → tomme id'er. Der er ikke noget at melde tilbage om.
    """
    sid = (session_id or "").strip()
    if not sid:
        return _tomt()
    try:
        raekker = _samtale(sid)
    except Exception:
        logger.debug("composer_suggest: kunne ikke læse samtalen", exc_info=True)
        return _tomt()
    beskeder = [
        b for b in raekker
        if str(b.get("role") or "") in ("user", "assistant")
        and str(b.get("content") or "").strip()
    ]
    if not beskeder:
        return _tomt()
    # Står der en ubesvaret besked fra ham, er turen i gang. At foreslå en ny
    # besked dér er at tale i munden på et svar der er på vej.
    if str(beskeder[-1].get("role") or "") != "assistant":
        return _tomt()
    # En stump til sidst («4.», «Generation cancelled.») er ikke et svar der
    # peger nogen steder hen — og et forslag på den ville være et bud uden
    # noget at bygge på.
    if len(" ".join(str(beskeder[-1].get("content") or "").split())) < MIN_SVAR_TEGN:
        return _tomt()

    # Jarvis' EGET forslag (24/9-2026). Bjørn: «det burde endelig osse være
    # dig der kommer med forslag i composer». Skriver han selv linjen, er den
    # bedre end en 4b-model der kun læser én besked — han ved hvad han lige
    # har lavet, og hvad næste skridt er. Findes det ikke, står pladsholderen
    # tom — den lokale model blev droppet 28/9-2026.
    #
    # Hentningen FORBRUGER IKKE laengere (Bjoern 6/10-2026: forslaget skal
    # overleve en app-genstart). Foer slettede `tag_forslag` raekken, saa
    # klienten der hentede holdt den eneste kopi — en genstart tabte baade
    # hukommelsen og raekken, og forslaget var vaek uden at nogen havde set det.
    #
    # Foraeldelsen afgoeres nu paa TID. Forslaget skrives MENS turen koerer,
    # altsaa foer svaret persisteres, saa antallet af assistent-beskeder EFTER
    # `skrevet_at` siger alt: 0 = turen er ikke landet endnu, 1 = forslaget
    # hoerer til svaret nederst, 2+ = samtalen er koert videre og buddet er
    # foraeldet. Se modul-docstringen i `db_composer_jarvis`.
    try:
        from core.runtime.db_composer_jarvis import kig_forslag, ryd_forslag
        eget = kig_forslag(session_id=sid)
        if eget:
            skrevet = str(eget.get("skrevet_at") or "")
            if skrevet and _svar_efter(sid, skrevet) >= 2:
                # Foraeldet. Ryd raekken, saa den ikke bliver maalt igen og
                # ikke ligger og fylder.
                ryd_forslag(session_id=sid)
                eget = None
    except Exception:
        logger.debug("composer_suggest: kunne ikke læse Jarvis' forslag", exc_info=True)
        eget = None
    if eget and str(eget.get("forslag") or "").strip():
        return {
            "forslag": str(eget["forslag"]).strip(),
            "forslag_id": str(eget.get("forslag_id") or ""),
            "kilde_besked_id": str(beskeder[-1].get("message_id") or ""),
        }

    # Her stod den lokale models forslag (qwen3:4b) indtil 28/9-2026.
    # Bjørn: «drop den anden models forslag og kun bruge dine... den anden
    # model viser lorte forslag». Målt i `composer_choices`: af 428 viste
    # forslag kom 411 fra modellen og 17 fra Jarvis selv — og hans egne blev
    # valgt 23,5 % af gangene mod modellens 2,9 %, altså otte gange så ofte.
    # Modellen læste ÉN besked og gættede i blinde; Jarvis ved hvad han lige
    # har lavet. Uden et eget forslag står pladsholderen tom — et tomt felt
    # er bedre end et dårligt forslag.
    return _tomt()
