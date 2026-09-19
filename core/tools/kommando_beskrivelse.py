"""Jarvis' egen beskrivelse af en kommando — linjen i klienterne.

Claude Desktop viser IKKE en lille models etiket over et Bash-kald; Code-
fanen starter CLI'en med `CLAUDE_CODE_EMIT_TOOL_USE_SUMMARIES=false` og
tegner i stedet modellens eget `description`-felt fra kaldet (`zu` i deres
klient, læst 19/9-2026). Bjørn sagde ja til det samme her: Jarvis skriver
linjen selv, i det øjeblik han kalder — og den ligger i kaldet, så den
overlever en genindlæsning uden noget ekstra.

Feltets tekst er Claude Codes egen, ordret fra CLI-binæren (2.1.161), med
ét tillæg: den skal skrives på dansk, fordi det er Bjørn der læser den.

`brugbar_beskrivelse` er deres afvisningsregel (`zu`/`Bu`): en beskrivelse
over flere linjer, eller en der bare gentager kommandoen, bruges ikke.
"""
from __future__ import annotations

import re
from typing import Any, Final

__all__ = ["BESKRIVELSE_PARAM", "BLOEDT_PAAKRAEVET", "brugbar_beskrivelse"]

BESKRIVELSE_PARAM: Final[dict[str, Any]] = {
    "type": "string",
    "description": (
        "Clear, concise description of what this command does in active voice. "
        "Never use words like \"complex\" or \"risk\" in the description - just "
        "describe what it does. Write it in Danish: it is shown to the user as "
        "the line for this call.\n\n"
        "For simple commands (git, npm, standard CLI tools), keep it brief "
        "(5-10 words):\n"
        "- ls → \"Vis filer i mappen\"\n"
        "- git status → \"Vis arbejdstræets status\"\n"
        "- npm install → \"Installer pakkeafhængigheder\"\n\n"
        "For commands that are harder to parse at a glance (piped commands, "
        "obscure flags, etc.), add enough context to clarify what it does:\n"
        "- find . -name \"*.tmp\" -exec rm {} \\; → \"Find og slet alle .tmp-filer rekursivt\"\n"
        "- git reset --hard origin/main → \"Kassér lokale ændringer og match origin/main\"\n"
        "- curl -s url | jq '.data[]' → \"Hent JSON og træk data-elementerne ud\""
    ),
}

#: Felter skemaet KRÆVER, men kun så modellen udfylder dem. Valgfrit fik
#: DeepSeek til at springe feltet over: 0 af 108 bash-kald havde det, målt på
#: CT105 19/9-2026 efter udrulningen. Kontrakt-værnet (`tool_schema_contract`)
#: må derfor aldrig afvise et kald der mangler det — kommandoen er gyldig uden.
BLOEDT_PAAKRAEVET: Final[dict[str, frozenset[str]]] = {
    "bash": frozenset({"description"}),
    "operator_bash": frozenset({"description"}),
}

_MELLEMRUM = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _MELLEMRUM.sub(" ", s).strip().lower()


def brugbar_beskrivelse(beskrivelse: Any, kommando: Any = None) -> str:
    """Beskrivelsen hvis den kan stå som linjen, ellers `""`.

    Claude Desktops regel: tom, flere linjer, eller blot kommandoen igen →
    ikke brugbar. Så falder linjen tilbage på den mekaniske tekst.
    """
    if not isinstance(beskrivelse, str):
        return ""
    b = beskrivelse.strip()
    if not b or re.search(r"[\n\r]", b):
        return ""
    if isinstance(kommando, str) and _norm(b) == _norm(kommando):
        return ""
    return b
