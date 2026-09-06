"""Fuzzy tekst-match til fil-redigering — porteret fra jarvis-code.

`operator_edit_file` var en REN gennemstikning til broen, som laver eksakt
strengmatch. Maalt paa produktionsdata: **56 % fejlrate paa edit, 44 % paa
write** — mod `operator_bash` paa 1,2 %. En kode-agent der kan laese og koere
kommandoer paa Bjoerns maskine, men fejler over halvdelen af sine redigeringer,
er ikke brugbar.

Aarsagen er ikke broen. Det er at eksakt match fejler saa snart indrykning eller
mellemrum afviger med ét tegn — og en model der gengiver en kodeblok rammer
sjaeldent whitespace praecist.

jarvis-code loeste det med en fire-trins stige, og den er ~150 linjer REN
stdlib. Den flyttes hertil ordret, saa matchet loeses SERVER-side mod filens
faktiske indhold og broen faar en faerdig, eksakt erstatning. Broen forbliver
dum; intelligensen ligger hvor runtimen er.

Stigen (foerste der rammer vinder):
  1. eksakt delstreng
  2. whitespace-normaliseret (alt whitespace kollapset paa BEGGE sider)
  3. indrykningsufoelsom (sammenlign strippede linjer, genanvend det FUNDNE
     blocks egen indrykning paa erstatningen)
  4. difflib over linje-vinduer, taerskel 0,85 — og under den fejler den HOEJT.
     Tekst der genuint ikke findes skal give en fejl, ikke en forkert redigering.
"""
from __future__ import annotations

import re

_FUZZY_DIFFLIB_THRESHOLD = 0.85


def _exact_find(content: str, old_text: str) -> list[tuple[int, int]]:
    """All exact-match spans of old_text in content. [] if none."""
    if not old_text:
        return []
    spans = []
    start = 0
    while True:
        i = content.find(old_text, start)
        if i == -1:
            break
        spans.append((i, i + len(old_text)))
        start = i + 1
    return spans


def _whitespace_fuzzy_find(content: str, old_text: str) -> list[tuple[int, int]]:
    """Match old_text against content with ALL whitespace (on BOTH sides)
    removed before comparing — catches an old_text that differs from the
    file only in internal spacing, in either direction (fewer OR extra
    spaces/tabs than the file actually has, whitespace present on one side
    but not the other). Scoped to SINGLE-LINE old_text by the caller — a
    multi-line indentation drift is strategy 3 (indent-insensitive), kept
    distinct so the two strategies are actually distinguishable rather than
    both silently matching the same indented block."""
    old_no_ws = re.sub(r"\s+", "", old_text)
    if not old_no_ws:
        return []
    content_chars: list[str] = []
    span_map: list[int] = []   # per non-whitespace char kept: original index
    for i, c in enumerate(content):
        if not c.isspace():
            content_chars.append(c)
            span_map.append(i)
    joined = "".join(content_chars)
    results: list[tuple[int, int]] = []
    search_from = 0
    while True:
        idx = joined.find(old_no_ws, search_from)
        if idx == -1:
            break
        end_idx = idx + len(old_no_ws) - 1
        orig_start = span_map[idx]
        orig_end = span_map[end_idx] + 1
        results.append((orig_start, orig_end))
        search_from = idx + 1
    return results


def _indent_insensitive_find(content: str, old_text: str) -> list[tuple[int, int, str]]:
    """Match old_text LINE-BY-LINE ignoring leading indent — each content
    line's stripped form must equal old_text's corresponding stripped line.
    Returns (start, end, matched_indent) so the caller can re-apply the
    FOUND block's own indent to new_text."""
    old_lines = old_text.splitlines()
    if not old_lines:
        return []
    content_lines = content.splitlines(keepends=True)
    n = len(old_lines)
    results = []
    offset = 0
    line_offsets = []
    for ln in content_lines:
        line_offsets.append(offset)
        offset += len(ln)
    for i in range(len(content_lines) - n + 1):
        window = content_lines[i:i + n]
        if all(w.rstrip("\n").strip() == o.strip() for w, o in zip(window, old_lines)):
            start = line_offsets[i]
            end = line_offsets[i + n - 1] + len(window[-1])
            # matched block's own leading indent, taken from its first line.
            first = window[0]
            indent = first[:len(first) - len(first.lstrip(" \t"))]
            results.append((start, end, indent))
    return results


def _reapply_indent(new_text: str, indent: str) -> str:
    """Re-apply `indent` as a leading prefix on every non-blank line of
    new_text (mirrors the indent-insensitive match's found block's own
    indent). Relative indentation already present in new_text (nested
    blocks) is preserved — `indent` is prepended, not a replacement."""
    if not indent:
        return new_text
    lines = new_text.splitlines(keepends=True)
    out = []
    for ln in lines:
        if ln.strip():
            out.append(indent + ln)
        else:
            out.append(ln)
    return "".join(out)


