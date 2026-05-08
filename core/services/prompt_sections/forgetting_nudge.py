"""Forgetting nudge — reminds Jarvis to consider transience during conversation.

Fase 2 i learning-to-forget. Modstykke til memory_consolidation_nudge:
den minder om at GEME, denne minder om at OVERVEJE GLEMSEL.

Injecterer et kort signal i prompten der spørger:
- Er noget af det her forbigående? Markér det med lav importance.
- Er noget af det her vigtigt? Markér det med høj importance.

Kører hver tur (kort nok til at være ubetydeligt i prompt-budgettet).
Jarvis kan vælge at ignorere det — det er en nudge, ikke en ordre.
"""
from __future__ import annotations

_NUDGE_TEXT = (
    "💡 Glemsels-nudge: Hvis noget i denne samtale er "
    "forbigående (en midlertidig besked, et hurtigt fix, "
    "snak der ikke skal gemmes), så kald `remember_this` "
    "med `importance=0.3` eller arkivér det bagefter. "
    "Omvendt: Hvis noget er vigtigt — markér med "
    "`importance=0.9`. Din pruning-daemon bruger "
    "importance til at afgøre hvad der overlever."
)


def forgetting_nudge_section() -> str:
    """Return forgetting nudge text — fires every turn unconditionally.

    Kort nok (~300 chars) til at være negligible i prompt-budgettet.
    Ignoreres let hvis irrelevant; giver værdi når samtalen indeholder
    noget der bør markeres som transient eller vigtigt.
    """
    return _NUDGE_TEXT
