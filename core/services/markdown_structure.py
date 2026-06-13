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

# En tabel-celle der KUN er bindestreger/koloner/whitespace = separator-celle
# (rækken `| --- | --- |` der adskiller header fra data i en GFM-tabel).
_SEP_CELL_RE = re.compile(r"^\s*:?-{1,}:?\s*$")


def _split_cells(region: str) -> list[str]:
    """Split en `|`-afgrænset region i celler; drop ydre tomme (før første /
    efter sidste pipe)."""
    parts = region.split("|")
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return parts


def _reflow_line_table(line: str) -> str | None:
    """Hvis `line` indeholder en HEL tabel mast sammen på én linje
    (`| h1 | h2 | --- | --- | a | b | c | d |`), genskab den som rigtige
    rækker. Returnér None hvis linjen ikke er en crammed tabel."""
    first = line.find("|")
    last = line.rfind("|")
    if first < 0 or last <= first:
        return None
    prefix, region, suffix = line[:first], line[first:last + 1], line[last + 1:]
    cells = _split_cells(region)
    if len(cells) < 4:
        return None
    # Find første run af >=2 sammenhængende separator-celler = kolonne-antal.
    sep_start, sep_len = -1, 0
    i = 0
    while i < len(cells):
        if _SEP_CELL_RE.match(cells[i]):
            j = i
            while j < len(cells) and _SEP_CELL_RE.match(cells[j]):
                j += 1
            if j - i >= 2:
                sep_start, sep_len = i, j - i
                break
            i = j
        else:
            i += 1
    # Kræv header-celler FØR separatoren på SAMME linje → det er en crammed
    # tabel. En korrekt formateret tabel har separatoren alene på sin linje
    # (sep_start == 0) og røres ikke.
    if sep_start < 1:
        return None
    n = sep_len
    header = [c.strip() for c in cells[:sep_start]]
    data = [c.strip() for c in cells[sep_start + sep_len:]]
    rows = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * n) + " |"]
    for k in range(0, len(data), n):
        rows.append("| " + " | ".join(data[k:k + n]) + " |")
    table = "\n".join(rows)
    out: list[str] = []
    if prefix.strip():
        out.append(prefix.rstrip())
    out.append("")          # blanklinje før tabel (GFM kræver det)
    out.append(table)
    out.append("")          # blanklinje efter
    if suffix.strip():
        out.append(suffix.lstrip())
    return "\n".join(out)


def _reflow_crammed_tables(text: str) -> str:
    """Genskab tabeller hvis hele rækken er mast sammen på én linje."""
    if "|" not in text:
        return text
    out_lines: list[str] = []
    for line in text.split("\n"):
        reflowed = _reflow_line_table(line) if line.count("|") >= 4 else None
        out_lines.append(reflowed if reflowed is not None else line)
    return "\n".join(out_lines)


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
    # 0) crammed tabeller (hel tabel på én linje) → rigtige rækker. Kør FØRST
    #    så cellerne ligger på egne linjer før bullet/header-logikken.
    text = _reflow_crammed_tables(text)
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
