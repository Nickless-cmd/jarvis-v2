"""Jarvis' eget forslag i komponisten — den næste OPGAVE, i Bjørns ord.

## Hvad værktøjet er, og hvad det ikke er

Komponistens forslag blev bygget på en lille lokal model der læser Jarvis'
seneste besked og gætter det næste skridt. Det virker, men stemmen er en
fremmeds: linjen står i Jarvis' skrivefelt uden at være hans.

Bjørn 24/9-2026: «i chatview er det dig selv der sætter ord på runderne...
det burde endelig osse være dig der kommer med forslag i composer?»

Værktøjet lader Jarvis lægge sit EGET forslag ned, mens han er i turen —
hvor han ved hvad han lige har lavet og hvad næste skridt er.

## Navnet blev rettet 7/10-2026 — det pegede på den forkerte opgave

Det hed `suggest_next_message`, og «message» lyder som en replik i en
samtale, altså smalltalk. Det Jarvis faktisk skal give er den næste OPGAVE:
den instruks Bjørn ville skrive for at sætte arbejdet i gang. Bjørn:
«den burde hedde suggest_next_task og være dit forslag med mine ord til
næste opgave». Navnet er derfor `suggest_next_task`, og formålet er skrevet
om i både prompten og beskrivelsen nedenfor — de sagde før to forskellige
ting (hans stemme i prompten, Jarvis' egen i beskrivelsen).

## Der er ingen anden kilde længere

Den lokale model (qwen3:4b) blev droppet 28/9-2026 efter en måling: af 428
viste forslag kom 411 fra modellen, og Jarvis' egne blev valgt 23,5 % af
gangene mod modellens 2,9 %. Siden da svarer `composer_suggest` TOMT når
Jarvis ikke har lagt noget ned. Konsekvensen er værd at kende: tier han, er
feltet tomt — der er ikke længere et dårligt forslag der fylder hullet.

## Hvorfor «tilbud» blev svækket

Kalder han det ikke, sker der ingenting teknisk. Men med modellen væk er
fraværet ikke neutralt: et tomt felt ER resultatet. Kalder han det, står
hans eget næste skridt der — i Bjørns ord, så det kan sendes med ét tryk.
"""
from __future__ import annotations

from typing import Any


def _exec_suggest_next_task(args: dict[str, Any]) -> dict[str, Any]:
    tekst = str(args.get("tekst") or "").strip()
    if not tekst:
        return {"status": "error", "error": "tekst er påkrævet"}

    session_id = str(args.get("_runtime_session_id") or "").strip()
    if not session_id:
        return {"status": "error", "error": "ingen session at lægge forslaget i"}

    from core.runtime.db_composer_jarvis import gem_forslag, kig_forslag

    fid = gem_forslag(
        session_id=session_id,
        forslag=tekst,
        kilde_besked_id=str(args.get("kilde_besked_id") or ""),
    )
    if not fid:
        return {"status": "error", "error": "kunne ikke gemme forslaget"}

    # Læs tilbage og bekræft — et «ok» er først bevis når rækken står der.
    # `kig_forslag` og ikke `tag_forslag`: bekræftelsen må ikke forbruge det
    # forslag Bjørn endnu ikke har set.
    gemt = kig_forslag(session_id=session_id)
    bekræftet = bool(gemt and gemt.get("forslag_id") == fid)
    return {
        "status": "ok" if bekræftet else "error",
        "confirmed": bekræftet,
        "forslag_id": fid,
        "forslag": str(gemt.get("forslag") if gemt else tekst),
        "note": (
            "Forslaget ligger klar i komponisten når feltet er tomt og svaret "
            "er færdigt. Det forbruges ved første hentning."
        ),
    }


COMPOSER_SUGGEST_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "suggest_next_task",
        "description": (
            "Læg den NÆSTE OPGAVE i Bjørns skrivefelt, formuleret i HANS ord — "
            "den instruks han ville sende for at sætte arbejdet i gang. Ikke en "
            "replik i samtalen, ikke et svar, ikke en kommentar. Bruges når du "
            "selv kan se hvad næste skridt er, typisk efter en teknisk runde "
            "hvor du lige har lavet noget: så ved du bedre end nogen model hvad "
            "der følger. Én linje, højst ti ord, dansk — en ordre han kunne "
            "sende. Den venter i hans komponist til han skriver, og overlever "
            "en app-genstart. Siden 28/9-2026 er der INGEN lokal model bag: "
            "springer du det over, står feltet tomt."
        ),
        "parameters": {"type": "object", "properties": {
            "tekst": {
                "type": "string",
                "description": (
                    "Forslaget til Bjørns næste besked. Én linje, højst ti "
                    "ord, dansk. En ordre eller et spørgsmål — aldrig et svar."
                ),
            },
            "kilde_besked_id": {
                "type": "string",
                "description": "Valgfri: id på den besked forslaget hører til.",
            },
        }, "required": ["tekst"]},
    }},
]

COMPOSER_SUGGEST_TOOL_HANDLERS: dict[str, Any] = {
    "suggest_next_task": _exec_suggest_next_task,
}
