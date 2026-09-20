"""Hvad Bjørn plejer at bede om — udledt af hans valg, ikke af hans ord.

## Beslutningen bag (20/9-2026)

Det åbne spørgsmål i Jarvis' plan var: skal mønstret fange *hvordan* Bjørn
formulerer sig, eller *hvad* han typisk beder om? Jarvis' vurdering, som jeg
delte, og som Bjørn gik med: kun det sidste er værd at bygge.

En stil-profil konvergerer mod det mest sandsynlige — altså mod gennemsnittet
af ham. Det er det modsatte af målet: noget han SELV kunne finde på er ikke
hans gennemsnit. Og bliver forslaget godt til at gætte ham, begynder det at
forme ham. Et forslag skal overraske lidt, ellers er det ikke et forslag, det
er en vane.

## Hvad signalet så ER

Serveren foreslår. Bjørn tager imod med Tab, afviser med Escape, eller skriver
sin egen besked. Mønstret tælles udelukkende over **serverens egne forslag** og
deres skæbne — hans beskeder indgår ikke i nogen form, hverken som tekst eller
som afledt træk. Det er derfor der ikke er noget at slukke af privathensyn;
kontakten findes alligevel, fordi et mønster der peger galt skal kunne tages
ud uden et deploy.

## Hvorfor en ART og ikke en formulering

Et forslag klassificeres efter hvad det beder om — at få noget VIST, at få
noget RETTET, at få noget KØRT — ikke efter hvordan det er sagt. Arten er
grov med vilje: der er cirka en håndfuld ting man beder en assistent om, og en
finere inddeling ville kræve flere valg end der nogensinde bliver truffet, før
den sagde noget.

## Horisonten er en TID

Samme lære som telemetrien fik samme dag (c3028da79): et loft på antal flytter
målevinduet når aktiviteten gør. Bruger han komponisten meget i en uge, ville
«de sidste 200 valg» blive til to dage. Derfor et fast vindue i døgn, med et
antal som ren sikkerhedsnet.

## Tærsklen

Under `MIN_VALG` siger mønstret INTET. Et forslag der retter sig efter tre
tilfældige tastetryk er ikke læring, det er overtro — og prompten er bedre
uden en linje der er gættet.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Final

logger = logging.getLogger(__name__)

#: Hvor langt tilbage valgene tæller. En TID, ikke et antal — se docstringen.
VINDUE_DAGE: Final[int] = 30
#: Rent sikkerhedsnet mod en løbsk mængde, ikke den effektive horisont.
MAKS_VALG: Final[int] = 2000
#: Under det er der intet mønster at tale om, kun støj.
MIN_VALG: Final[int] = 10
#: Hvor mange arter der nævnes i hver retning. To er nok til at pege; flere
#: bliver til en liste modellen ikke kan bruge.
MAKS_ARTER: Final[int] = 2

#: Arterne. Nøglen er hvad den HEDDER i prompten; værdierne er de verber der
#: afslører den. Grov med vilje: der er en håndfuld ting man beder om.
_ARTER: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("vise noget frem", ("vis", "se", "åbn", "aabn", "list", "find", "hvor", "hvilke")),
    ("rette noget", ("ret", "fiks", "fix", "luk", "ryd", "slet", "fjern", "opdater")),
    ("køre noget", ("kør", "koer", "start", "genstart", "deploy", "byg", "test", "commit")),
    ("forklare noget", ("hvorfor", "hvordan", "forklar", "hvad", "er", "kan", "skal")),
    ("måle noget", ("mål", "maal", "tjek", "verificer", "tæl", "taal", "sammenlign")),
)

_ANDET: Final[str] = "andet"


def art(forslag: str) -> str:
    """Hvad et forslag beder om. Altid ét ord-par, aldrig tomt.

    Første ord afgør. Et forslag er en ordre eller et spørgsmål (det håndhæver
    prompten i `composer_suggest`), og dér bærer verbet hele meningen:
    «Vis mig …», «Ret det og …», «Hvorfor fejler …».
    """
    t = " ".join((forslag or "").split()).lower()
    if not t:
        return _ANDET
    ord0 = re.split(r"[\s,.:;!?]+", t)[0].strip("«»\"'`")
    for navn, verber in _ARTER:
        if ord0 in verber:
            return navn
    return _ANDET


def _valg_i_vinduet() -> list[dict[str, str]]:
    """De terminale valg indenfor vinduet. Egen funktion, så testene kan sætte dem."""
    from datetime import UTC, datetime, timedelta

    from core.runtime.db_composer_choice import seneste_valg

    graense = (datetime.now(UTC) - timedelta(days=VINDUE_DAGE)).isoformat()
    ud = []
    for r in seneste_valg(limit=MAKS_VALG):
        if str(r.get("valg") or "") == "vist":
            continue  # står stadig åbent; ingen dom endnu
        if str(r.get("vist_at") or "") < graense:
            continue
        ud.append(r)
    return ud


def moenster() -> str:
    """Én linje til prompten — eller `""` når der ikke er noget at sige.

    Formen er bevidst en ERFARING og ikke en ordre: modellen skal vægte, ikke
    adlyde. En hård regel ville gøre forslaget forudsigeligt, og et forslag der
    altid beder om det samme er en vane, ikke et tilbud.
    """
    try:
        valg = _valg_i_vinduet()
    except Exception:
        logger.debug("composer_moenster: kunne ikke læse valgene", exc_info=True)
        return ""
    if len(valg) < MIN_VALG:
        return ""

    taget: Counter[str] = Counter()
    vraget: Counter[str] = Counter()
    for r in valg:
        a = art(str(r.get("forslag") or ""))
        if str(r.get("valg") or "") == "accepteret":
            taget[a] += 1
        else:
            vraget[a] += 1

    # Kun arter hvor dommen er ENTYDIG. En art der både tages og vrages lige
    # ofte, siger intet — og at nævne den ville bare gøre prompten længere.
    gode = [a for a, n in taget.most_common(MAKS_ARTER * 2) if n > vraget.get(a, 0)]
    daarlige = [a for a, n in vraget.most_common(MAKS_ARTER * 2) if n > taget.get(a, 0)]
    gode, daarlige = gode[:MAKS_ARTER], daarlige[:MAKS_ARTER]
    if not gode and not daarlige:
        return ""

    dele = []
    if gode:
        dele.append("han tager oftest imod når forslaget beder om at " + " eller ".join(gode))
    if daarlige:
        dele.append("han skriver oftest selv når det beder om at " + " eller ".join(daarlige))
    return "Erfaring fra hans tidligere valg: " + ", og ".join(dele) + "."


def er_taendt() -> bool:
    """Kontakten. Et mønster der peger galt skal kunne tages ud uden et deploy."""
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().composer_moenster_enabled)
    except Exception:
        return True


def prompt_linje() -> str:
    """Mønstret som det ser ud i prompten — tom streng når det er slukket."""
    if not er_taendt():
        return ""
    return moenster()
