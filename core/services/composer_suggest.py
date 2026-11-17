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
from datetime import UTC, datetime, timedelta
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

#: (Reglen om en «stump til sidst» — `MIN_SVAR_TEGN` — stod her indtil
#: 17/11-2026. Den gjaldt et forslag bygget på samtalen; et forslag Jarvis selv
#: har lagt ned bærer sin egen kontekst og skal ikke afvises fordi det sidste
#: svar er kort. Efter en genstart er det netop tilfældet.)


def _samtale(session_id: str) -> list[dict[str, str]]:
    """De seneste beskeder. Egen funktion, så testene kan sætte dem.

    ROD (målt 18/10-2026): vinduet var `recent_chat_session_messages(limit=6)`,
    som tæller ALLE roller. I en tool-tung session er de sidste seks rækker
    `tool`-resultater, så der var nul `user`/`assistant` tilbage — og funktionen
    returnerede tomt FØR den nåede til Jarvis' eget forslag. Målt på Bjørns
    session (866 rækker): 6 af 6 rækker var `tool`, forslaget lå klar i
    `composer_jarvis_forslag` og blev aldrig vist. Komponisten stod tom.

    `recent_chat_session_messages_by_user_turns` ankrer i USER-beskeder i
    stedet, så vinduet altid indeholder rigtige samtale-runder. Samme
    begrundelse som prompt-stien fik 9/6-2026 (se dens docstring): et
    råtals-vindue drukner i tool-rækker.
    """
    from core.services.chat_sessions import recent_chat_session_messages_by_user_turns
    return recent_chat_session_messages_by_user_turns(session_id, user_turns=MAKS_HISTORIK)


#: Hvor længe et forslag fra Jarvis stadig må tilbydes. Loftet erstattede
#: 17/11-2026 forældelses-reglen (2+ assistent-svar → ryd): den målte «samtalen
#: er kørt videre» og ramte dermed også et forslag Bjørn lige havde taget med
#: Tab, så snart næste tur begyndte. Alders-loftet rammer kun det der faktisk
#: er gammelt, og lader forslaget overleve både genstart og flere ture.
FORSLAG_MAKS_ALDER_H: Final[int] = 24


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


def _foraeldet(skrevet_at: str) -> bool:
    """Er forslaget ældre end `FORSLAG_MAKS_ALDER_H`?

    Ukendt eller ulæselig tid giver False — den sikre side er at tilbyde det
    for meget frem for at rydde et bud vi ikke kan aldersbestemme.
    """
    tid = _til_tid(skrevet_at)
    if tid is None:
        return False
    alder = datetime.now(UTC) - tid
    return alder > timedelta(hours=FORSLAG_MAKS_ALDER_H)


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

    ## Omlagt 17/11-2026: forslaget hører til SESSIONEN, ikke til turen

    Bjørn: «der ligger ikk noget i komponisten... han har været genstartet og
    så forsvinder dit forslag». Målt i `composer_choices` og `chat_messages`:
    forslaget blev vist 11:30:31, taget med Tab 11:31:00 og ryddet ved
    turstart 11:31 — 58 minutter før han kiggede. Det var ikke genstarten der
    slettede det; det var to regler der begge målte «samtalen er kørt videre»:

      1. `chat_sessions._ryd_komponist_forslag` ryddede ved nyt tur-start så
         snart forslaget blot var SET (`er_vist`).
      2. Forældelses-reglen her ryddede efter 2+ assistent-svar.

    Tilsammen gjorde de hentningen éngangs: forslaget kunne ikke hentes igen
    efter en genstart, fordi den næste tur allerede havde fjernet det. Begge
    er nu erstattet af ét spørgsmål — blev forslaget BRUGT? — plus et alders-
    loft, så et gammelt bud ikke kan hænge for evigt:

      * `afvist` (Escape) eller `eget` (han skrev selv) → ryddes. Han sagde nej.
      * hans besked indeholder forslagets tekst → ryddes. Det blev brugt.
      * nyere forslag i samme session → afløser det (`gem_forslag` holder ét).
      * ældre end `FORSLAG_MAKS_ALDER_H` → ryddes. Det peger på arbejde der er
        kørt videre.

    Det var den anden halvdel af fejlen at opslaget lå BAG fire tidlige
    return (tom samtale, tur i gang, stump til sidst). Efter en genstart er
    vinduet kort, og så returnerede funktionen tomt uden at kigge i basen —
    rækken kunne ligge der hele dagen uden at blive vist. Opslaget sker derfor
    nu først; kun «hans besked venter stadig på svar» kan holde det tilbage,
    for dér er der ingen næste besked at foreslå.
    """
    sid = (session_id or "").strip()
    if not sid:
        return _tomt()
    try:
        raekker = _samtale(sid)
    except Exception:
        logger.debug("composer_suggest: kunne ikke læse samtalen", exc_info=True)
        raekker = []
    beskeder = [
        b for b in raekker
        if str(b.get("role") or "") in ("user", "assistant")
        and str(b.get("content") or "").strip()
    ]
    # Står der en ubesvaret besked fra ham, er turen i gang. At foreslå en ny
    # besked dér er at tale i munden på et svar der er på vej — og forslaget
    # skal blive liggende, ikke forbruges.
    if beskeder and str(beskeder[-1].get("role") or "") == "user":
        return _tomt()

    # Jarvis' EGET forslag (24/9-2026). Bjørn: «det burde endelig osse være
    # dig der kommer med forslag i composer». Skriver han selv linjen, er den
    # bedre end en 4b-model der kun læser én besked — han ved hvad han lige
    # har lavet, og hvad næste skridt er. Findes det ikke, står pladsholderen
    # tom — den lokale model blev droppet 28/9-2026.
    #
    # Hentningen FORBRUGER IKKE (Bjørn 6/10-2026: forslaget skal overleve en
    # app-genstart). `kig_forslag` læser uden at slette, så en genstart er
    # blot endnu en hentning.
    eget = None
    try:
        from core.runtime.db_composer_jarvis import (
            kig_forslag,
            kig_forslag_til_klient,
            ryd_forslag,
        )
        eget = kig_forslag(session_id=sid)
        if eget and _foraeldet(str(eget.get("skrevet_at") or "")):
            ryd_forslag(session_id=sid)
            eget = None
        # 30/10-2026: er der intet forslag i HANS session, falder vi tilbage
        # til et USET, friskt forslag fra en autonom koersel. Maalt: 6 af 8
        # auto-forslag blev aldrig vist, fordi opslaget var bundet til den
        # session de blev skrevet i.
        if not eget:
            eget = kig_forslag_til_klient(session_id=sid)
    except Exception:
        logger.debug("composer_suggest: kunne ikke læse Jarvis' forslag", exc_info=True)
        eget = None
    if eget and str(eget.get("forslag") or "").strip():
        kilde = next(
            (str(b.get("message_id") or "") for b in reversed(beskeder)
             if str(b.get("role") or "") == "assistant"),
            "",
        )
        return {
            "forslag": str(eget["forslag"]).strip(),
            "forslag_id": str(eget.get("forslag_id") or ""),
            "kilde_besked_id": kilde,
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
