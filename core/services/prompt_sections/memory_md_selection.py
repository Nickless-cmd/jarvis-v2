"""MEMORY.md selection by SECTION for the visible prompt (memory repair 2026-09-04, R2).

Before: MEMORY.md (67 KB, 93 sections) was split into bare lines without their
headings, scored by a hard-coded keyword list, and when nothing matched the
LAST FOUR LINES of the file were injected — 4 lines × 280 chars. The answer to
"hvor ligger pfsense-nøglen" was in the file; the prompt got two lines about
"inner voice, boredom and reflective noise".

Now: the existing `memory_search` index already chunks MEMORY.md per heading
and embeds each chunk. We ask it for the top sections for the user's message
and render them WITH their heading. Falls back to the old heuristic (caller's
responsibility) when the index yields nothing.
"""
from __future__ import annotations

import logging
import math
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_MIN_SCORE = 0.30
#: Under saa faa sektioner er en df-taelling stoej, og vaegtene gaar amok.
_IDF_MIN_SEKTIONER = 20
#: Vaegt for et ord der ikke findes i korpus. `log(N/1)` for N=928 er 6,83;
#: dette er et fast, konservativt loft saa én slaafejl ikke faar al vaegt.
_IDF_UKENDT = 5.0
_TERM_RE = re.compile(r"[0-9A-Za-zÆØÅæøå]+")
_STOP_TERMS = frozenset({
    "hvad", "hvor", "hvilken", "hvilket", "hvilke", "hvorfor", "hvornår",
    "hvordan", "blev", "var", "har", "havde", "det", "der", "den", "til",
    "fra", "med", "for", "som", "jeg", "mig", "du", "dig", "vores", "mine",
    "dine", "siger", "sagde", "besluttede", "aftalte", "lærte", "bruges", "om", "og",
})


def _render(section: str, text: str, *, max_chars: int) -> str:
    heading = " ".join((section or "").split()).strip()
    body = " ".join((text or "").split()).strip()
    line = f"§ {heading}: {body}" if heading else body
    if len(line) > max_chars:
        line = line[: max_chars - 1].rstrip() + "…"
    return line


def _terms(text: str) -> set[str]:
    terms: set[str] = set()
    for raw in _TERM_RE.findall(str(text or "").replace("-", " ")):
        term = raw.lower()
        if len(term) < 2 or term in _STOP_TERMS:
            continue
        terms.add(term)
        if len(term) > 4 and term.endswith("s"):
            terms.add(term[:-1])
    return terms


#: (mtime, stoerrelse) → (sektioner, vaegte). Vaegtene aendrer sig KUN naar
#: MEMORY.md goer, og en df-taelling over 928 sektioner tokeniserer hele filen.
#: Uden cachen kostede IDF +236 ms pr. tur (253 → 489 ms, maalt skiftevis).
_IDF_CACHE: dict[tuple[float, int], tuple[list[tuple[str, str]], dict[str, float]]] = {}


def _sektioner_og_vaegte(workspace_dir: Path) -> tuple[list[tuple[str, str]], dict[str, float]]:
    """Sektionerne og deres idf-vaegte, cachet paa filens (mtime, stoerrelse).

    `select_memory_md_sections` og `_lexical_candidates` behoever begge begge
    dele. Uden dette laeste og tokeniserede de 980 KB hver sin gang i samme
    kald.
    """
    sti = workspace_dir / "MEMORY.md"
    try:
        st = sti.stat()
    except OSError:  # ingen fil at noegle paa: parse direkte og cach intet
        return _memory_md_sections(workspace_dir), {}
    noegle = (st.st_mtime, st.st_size)
    truffet = _IDF_CACHE.get(noegle)
    if truffet is not None:
        return truffet
    sektioner = _memory_md_sections(workspace_dir)
    par = (sektioner, _idf_vaegte(sektioner))
    _IDF_CACHE.clear()  # kun den nyeste udgave er interessant
    _IDF_CACHE[noegle] = par
    return par