def _difflib_fuzzy_find(content: str, old_text: str,
                        threshold: float = _FUZZY_DIFFLIB_THRESHOLD) -> tuple[int, int, float] | None:
    """Best-matching line-window in content vs. old_text, by
    difflib.SequenceMatcher ratio. Returns (start, end, ratio) for the BEST
    window if it clears `threshold`, else None (genuinely-absent text must
    fail loudly, not silently apply a wrong edit)."""
    import difflib
    old_lines = old_text.splitlines()
    n = len(old_lines)
    if n == 0:
        return None
    content_lines = content.splitlines(keepends=True)
    if len(content_lines) < n:
        return None
    offset = 0
    line_offsets = []
    for ln in content_lines:
        line_offsets.append(offset)
        offset += len(ln)
    best: tuple[int, int, float] | None = None
    for i in range(len(content_lines) - n + 1):
        window = content_lines[i:i + n]
        window_text = "".join(window)
        ratio = difflib.SequenceMatcher(None, window_text, old_text).ratio()
        if best is None or ratio > best[2]:
            start = line_offsets[i]
            end = line_offsets[i + n - 1] + len(window[-1])
            best = (start, end, ratio)
    if best is not None and best[2] >= threshold:
        return best
    return None


def resolve_edit(content: str, old_text: str, new_text: str,
                 replace_all: bool = False) -> tuple[str, int, str]:
    """Loes et redigerings-oenske mod filens FAKTISKE indhold.

    Returnerer ``(nyt_indhold, antal_erstatninger, strategi)``.

    Kaster ``ValueError`` naar teksten ikke findes, eller naar den findes flere
    gange uden ``replace_all`` — begge dele skal fejle hoejt. En redigering der
    rammer et andet sted end brugeren mente er vaerre end en der ikke sker.
    """
    if not old_text:
        raise ValueError("old_string er tom")

    spans = _exact_find(content, old_text)
    strategi, erstatning = "exact", new_text
    if not spans:
        spans = _whitespace_fuzzy_find(content, old_text)
        strategi = "whitespace"
        # FEJL FUNDET UNDER PORTEN (5/9-2026). Strategi 2 kollapser ALT
        # whitespace — ogsaa indrykning — og indsatte saa kalderens egen. Paa et
        # flerlinje-match braekkede den koden i stilhed:
        #     foer  '        return 1'   (8 mellemrum)
        #     efter '    return 2'       (4 — forkert blok)
        # Kommentaren i jarvis-codes egen strategi 2 siger at flerlinje-drift
        # hoerer til strategi 3, men 2 rammer foerst. En stille forkert
        # redigering er vaerre end en der fejler, saa flerlinje-traef genanvender
        # nu det FUNDNE blocks indrykning — praecis som strategi 3 goer.
        if spans and "\n" in old_text:
            # Indrykningen skal findes BAGLAENS til linjestart: matchet begynder
            # ved det foerste ikke-blanke tegn (`def`), ikke ved de mellemrum der
            # staar foran det. At lstrip'e selve traeffet giver derfor altid tom
            # indrykning — den fejl kostede en runde.
            linjestart = content.rfind("\n", 0, spans[0][0]) + 1
            indryk = content[linjestart:spans[0][0]]
            if indryk and not indryk.strip():
                # Spaendet UDVIDES tilbage til linjestart, saa den gamle
                # indrykning bliver erstattet frem for at faa den nye lagt
                # ovenpaa. `_reapply_indent` praefikser HVER linje, og uden
                # udvidelsen ville foerste linje faa indrykningen to gange.
                spans = [(linjestart, spans[0][1])] + list(spans[1:])
                erstatning = _reapply_indent(new_text, indryk)
                strategi = "whitespace+indent"
    if not spans:
        traf = _indent_insensitive_find(content, old_text)
        if traf:
            # Genanvend det fundne blocks egen indrykning, ellers lander
            # erstatningen med kildens indrykning i en anden kontekst.
            spans = [(s, e) for s, e, _ in traf]
            erstatning = _reapply_indent(new_text, traf[0][2])
            strategi = "indent"
    if not spans:
        bedste = _difflib_fuzzy_find(content, old_text)
        if bedste:
            spans = [(bedste[0], bedste[1])]
            strategi = f"difflib:{bedste[2]:.2f}"
    if not spans:
        raise ValueError("old_string blev ikke fundet i filen")
    if len(spans) > 1 and not replace_all:
        raise ValueError(
            f"old_string findes {len(spans)} gange — brug replace_all "
            f"eller giv mere kontekst")

    ud, sidst = [], 0
    for s, e in (spans if replace_all else spans[:1]):
        ud.append(content[sidst:s])
        ud.append(erstatning)
        sidst = e
    ud.append(content[sidst:])
    return "".join(ud), len(spans if replace_all else spans[:1]), strategi
