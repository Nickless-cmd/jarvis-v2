"""`call_loaded_tool` — en transport, ikke en udfører.

## Hvorfor den findes

DeepSeeks præfiks er `[system][tools][beskeder]`, og cachen matcher fra
begyndelsen: **en ændring koster alt fra ændringspunktet og frem.** Værktøjs-
arrayet ligger før hele samtalen, så én ny definition dér kasserer historikken.

Målt tre gange, uafhængigt, 30/9-2026:

* mod DeepSeeks API direkte: **én ny definition bagerst i tools = 8.704 tokens**
  tabt — fire gange dyrere end to store beskeder, udelukkende på grund af
  positionen;
* i produktion ved katalog-dommen: værktøjerne skiftede 59.643 → 61.120 tegn,
  og hit faldt **88,0 % → 17,9 %**;
* i produktion igen: **+419 tegn definition → 62.672 miss-tokens**, hit fra
  97 % til 28,3 %.

`load_more_tools` returnerer i forvejen de fulde skemaer **i sit resultat** —
altså i beskederne, efter cache-grænsen, hvor de koster ~0. Det dyre er at
definitionerne *derudover* flettes ind i næste rundes værktøjsarray. Med en
generisk dispatcher der selv står fast i arrayet, bliver en hentning et
almindeligt værktøjskald i beskederne, og arrayet behøver aldrig ændre sig.

## Hvorfor den ikke udfører noget

**Hver eneste gate i systemet nøgles på navnet i kaldet** — `evaluate_commit_gates(name=…)`,
r2.5-gaten, veto-gaten, skema-kontrakten, godkendelser, dedup og telemetri.
Udførte denne dispatcher selv værktøjet, ville alle gates se
`call_loaded_tool` i stedet for `delete_file`, og så var den en universel
gate-omgåelse for alle ~370 værktøjer.

Derfor pakkes kaldet ud **øverst i `_prepare_call`, før nogen gate** — så
resten af kæden ser det ÆGTE navn og opfører sig præcis som hidtil.
`call_loaded_tool` har med vilje ingen executor: den findes kun som et navn
modellen kan sende, og den er væk igen før noget bliver kaldt.
"""
from __future__ import annotations

from typing import Any

#: Navnet modellen kalder. Skal stå i det faste værktøjsarray.
KALD_NAVN = "call_loaded_tool"

#: Definitionen. Den er konstant — det er hele pointen: arrayet må aldrig
#: ændre sig, så præfikset kan genbruges på tværs af ture og sessioner.
DEFINITION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": KALD_NAVN,
        "description": (
            "Kald et værktøj du har hentet med load_more_tools. "
            "Brug dette i stedet for at kalde det hentede værktøj direkte — "
            "værktøjslisten ændrer sig ikke, så samtalens cache holder. "
            "Argumenterne skal bruge præcis de feltnavne der stod i skemaet "
            "fra load_more_tools; gæt ikke."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "navn": {
                    "type": "string",
                    "description": "Værktøjets navn, præcis som load_more_tools returnerede det.",
                },
                "argumenter": {
                    "type": "object",
                    "description": "Værktøjets egne argumenter, som objekt.",
                },
            },
            "required": ["navn"],
        },
    },
}


def pak_ud(navn: str, argumenter: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Oversæt et dispatcher-kald til det ægte kald. Alt andet går uændret igennem.

    Returnerer ``(navn, argumenter)`` uændret når det ikke er et dispatcher-kald.
    Er det et dispatcher-kald uden brugbart navn, returneres dispatcher-navnet
    uændret — så det fejler HØJLYDT som et ukendt værktøj i stedet for at
    udføre ingenting i stilhed.
    """
    if navn != KALD_NAVN:
        return navn, argumenter
    indre = str((argumenter or {}).get("navn") or "").strip()
    if not indre or indre == KALD_NAVN:
        return navn, argumenter
    args = (argumenter or {}).get("argumenter")
    if not isinstance(args, dict):
        args = {}
    return indre, args