def _idf_vaegte(sektioner: list[tuple[str, str]]) -> dict[str, float]:
    """log(N/df) pr. term over sektionerne. Tom dict naar der er for lidt data.

    ## Hvorfor (maalt 5/10-2026)

    `_lexical_coverage` vaegter 0,65 af rangeringen i
    `select_memory_md_sections` — altsaa mere end selve soegningen. Den taeller
    BINAER ord-tilstedevaerelse, saa et almindeligt ord vejer som et sjaeldent.
    Maalt paa Bjoerns 928 sektioner: «ligger» staar i 130 af dem (idf 1,97),
    «pfsense» i 11 (idf 4,44) — og de taeller lige meget.

    Konsekvensen var BUNKER, ikke forkerte svar: «hvor ligger pfsense-noeglen»
    satte den rigtige sektion foerst, men NI sektioner stod lige paa 0,667, og
    148 paa 0,333. Hvem der vandt afgjorde de resterende 0,35 af vaegten.

    Effekten er maalt FOER den blev bygget, og den er lille: bunken paa ni
    bliver én (0,667 → 0,804), og de tre andre proever er uaendrede. IDF retter
    IKKE «hvordan udgiver jeg mobil-APK», som rammer «Genoptagelses-banneret»
    fordi «Udgiver:» staar som ETIKET i den udgivelses-note — det er aegte
    leksikalsk tvetydighed. Og den bryder ikke VESC's tre lige paa 1,0, for
    alle tre indeholder alle ordene; det kraever term-frekvens.
    """
    if len(sektioner) < _IDF_MIN_SEKTIONER:
        return {}
    df: dict[str, int] = {}
    for heading, text in sektioner:
        for term in _terms(f"{heading} {text}"):
            df[term] = df.get(term, 0) + 1
    n = float(len(sektioner))
    return {term: math.log(n / max(antal, 1)) for term, antal in df.items()}


def _lexical_coverage(
    query: str,
    section: str,
    text: str,
    *,
    vaegte: dict[str, float] | None = None,
) -> float:
    """Hvor meget af forespoergslen daekker denne sektion, 0..1.

    Uden `vaegte` er det den uvaegtede andel med loft 5 i naevneren — uaendret
    adfaerd, og den gaelder stadig dér hvor der ikke findes et korpus at veje
    imod (`_focused_excerpt` scorer enkelte saetninger).
    """
    q_terms = _terms(query)
    if not q_terms:
        return 0.0
    haystack = _terms(f"{section} {text}")
    ramt = q_terms & haystack
    if not vaegte:
        return min(1.0, len(ramt) / max(1, min(len(q_terms), 5)))
    # Naevneren er SUMMEN af forespoergslens vaegte, ikke et loft paa fem: et
    # sjaeldent ord der IKKE blev ramt skal traekke ned. Et ukendt ord (df 0)
    # faar derfor den hoejeste vaegt og kan aldrig rammes — det skalerer alle
    # kandidater ens ned og aendrer ikke RAEKKEFOELGEN, kun niveauet.
    i_alt = sum(vaegte.get(t, _IDF_UKENDT) for t in q_terms)
    if i_alt <= 0.0:
        return 0.0
    return min(1.0, sum(vaegte.get(t, _IDF_UKENDT) for t in ramt) / i_alt)


def _memory_md_sections(workspace_dir: Path) -> list[tuple[str, str]]:
    path = workspace_dir / "MEMORY.md"
    try:
        from core.services.secret_redaction import read_for_prompt

        raw = read_for_prompt(path)
    except Exception:
        raw = path.read_text(encoding="utf-8") if path.exists() else ""
    if not raw:
        return []

    sections: list[tuple[str, str]] = []
    heading = ""
    lines: list[str] = []

    def flush() -> None:
        nonlocal lines
        text = "\n".join(line.strip().lstrip("-* ").strip() for line in lines if line.strip())
        if text:
            sections.append((heading, text))
        lines = []

    for line in str(raw).splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            heading = stripped.lstrip("#").strip()
        else:
            lines.append(stripped)
    flush()
    return sections


