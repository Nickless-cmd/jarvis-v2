"""Fortael ham hvor mange runder han har tilbage, foer doeren smaekker.

Bjoern 6/9-2026: «han rammer den 30-runde regel og bliver afbrudt. Intet tvinger
ham til at afslutte, den cutter ham bare.»

Maalt: 12 af 658 runs naar runde 30. Sjaeldent i alt (1,8 %) — men det er
praecis dybdearbejdet, og faldet fra runde 23 til 30 er blidt: naar han foerst
graver, bliver han ved.

Mekanismen FINDES: loop-gaten returnerer RED paa sidste runde, tools fjernes
fysisk, og der paahaeftes «skriv nu dit endelige svar». Problemet er at den
kommer uden varsel — den ene runde arbejder han, den naeste er vaerktoejerne
vaek. Fra hans side er det ikke en afrunding, det er en doer der smaekker
midt i en taenkning.

Bjoern spurgte om runderne kunne goeres laengere. Det kan de ikke som knap:
intet i koden begraenser hvor mange vaerktoejer han kalder pr. runde — modellen
vaelger selv. Loeftestangen er at BATCHE, og den kan han kun traekke i hvis han
ved at budgettet er ved at slippe op.

Beskeden er append-only paa en trailing user-tur: cache-praefikset (system +
tools + historik) er uroert, saa varslet koster ingen cache — modsat selve
finalize-runden, hvor tools fjernes fysisk.
"""

from __future__ import annotations

# Hvor mange runder foer loftet varslet begynder. Fem giver plads til at samle
# de sidste kald og skrive et ordentligt svar; et varsel paa den sidste runde
# ville vaere det samme som ingen varsel.
_VARSEL_FRA = 5


def round_budget_notice(*, round_index: int, max_rounds: int) -> str:
    """Varsel til modellen naar rundebudgettet slipper op. "" ellers.

    `round_index` er 0-baseret som i loopet; `max_rounds` er loftet. Den SIDSTE
    runde faar intet varsel herfra — den har allerede sin egen tvungne
    finalize-instruktion, og to beskeder om det samme ville stoeje.
    """
    try:
        r = int(round_index)
        mx = int(max_rounds)
    except Exception:
        return ""
    if mx <= 1 or r < 0:
        return ""

    tilbage = mx - 1 - r          # antal runder EFTER denne, foer finalize
    if tilbage <= 0 or tilbage > _VARSEL_FRA:
        return ""

    if tilbage == 1:
        return (
            "⏳ Sidste arbejdsrunde. Efter denne kan du ikke kalde flere "
            "værktøjer — så kald nu det du mangler, og gør dig klar til at "
            "skrive dit endelige svar."
        )
    return (
        f"⏳ Du har {tilbage} arbejdsrunder tilbage af {mx}. Saml de "
        "resterende værktøjskald i så få runder som muligt — du må gerne "
        "kalde flere værktøjer i samme runde — og begynd at runde af, så du "
        "ikke bliver afbrudt midt i en tanke."
    )
