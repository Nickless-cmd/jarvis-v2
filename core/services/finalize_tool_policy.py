"""Skal den tvungne afslutnings-runde FJERNE vaerktoejslisten — eller raekker et flag?

## Hvorfor spoergsmaalet koster penge

Prompten sendes som [systemprompt, vaerktoejsliste, samtale]. DeepSeeks
praefiks-cache genkender fra begyndelsen og fremad, saa forsvinder
vaerktoejslisten, er ALT efter systemprompten nyt — ogsaa selvom samtalen staar
ord for ord som i runden foer.

Maalt paa CT105 28/9-2026, run `f3897d2bde28`:

    runde 43   hit 99.584   miss  77.175
    runde 44   hit  9.600   miss 118.211   <- vaerktoejerne fjernet

Genkendelsen faldt til det systemprompten fylder. Merpris paa den ene runde:
41.036 tokens. Det rammer kun runs der loeber ind i rundeloftet — 2 af dagens
30 — men det er den dyreste enkeltrunde de har.

## Hvorfor listen blev fjernet i foerste omgang

`tool_choice="none"` beder modellen lade vaere. Mange modeller ignorerer det,
og saa loeb turen videre uden nogensinde at give brugeren prosa. Derfor
fjernede man listen fysisk: saa KAN ingen model kalde noget.

Prisen for den garanti er den kolde runde. Den er kun noedvendig hos de
udbydere der faktisk ignorerer flaget.

## Hvad der er maalt, ikke antaget

DeepSeek, 28/9-2026, tre gange, uden afslutnings-instruktion saa fristelsen var
aegte (spoergsmaalet bad om et opslag modellen ikke havde lavet endnu):

    vaerktoejer med, intet flag  -> kaldte search_memory      (kontrollen holder)
    vaerktoejer med, flag=none   -> 0 kald, 387 tegn prosa    (den adlyder)
    vaerktoejer fjernet          -> 0 kald, 588 tegn prosa    (som i dag)

Kontrollen er det vigtige led: foerste forsoeg havde afslutnings-instruktionen
med, og saa kaldte kontrollen heller ingenting — testen maalte ingenting.

Listen er en HVIDLISTE, ikke en sortliste. En ukendt udbyder faar den fysiske
fjernelse, altsaa det garanterede svar. At gaette forkert den anden vej koster
brugeren et svar; at gaette forkert denne vej koster kun tokens.
"""
from __future__ import annotations

#: Udbydere hvor `tool_choice="none"` er MAALT til at blive adlydt, og hvor
#: flaget faktisk naar payloaden. `visible_followup` sender kun tool_choice
#: videre til openai-compat-adapteren — en udbyder der ikke faar flaget ville
#: kalde vaerktoejer uanset hvad den ellers kan.
_ADLYDER_TOOL_CHOICE_NONE = frozenset({"deepseek"})


def behold_vaerktoejer_paa_finalize(provider: str) -> bool:
    """Maa den tvungne afslutning beholde vaerktoejslisten hos denne udbyder?

    True  → behold listen, saet `tool_choice="none"`; praefikset er urørt.
    False → fjern listen fysisk; ét koldt kald, men et garanteret svar.
    """
    return (provider or "").strip().lower() in _ADLYDER_TOOL_CHOICE_NONE
