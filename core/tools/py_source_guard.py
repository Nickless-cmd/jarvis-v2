"""py_source_guard — vaern mod en tilbagevendende LLM-skrive-artefakt.

Nogle modeller (saerligt billigere) emitter docstring-triple-quotes OVER-escaped i deres
fil-content-tool-argument: en backslash foran hvert anfoerselstegn i stedet for et rent
triple-quote. Tool-laget skriver content verbatim (korrekt), saa artefakten lander i
.py-filen og den kan ikke parses/importeres. Det har braekket flere af Jarvis' egne
skrivninger.

guard_py_escapes er et minimalt, nul-risiko vaern: KUN for .py, og KUN naar indholdet
ikke allerede parser. En gyldig fil (inkl. en der lovligt indeholder de escaped tegn i
et string-literal) parser og roeres aldrig. Kun naar en normalisering af de over-escaped
triple-quotes faar en ellers-uparsbar fil til at parse, bruges den rettede.
"""
from __future__ import annotations

import ast

_ESC_DQ = '\\"\\"\\"'   # backslash-escaped triple double-quote (artefakten)
_ESC_SQ = "\\'\\'\\'"   # backslash-escaped triple single-quote


def guard_py_escapes(content: str, path: str) -> tuple[str, str | None]:
    """Returnér (evt. rettet content, advarsels-note eller None). Se modul-docstring."""
    if not path.endswith(".py"):
        return content, None
    try:
        ast.parse(content)
        return content, None            # parser allerede -> roer intet
    except SyntaxError:
        pass
    fixed = content.replace(_ESC_DQ, '"""').replace(_ESC_SQ, "'''")
    if fixed == content:
        return content, None
    try:
        ast.parse(fixed)
    except SyntaxError:
        return content, None            # rettelsen loeste det ikke -> original uaendret
    return fixed, "auto-rettede over-escaped triple-quotes (LLM-artefakt) — filen parser nu"
