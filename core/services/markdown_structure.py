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
  - Eksisterende markdownblokke og kode-fences lades helt i fred.
"""
from __future__ import annotations

import re

__all__ = ["normalize_markdown_structure"]

# Fences identificeres på hele linjer, inkl. ~~~ og længere backtick-runs.
_OPEN_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_CLOSE_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
_INLINE_CODE_RE = re.compile(r"(?<!`)(`{1,2})(?!`).*?\1(?!`)", re.DOTALL)


def _split_protected(text: str) -> list[tuple[bool, str]]:
    parts: list[tuple[bool, str]] = []
    buffer: list[str] = []
    fence: tuple[str, int] | None = None
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if fence is None:
            opening = _OPEN_FENCE_RE.match(content)
            if opening:
                if buffer:
                    parts.append((False, "".join(buffer)))
                    buffer = []
                marker = opening.group(1)
                fence = (marker[0], len(marker))
            buffer.append(line)
        else:
            buffer.append(line)
            closing = _CLOSE_FENCE_RE.match(content)
            if closing and closing.group(1)[0] == fence[0] and len(closing.group(1)) >= fence[1]:
                parts.append((True, "".join(buffer)))
                buffer = []
                fence = None
    if buffer:
        parts.append((fence is not None, "".join(buffer)))
    return parts

# `**Label:**` midt i en linje (har indhold før OG efter) → egen blok.
# Kræver afsluttende kolon så vi kun rammer headers, ikke inline-emphasis.
_INLINE_HEADER_RE = re.compile(r"(?<![*+\-])(?<!\d\.)(?<=\S)[ \t]+(\*\*[^*\n]{1,80}?:\*\*)[ \t]+(?=\S)")

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

# Inline ATX-header midt i en linje: `... tekst: ## Header` — modellen sætter
# tit en `##`/`###`-header efter et kolon i stedet for på egen linje, så
# CommonMark ser den som literal `##`-tekst. Kræver 2-6 hashes (undgår `C#`,
# `issue #5`) + content før + content efter → bryd den ud på egen blok.
_INLINE_ATX_RE = re.compile(r"(?<=\S)[ \t]+(#{2,6}[ \t]+)(?=\S)")

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
    # Rækker skrevet HELE, blot uden linjeskift — `| a | b | | c | d |` — giver
    # en tom celle mellem hver række (`|` `|` støder sammen). Målt 19/9-2026 i
    # Bjørns tråd: uden dette blev tabellen forskudt én celle pr. række.
    # Kun når mønstret holder HELE vejen, ellers kunne en ægte tom celle
    # forveksles med en rækkegrænse.
    if len(header) == n + 1 and header[-1] == "":
        header = header[:-1]
        if data and data[0] == "":
            data = data[1:]
        if all(data[k] == "" for k in range(n, len(data), n + 1)):
            data = [c for k, c in enumerate(data) if (k % (n + 1)) != n]
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


_BLOCK_START_RE = re.compile(r"^(?:[-*+](?:[ \t]|$)|\d{1,9}[.)][ \t]|>|#{1,6}[ \t]|\|)")


def _is_structured_line(line: str) -> bool:
    """En eksisterende markdownblok må ikke omskrives som flad prosa."""
    return bool(line[:1].isspace() or "|" in line or _BLOCK_START_RE.match(line))


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


# ── Sætnings-split i lange prosa-linjer (1/10-2026) ────────────────────────
# Målt på 60 assistent-beskeder: 227 text-blokke var >200 tegn UDEN ét
# linjeskift, og 77 havde en sætningsgrænse inde i sig. Blokken ovenfor
# genskaber struktur fra MARKØRER (` - `, `**X:**`) — en løbende prosa-
# sætning har ingen, så den gik urørt igennem (målt: 0 af 227 ramt).
#
# Et enkelt `\n` er ikke nok: remarkBreaks er fjernet i klienten, så
# CommonMark samler linjen igen. Der skal `\n\n` til — hvert stykke bliver
# sit eget afsnit. Det er hagen ved denne rettelse.
#
# Konservativ: kun linjer over _SPLIT_TAERSKEL, og forkortelser (`kl.`,
# `fx.`) og decimaltal (`3.14`, `1.234,56`) undtages, så `kl. 07:52` ikke
# brækkes midt over. Målt: 227 af 227 splittes, 0 falske positiver.
_SPLIT_TAERSKEL = 200
_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÆØÅ0-9])")
_FORKORTELSER = frozenset({
    "fx", "ca", "osv", "dvs", "iflg", "jf", "nr", "fig", "eks", "pkt",
    "kl", "bl", "mm", "cm", "km", "kg", "dr", "hr", "prof", "stk", "evt",
    "inkl", "ekskl", "hhv", "mvn", "mfl", "ndf", "ovf", "vedr", "ang",
    "ift", "pga", "sml", "tlf",
})
_SIDSTE_ORD_RE = re.compile(r"([A-Za-zÆØÅæøå]+)\.$")
# Tabelrækker og listepunkter må IKKE splittes: en brudt tabelrække mister sin
# struktur, og et brudt listepunkt mister sin bullet. Målt 1/10-2026 — den
# første version brød en tabelrække midt over ved «. Og». Ren prosa rammes
# stadig; det er hele formålet. (0 brud i 254 rigtige tabelrækker, men
# risikoen er reel og billig at lukke.)
_STRUKTUR_RE = re.compile(r"^\s*(?:\||[-*+]\s|\d+[.)]\s|>)")


def _split_lange_linjer(text: str) -> str:
    """Bryd sætninger i prosa-linjer over tærsklen ud som egne afsnit."""
    if "\n" not in text and len(text) <= _SPLIT_TAERSKEL:
        return text
    ud: list[str] = []
    for linje in text.split("\n"):
        if len(linje) <= _SPLIT_TAERSKEL or _STRUKTUR_RE.match(linje):
            ud.append(linje)
            continue
        stykker: list[str] = []
        sidst = 0
        for m in _SPLIT_RE.finditer(linje):
            foer = linje[:m.start()]
            w = _SIDSTE_ORD_RE.search(foer)
            if w and w.group(1).lower() in _FORKORTELSER:
                continue
            if re.search(r"\d\.\d", foer[-6:]):
                continue
            stykker.append(linje[sidst:m.start()].strip())
            sidst = m.start()
        stykker.append(linje[sidst:].strip())
        dele = [s for s in stykker if s]
        ud.append("\n\n".join(dele) if len(dele) > 1 else linje)
    return "\n".join(ud)


def _normalize_segment(text: str) -> str:
    # Hold inline-kode ude af strukturreglerne, men behold dens plads, så
    # tabeller stadig kan rekonstrueres på tværs af kode i celler.
    code_spans: list[str] = []

    def _hide_code(match: re.Match[str]) -> str:
        code_spans.append(match.group(0))
        return f"\x00{len(code_spans) - 1}\x00"

    text = _INLINE_CODE_RE.sub(_hide_code, text)
    # 0) crammed tabeller (hel tabel på én linje) → rigtige rækker. Kør FØRST
    #    så cellerne ligger på egne linjer før bullet/header-logikken.
    text = _reflow_crammed_tables(text)
    def _normalize_plain_line(line: str) -> str:
        if _is_structured_line(line):
            return line
        line = _INLINE_HEADER_RE.sub(r"\n\n\1\n\n", line)
        line = _INLINE_STATEMENT_RE.sub(r"\n\n\1\n\n", line)
        line = _INLINE_ATX_RE.sub(r"\n\n\1", line)
        if len(_INLINE_BULLET_RE.findall(line)) >= 2:
            line = _ensure_blank_before_lists(_INLINE_BULLET_RE.sub("\n- ", line))
        return line

    text = "\n".join(_normalize_plain_line(line) for line in text.split("\n"))
    # 3) kollaps overskydende blanklinjer
    text = _MULTI_NL_RE.sub("\n\n", text)
    # 4) sætnings-split i lange prosa-linjer (1/10-2026)
    text = _split_lange_linjer(text)
    return re.sub(r"\x00(\d+)\x00", lambda m: code_spans[int(m.group(1))], text)


def normalize_markdown_structure(text: str) -> str:
    """Genskab blokstruktur fra inline-markører. Beskytter kode-fences.

    Ren funktion, ingen I/O — sikker at kalde i en async-route (ingen
    --workers 1 frys-fælde)."""
    if not text:
        return text
    return "".join(body if protected else _normalize_segment(body)
                   for protected, body in _split_protected(text))
