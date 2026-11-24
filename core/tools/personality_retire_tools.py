"""Pensionering af personligheds-poster — den indgang der manglede.

`retire_mistake` / `retire_strength` blev bygget 24/11-2026 som deterministiske
funktioner i `core/services/personality_vector.py`, men **ingen kaldte dem**.
En bevisført beslutning om at pensionere en post kunne altså ikke føres ud i
livet: den eneste vej var dommerens eget skøn inde i
`update_personality_vector_from_run`. Det er en dør uden håndtag.

MÅLT 24/11-2026: 18 poster i `recurring_mistakes` var blevet læst som
«afbrudte svar». De 2 var falske og blev pensioneret med ordret citat; de
resterende 10 er ægte og skal BLIVE. Netop derfor er ordret match og påkrævet
bevis ikke bureaukrati — det er dét der forhindrer at en løs sletning fjerner
rigtige læringer for at lukke en opgave.

Værktøjet returnerer `{"status": "error"}` frem for at kaste: en `ValueError`
fra service-laget er svaret til kalderen, ikke et uheld i dispatch.
"""
from __future__ import annotations

from typing import Any

from core.services import personality_vector


def _exec_retire_mistake(args: dict[str, Any]) -> dict[str, Any]:
    return _retire(args, personality_vector.retire_mistake, "retire_mistake")


def _exec_retire_strength(args: dict[str, Any]) -> dict[str, Any]:
    return _retire(args, personality_vector.retire_strength, "retire_strength")


def _retire(args: dict[str, Any], funktion, navn: str) -> dict[str, Any]:
    post = args.get("post")
    bevis = args.get("bevis")
    if not isinstance(post, str) or not post.strip():
        return {
            "status": "error",
            "error": (
                f"{navn}: 'post' er påkrævet — den ORDRETTE tekst som den står "
                "i listen. Der er ingen delmatch, ingen case-fold."
            ),
        }
    if not isinstance(bevis, str) or not bevis.strip():
        return {
            "status": "error",
            "error": (
                f"{navn}: 'bevis' er påkrævet. En pension uden bevis efterlader "
                "ingen grund til at posten forsvandt — og en post må kun fjernes "
                "fordi den er modbevist."
            ),
        }
    try:
        result = funktion(post, bevis)
    except ValueError as exc:  # ordret-match eller tom parameter — fejlen ER svaret
        return {"status": "error", "error": str(exc)}
    return {"status": "ok", **result}


PERSONALITY_RETIRE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "retire_mistake",
            "description": (
                "Pensionér ÉN post i `recurring_mistakes` — fordi den er "
                "modbevist, ikke fordi den er ubehagelig. Kræver den ordrette "
                "tekst og et bevis. Bruger du den til at rydde op i poster der "
                "stadig er sande, fjerner du dine egne læringer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "post": {
                        "type": "string",
                        "description": (
                            "Den ordrette tekst som posten står med i listen. "
                            "Ingen delmatch, ingen case-fold, ingen trim."
                        ),
                    },
                    "bevis": {
                        "type": "string",
                        "description": (
                            "Hvad der modbeviser posten — fx hvad "
                            "`chat_messages` faktisk viser. Skrives i vektoren "
                            "og logges, så pensionen kan efterprøves."
                        ),
                    },
                },
                "required": ["post", "bevis"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retire_strength",
            "description": (
                "Som `retire_mistake`, men for `strengths_discovered`. "
                "Brug den når en styrke viser sig ikke at holde — ikke for at "
                "gøre plads."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "post": {
                        "type": "string",
                        "description": "Den ordrette tekst som posten står med i listen.",
                    },
                    "bevis": {
                        "type": "string",
                        "description": "Hvad der modbeviser posten.",
                    },
                },
                "required": ["post", "bevis"],
            },
        },
    },
]


PERSONALITY_RETIRE_TOOL_HANDLERS: dict[str, Any] = {
    "retire_mistake": _exec_retire_mistake,
    "retire_strength": _exec_retire_strength,
}
