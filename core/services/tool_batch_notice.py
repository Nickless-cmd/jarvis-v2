"""Vink til modellen om at kalde flere uafhængige værktøjer i SAMME runde.

## Hvorfor det findes

Målt 13/9-2026 på tre timers kørsel: **304 af 366 agentiske runder kaldte
præcis ét værktøj.** Kun 62 batchede to eller flere, og én enkelt runde nåede
fire. Rundebudgettet er 30; med ét kald pr. runde er det 30 handlinger til et
stykke arbejde der let kræver hundrede — og så løber turen tør, runder af, og
Bjørn skriver «Forsæt». Det gjorde han 24 gange det døgn.

Der er intet loft i koden; modellen bestemmer selv. Derfor er løftestangen et
vink, ikke en grænse.

## Hvorfor det ikke fyrer hver runde

Et vink der står i hver eneste runde er ikke et vink, det er en baggrundslyd —
og det koster kontekst i hver runde af en lang tur. Det fyrer kun når det
faktisk kan gøre en forskel: når den FORRIGE runde nøjedes med ét kald, og kun
et par gange pr. tur. Har han forstået det, tier vi.

Samme form som `round_budget_notice`: en ren funktion der returnerer teksten
eller «», og en kalder der hænger den på som en efterfølgende user-tur, så
cache-præfikset er urørt.
"""
from __future__ import annotations

#: Hvor mange gange vinket må fyre i én tur. Tre er nok til at etablere vanen;
#: derefter er det nag.
MAKS_PR_TUR = 3

#: Vinket giver først mening når der er runder nok tilbage til at bruge det.
MIN_RUNDER_TILBAGE = 3


def tool_batch_notice(
    *,
    forrige_runde_kald: int,
    runder_tilbage: int,
    gange_vist: int,
    forrige_forrige_kald: int | None = None,
) -> str:
    """Vinket, eller «» når det ikke ville hjælpe.

    `forrige_runde_kald` er antallet af værktøjskald i runden før denne — 0 hvis
    der ikke var nogen (første runde, eller en ren tekst-runde).

    `forrige_forrige_kald` er det samme tal én runde længere tilbage.

    ## Hvorfor det andet tal kom til (4/10-2026)

    Betingelsen var `forrige_runde_kald == 1` — et ANTAL. Men et enkelt kald er
    ikke et bevis på at der var noget at batche; det er ofte det ENESTE rigtige
    kald, fordi det næste skal bygge på resultatet. Vinket fyrede derfor også
    midt i en strengt sekventiel kæde (læs → mål → beslut → læs), hvor der ikke
    fandtes to uafhængige kald at slå sammen.

    Målt i drift: vinket fyrede i en tur hvor hvert kald ventede på det forrige,
    og sagde «Du kaldte ét værktøj i sidste runde» om noget der var korrekt.
    Bjørn 4/10: «den genere dig».

    Fixet kræver at MØNSTERET gentager sig: to runder i træk med præcis ét kald
    er en vane på vej. Ét enkelt kald er normal sekventiel udførelse.

    Er tallet ukendt (None), tier vi: et vink vi ikke kan begrunde, sender vi
    ikke. Det er den samme fail-retning som resten af filen — hellere tie end
    at påstå noget usandt om en runde.
    """
    try:
        kald = int(forrige_runde_kald)
        tilbage = int(runder_tilbage)
        vist = int(gange_vist)
    except Exception:
        return ""

    if vist >= MAKS_PR_TUR:
        return ""
    if tilbage < MIN_RUNDER_TILBAGE:
        # Tæt på døren er rundebudget-varslet det vigtigste; to beskeder om
        # rytmen i samme runde trækker i hver sin retning.
        return ""
    if kald != 1:
        # 0 kald: der var ikke noget at batche. 2+: han gør det allerede.
        return ""
    # Mønsteret, ikke det enkelte kald — se docstringen. `int(None)` kaster, så
    # en kalder der ikke kender tallet får tavshed i stedet for et gæt.
    try:
        forrige = int(forrige_forrige_kald)  # type: ignore[arg-type]
    except Exception:  # tavs med vilje: None/ikke-tal = «historikken kendes ikke»
        # Vi tier frem for at gaette. Se docstringen: et vink vi ikke kan
        # begrunde, sender vi ikke. Der er intet at logge — None er et
        # LOVLIGT svar fra en kalder der kun har ét runders tal.
        return ""
    if forrige != 1:
        return ""

    return (
        "💡 Du kaldte ét værktøj i sidste runde. Kald de værktøjer der ikke "
        "afhænger af hinandens resultat i SAMME runde — de køres i samme batch, "
        "og hver runde koster af dit budget. Kald der bygger på et resultat "
        "skal selvfølgelig stadig vente på det."
    )