def _focused_excerpt(msg: str, text: str, *, max_chars: int = 900) -> str:
    body = str(text or "").strip()
    if len(body) <= max_chars:
        return body
    parts: list[str] = []
    for line in body.splitlines():
        clean = " ".join(line.split())
        if clean:
            parts.append(clean)
    if len(parts) <= 1:
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", body) if p.strip()]
    scored = sorted(
        parts,
        key=lambda p: (_lexical_coverage(msg, "", p), -len(p)),
        reverse=True,
    )
    chosen: list[str] = []
    used = 0
    for part in scored:
        if _lexical_coverage(msg, "", part) <= 0.0:
            continue
        if used + len(part) > max_chars and chosen:
            break
        chosen.append(part)
        used += len(part)
        if used >= max_chars:
            break
    return " ".join(chosen).strip() or body[:max_chars].strip()


def _lexical_candidates(
    msg: str,
    workspace_dir: Path,
    *,
    limit: int,
    vaegte: dict[str, float] | None = None,
) -> list[dict[str, object]]:
    sektioner, egne_vaegte = _sektioner_og_vaegte(workspace_dir)
    if vaegte is None:
        vaegte = egne_vaegte
    out: list[dict[str, object]] = []
    for section, text in sektioner:
        coverage = _lexical_coverage(msg, section, text, vaegte=vaegte)
        if coverage <= 0.0:
            continue
        out.append({
            "section": section,
            "text": _focused_excerpt(msg, text),
            "score": min(1.0, 0.30 + 0.70 * coverage),
            "_lexical_fallback": True,
        })
    out.sort(key=lambda h: float(h.get("score") or 0.0), reverse=True)
    return out[:limit]


def select_memory_md_sections(
    user_message: str,
    *,
    workspace_dir: Path,
    max_sections: int = 3,
    max_chars: int = 1500,
    min_score: float = _MIN_SCORE,
) -> list[str]:
    """Return up to ``max_sections`` rendered MEMORY.md sections, most relevant first.

    - one line per section, ``§ <heading>: <text>``, deduplicated by heading
    - total length ≤ ``max_chars`` (each line ≤ max_chars // max_sections … but a
      single strong section may take up to max_chars // 2)
    - empty list when the message is too short or nothing scores ≥ ``min_score``
    """
    msg = " ".join((user_message or "").split()).strip()
    if len(msg) < 8:
        return []
    try:
        from core.services.memory_search import search_memory

        hits = search_memory(
            msg, limit=max(max_sections * 8, 24), sources=["MEMORY.md"],
            workspace_dir=workspace_dir,
        )
    except Exception as exc:
        logger.debug("memory_md_selection: search failed: %s", exc)
        hits = []

    # Vaegtene regnes ÉN gang og bruges baade til kandidaterne og til
    # rangeringen nedenfor — ellers ville de to halvdele af samme formel maale
    # paa hver sin skala.
    _vaegte = _sektioner_og_vaegte(workspace_dir)[1]
    hits = list(hits or []) + _lexical_candidates(
        msg, workspace_dir, limit=max(max_sections * 4, 12), vaegte=_vaegte,
    )

    per_line_cap = max(200, max_chars // 2)
    out: list[str] = []
    seen: set[str] = set()
    used = 0
    ranked_hits = sorted(
        hits,
        key=lambda h: (
            0.35 * float(h.get("score") or 0.0)
            + 0.65 * _lexical_coverage(
                msg, str(h.get("section") or ""), str(h.get("text") or ""), vaegte=_vaegte,
            )
        ),
        reverse=True,
    )
    for h in ranked_hits:
        if float(h.get("score") or 0.0) < min_score:
            continue
        section = str(h.get("section") or "")
        key = section.strip().lower()
        if key in seen:
            continue
        line = _render(section, str(h.get("text") or ""), max_chars=per_line_cap)
        if not line:
            continue
        if used + len(line) > max_chars and out:
            break
        seen.add(key)
        out.append(line)
        used += len(line)
        if len(out) >= max_sections:
            break
    return out
