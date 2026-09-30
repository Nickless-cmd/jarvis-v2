"""Værktøj: skift tænke-sprog uden genstart (killswitch, 30/9-2026).

Bjørn kan skrive kommandoen i chatten; Jarvis kalder dette værktøj, og skiftet
slår igennem på næste tur — ingen genstart. Se `core/services/think_language.py`
for målingen bag og hvorfor instruktionen er formuleret hårdt.

Strikt resultat-kontrakt: skrivningen LÆSES TILBAGE. Et «ok» er først sandt når
den læste værdi er den ønskede.
"""
from __future__ import annotations

from typing import Any

from core.services.think_language import KV_KEY, current, set_language


def _exec_think_language(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "status").strip().lower()

    if action in ("", "status"):
        return {
            "status": "ok",
            "language": current(),
            "kv_key": KV_KEY,
            "note": ("Tænke-sprog = %s. 'da' = dansk ræsonnement (standard), "
                     "'en' = engelsk ræsonnement, dansk svar til Bjørn." % current()),
        }

    if action not in ("da", "en"):
        return {
            "status": "error",
            "error": "action skal være 'status', 'da' eller 'en'",
            "language": current(),
        }

    before = current()
    set_language(action)
    # STRIKS BEKRÆFTELSE: læs tilbage — «ok» er bevis for at flaget stod fast.
    after = current()
    if after != action:
        return {
            "status": "error",
            "error": f"flaget stod ikke fast efter skriv (læst: {after!r})",
            "before": before,
        }

    return {
        "status": "ok",
        "before": before,
        "language": after,
        "confirmed": True,
        "note": (f"Tænke-sprog: {before} → {after}. Slår igennem på NÆSTE tur — ingen "
                 "genstart. Direktivet lægges i prompt-HALEN, så det cachede præfiks "
                 "er uberørt."),
    }


THINK_LANGUAGE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "think_language",
        "description": (
            "Læs eller skift hvilket sprog Jarvis' RÆSONNEMENT føres i — uden genstart. "
            "Målt 30/9-2026: engelsk tænkning brugte 1,87x færre tænke-tokens og 1,82x "
            "kortere tid end dansk (samme opgave, samme danske svar). Svaret til Bjørn "
            "forbliver dansk; kun den indre tænkning skifter. 'status' læser det aktive "
            "sprog, 'da'/'en' sætter det. Skiftet virker fra næste tur."
        ),
        "parameters": {"type": "object", "properties": {
            "action": {
                "type": "string",
                "enum": ["status", "da", "en"],
                "description": "'status' = læs aktivt sprog. 'da' = dansk tænkning (standard). 'en' = engelsk tænkning, dansk svar.",
            },
        }, "required": []},
    }},
]

THINK_LANGUAGE_TOOL_HANDLERS: dict[str, Any] = {
    "think_language": _exec_think_language,
}
