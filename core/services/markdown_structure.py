"""Rekonstruér markdown-blokstruktur fra inline-markører.

Jarvis (deepseek-modellen) emitterer inkonsistent newlines: ca. halvdelen af
hans svar skriver alt inline med ` - `-bullets og `**X:**`-headers men UDEN
newlines. CommonMark merger så det hele til ét løbende afsnit ("kastet ind").
Hverken client-rendering (remark-breaks/enforceStructure) kan redde tekst der
bogstaveligt er én linje — der er ingen `\\n` at bryde på.

Denne funktion kører server-side på den endelige assistent-tekst FØR den gemmes
og sendes til kanaler (jarvis-desk, webchat, Discord). Den genskaber blok-
struktur fra de strukturelle markører Jarvis faktisk bruger:

  - ` - item - item - item`  → en rigtig punktliste (én pr. linje)
  - `**Header:**` midt i en linje → headeren på egen linje med blanklinjer om

Designprincipper:
  - Idempotent: tekst der allerede har newlines/struktur ændres ikke.
  - Konservativ: en enkelt ` - ` (tankestreg) røres ikke; kun lister på 2+.
  - Kode-fences (```...```) lades helt i fred.
"""
from __future__ import annotations

import re

__all__ = ["normalize_markdown_structure"]

# ```...``` blokke beskyttes mod al transformation.
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)

# `**Label:**` midt i en linje (har indhold før OG efter) → egen blok.
# Kræver afsluttende kolon så vi kun rammer headers, ikke inline-emphasis.
_INLINE_HEADER_RE = re.compile(r"(?<=\S)[ \t]+(\*\*[^*\n]{1,80}?:\*\*)[ \t]+(?=\S)")

# Flerords-bold der ender på sætningstegn (`**Det er chat + permissions.**`) =
# en selvstændig udsagn-sætning → eget afsnit. Lookahead `(?=[^*\n]*\s)` kræver
# mindst ét mellemrum (flerords) så kort inline-emphasis (`**vigtigt!**`) IKKE
# brækkes ud midt i en sætning.
_INLINE_STATEMENT_RE = re.compile(
    r"(?<=\S)[ \t]+(\*\*(?=[^*\n]*\s)[^*\n]{1,160}?[.!?]\*\*)[ \t]+(?=\S)"
)

# ` - ` (mellemrum, bindestreg, mellemrum) midt i en linje = bullet-markør.
# Lookbehind \S sikrer at line-start-bullets (`\n- `) ikke matches igen.
_INLINE_BULLET_RE = re.compile(r"(?<=\S)[ \t]-[ \t](?=\S)")

_MULTI_NL_RE = re.compile(r"\n{3,}")
_ORDERED_RE = re.compile(r"\d+\.[ \t]")


def _is_bullet_line(line: str) -> bool:
    s = line.lstrip()
    return s.startswith("- ") or bool(_ORDERED_RE.match(s))


def _ensure_blank_before_lists(text: str) -> str:
    """Indsæt en blank linje før første bullet i en liste der følger prosa, så
    CommonMark starter listen i stedet for at klistre den til afsnittet."""
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        if _is_bullet_line(line) and out:
            prev = out[-1]
            if prev.strip() and not _is_bullet_line(prev):
                out.append("")
        out.append(line)
    return "\n".join(out)


def _normalize_segment(text: str) -> str:
    # 1) inline `**Header:**` → egen blok
    text = _INLINE_HEADER_RE.sub(r"\n\n\1\n\n", text)
    # 1b) inline flerords-udsagn `**...sætning.**` → eget afsnit
    text = _INLINE_STATEMENT_RE.sub(r"\n\n\1\n\n", text)
    # 2) inline ` - ` bullets — kun når det er en ægte liste (2+ markører)
    if len(_INLINE_BULLET_RE.findall(text)) >= 2:
        text = _INLINE_BULLET_RE.sub("\n- ", text)
        text = _ensure_blank_before_lists(text)
    # 3) kollaps overskydende blanklinjer
    text = _MULTI_NL_RE.sub("\n\n", text)
    return text


def normalize_markdown_structure(text: str) -> str:
    """Genskab blokstruktur fra inline-markører. Beskytter kode-fences.

    Ren funktion, ingen I/O — sikker at kalde i en async-route (ingen
    --workers 1 frys-fælde)."""
    if not text:
        return text
    parts: list[str] = []
    last = 0
    for m in _FENCE_RE.finditer(text):
        if m.start() > last:
            parts.append(_normalize_segment(text[last:m.start()]))
        parts.append(m.group(0))
        last = m.end()
    if last < len(text):
        parts.append(_normalize_segment(text[last:]))
    return "".join(parts)
