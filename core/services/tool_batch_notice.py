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
) -> str:
    """Vinket, eller «» når det ikke ville hjælpe.

    `forrige_runde_kald` er antallet af værktøjskald i runden før denne — 0 hvis
    der ikke var nogen (første runde, eller en ren tekst-runde).
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

    return (
        "💡 Du kaldte ét værktøj i sidste runde. Kald de værktøjer der ikke "
        "afhænger af hinandens resultat i SAMME runde — de køres i samme batch, "
        "og hver runde koster af dit budget. Kald der bygger på et resultat "
        "skal selvfølgelig stadig vente på det."
    )
