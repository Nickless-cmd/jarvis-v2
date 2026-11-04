"""Hvilke værktøjer en opgaveprompt KRÆVER at agenten kalder.

Task-facaden giver en agent et fast værktøjssæt (executor: wt_bash, wt_write_file,
agent_note). Prompt-tekst må aldrig give mere end det — så en opgave der kræver
`restart_self` kan ikke løses af en executor, uanset formuleringen. Målt 4/11-2026:
fire dispatches blev accepteret, kørte, brændte tokens og svarede «værktøjet findes
ikke». Her genkendes kravet, så dispatch kan AFVISE i stedet for at acceptere.

Vagten kan kun afvise, aldrig tildele: den giver intet værktøj, og et krav den ikke
genkender (ingen backticks, andet ordvalg) slipper igennem som før. Den er med vilje
snæver — en executor der RETTER kode om et værktøj («ret `read_file` i …») må ikke
afvises, så kun et KALD-krav tæller: et kaldeverbum lige foran et backtick-navn.
Beslutningen er begrundet i docs/analysis/2026-11-04-agent-dispatch-vaerktoejer.md.
"""
from __future__ import annotations

import re
from collections.abc import Collection

# Kaldeverbum, evt. «værktøjet/tool/funktionen», så `navn`. Et negationsord lige foran
# verbet («ikke kalde», «do not call») gør det til et forbud, ikke et krav.
_KALD = re.compile(
    r"(?<!ikke\s)(?<!aldrig\s)(?<!not\s)(?<!never\s)(?<!n't\s)"
    r"\b(?:kald(?:e|er)?|kør(?:e|er)?|brug(?:e|er)?|udfør(?:e|er)?|"
    r"call|invoke|use|run|execute)\s+"
    r"(?:(?:værktøjet|vaerktoejet|tool|the\s+tool|funktionen)\s+)?"
    r"`([A-Za-z_][A-Za-z0-9_]*)`",
    re.IGNORECASE,
)


def ufuldstaendige_vaerktoejer(
    prompt: str, allowed_tools: Collection[str], known_tools: Collection[str],
) -> list[str]:
    """Kendte runtime-værktøjer prompten beder agenten KALDE, men som den ikke har.

    Rækkefølgen er første forekomst; hvert navn står én gang. Tom liste = intet at afvise.
    """
    har = set(allowed_tools)
    kendte = set(known_tools)
    fundet: list[str] = []
    for m in _KALD.finditer(prompt or ""):
        navn = m.group(1)
        if navn in kendte and navn not in har and navn not in fundet:
            fundet.append(navn)
    return fundet
