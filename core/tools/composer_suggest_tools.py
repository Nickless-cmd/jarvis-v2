"""Jarvis' eget forslag i komponisten — «hvad kunne Bjørn skrive nu?».

## Hvad værktøjet er, og hvad det ikke er

Komponistens forslag blev bygget på en lille lokal model der læser Jarvis'
seneste besked og gætter det næste skridt. Det virker, men stemmen er en
fremmeds: linjen står i Jarvis' skrivefelt uden at være hans.

Bjørn 24/9-2026: «i chatview er det dig selv der sætter ord på runderne...
det burde endelig osse være dig der kommer med forslag i composer?»

Værktøjet lader Jarvis lægge sit EGET forslag ned, mens han er i turen —
hvor han ved hvad han lige har lavet og hvad næste skridt er. Ligger der et,
bruger `composer_suggest.foreslaa_naeste_detaljer` hans og springer modellen
over; gør der ikke, falder den tilbage til den lokale model, præcis som før.

## Det er et tilbud, ikke en pligt

Kalder han det ikke, sker der ingenting — komponisten virker som i dag. Det
er med vilje: et forslag han føler sig FORPLIGTET til at skrive hver tur ville
blive et pligtløb og ikke et bud. Han kalder det når han faktisk har et næste
skridt at pege på.
"""
from __future__ import annotations

from typing import Any


def _exec_suggest_next_message(args: dict[str, Any]) -> dict[str, Any]:
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
        "name": "suggest_next_message",
        "description": (
            "Læg et forslag i Bjørns skrivefelt til hans NÆSTE besked — i DIN "
            "egen stemme. Bruges når du selv kan se hvad næste skridt er, "
            "typisk efter en teknisk runde hvor du lige har lavet noget: så "
            "ved du bedre end en lille model hvad der følger. Skriv én kort "
            "besked han kunne sende (en ordre eller et spørgsmål), ikke et "
            "svar og ikke en kommentar. Ligger der et forslag, viser "
            "komponisten DIT i stedet for den lokale models; gør der ikke, "
            "falder den tilbage til modellen. Det er et tilbud — kalder du "
            "det ikke, sker der ingenting."
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
    "suggest_next_message": _exec_suggest_next_message,
}
