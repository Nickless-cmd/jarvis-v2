"""Det Jarvis har LÆRT om Bjørn — læsesiden (lærings-sløjfe 2026-09-04, blok A).

Målt 4/9: `end_of_run_memory_consolidation` skrev 43 præferencer til USER.md på
30 dage (146 i alt siden foråret) i sektionen `## Durable Preferences`, der
starter på linje 70 af 202. Prompten læste enten de første 40 linjer eller —
efter Kerne-mekanismen samme dag — KUN `## Kerne`. Så intet af det han lærte om
Bjørn nåede nogensinde hans egen prompt. Han kunne finde det med `search_memory`
hvis han søgte på det rigtige ord. Det er ikke en mekanisme.

Todeling nu:

* `## Kerne` — altid i prompten, højst ~25 linjer, kurateret (se
  `core.services.kerne_curator`).
* `## Lært` — alt det konsolideringen skriver, med dato og kilde pr. linje.
  Relevans-udvalgt pr. tur ind i `[HUKOMMELSE]`, præcis som MEMORY.md-
  sektionerne siden R2.

En linje ser sådan ud::

    - Bjørn vil have korte mellemregninger mellem tool-kald (2026-09-02, sagt eksplicit)

Suffikset er valgfrit; linjer uden det læses stadig. `note_selected` tæller hvor
tit en linje faktisk blev valgt ind — det er kuratorens signal for hvad der er
blevet så fast at det hører hjemme i Kerne.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

LEARNED_HEADINGS = frozenset({"lært", "laert", "learned", "lært om bjørn"})
CORE_HEADINGS = frozenset({"kerne", "core", "kerne (altid i prompten)"})

_MIN_COVERAGE = 0.34
_MAX_LINES = 3
_MAX_CHARS = 700
_SELECTION_COUNTER_KEY = "learned_about_user.selection_counts"

_TERM_RE = re.compile(r"[0-9A-Za-zÆØÅæøå]+")
_STOP_TERMS = frozenset({
    "hvad", "hvor", "hvilken", "hvilket", "hvilke", "hvorfor", "hvornår",
    "hvordan", "blev", "var", "har", "havde", "det", "der", "den", "til",
    "fra", "med", "for", "som", "jeg", "mig", "du", "dig", "vores", "mine",
    "dine", "siger", "sagde", "om", "og", "kan", "skal", "ikke", "eller",
    "bjørn", "bjoern", "jarvis", "the", "and", "you", "your", "that", "this",
})
# "(2026-09-02, sagt eksplicit)" i enden af en linje.
_SUFFIX_RE = re.compile(r"\s*\((\d{4}-\d{2}-\d{2})(?:,\s*([^)]{0,40}))?\)\s*$")


def _terms(text: str) -> set[str]:
    out: set[str] = set()
    for raw in _TERM_RE.findall(str(text or "").replace("-", " ")):
        term = raw.lower()
        if len(term) < 3 or term in _STOP_TERMS:
            continue
        out.add(term)
        if len(term) > 4 and term.endswith("s"):
            out.add(term[:-1])
    return out


def lexical_coverage(query: str, text: str) -> float:
    """Andel af beskedens betydningsbærende ord der findes i linjen (0-1)."""
    q = _terms(query)
    if not q:
        return 0.0
    return min(1.0, len(q & _terms(text)) / max(1, min(len(q), 5)))


def _read_user_md(workspace_dir: Path) -> str:
    path = Path(workspace_dir) / "USER.md"
    try:
        from core.services.prompt_sections.workspace_files import (
            _resolve_with_shared_fallback,
        )
        path = _resolve_with_shared_fallback(path)
    except Exception:
        pass
    try:
        from core.services.secret_redaction import read_for_prompt
        return read_for_prompt(path) or ""
    except Exception:
        try:
            return path.read_text(encoding="utf-8") if path.exists() else ""
        except Exception:
            return ""


def section_body(text: str, headings: frozenset[str]) -> str:
    """Brødteksten under den første overskrift i ``headings`` — "" hvis ingen."""
    out: list[str] = []
    inside = False
    level = 0
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            hashes = len(line) - len(line.lstrip("#"))
            title = line.lstrip("#").strip().lower()
            if inside and hashes <= level:
                break
            if title in headings:
                inside, level = True, hashes
                continue
        if inside:
            out.append(raw)
    return "\n".join(out).strip()


def parse_line(raw: str) -> dict[str, str]:
    """Én Lært-linje → {text, date, source}. Suffikset er valgfrit."""
    body = " ".join(str(raw or "").split()).strip().lstrip("-*").strip()
    m = _SUFFIX_RE.search(body)
    date = source = ""
    if m:
        date = m.group(1) or ""
        source = " ".join((m.group(2) or "").split())
        body = body[: m.start()].rstrip()
    return {"text": body, "date": date, "source": source}


def learned_lines(workspace_dir: Path) -> list[dict[str, str]]:
    """Alle linjer i `## Lært`, nyeste sidst (filens rækkefølge)."""
    body = section_body(_read_user_md(workspace_dir), LEARNED_HEADINGS)
    out: list[dict[str, str]] = []
    for raw in body.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        parsed = parse_line(raw)
        if len(parsed["text"]) >= 8:
            out.append(parsed)
    return out


def core_lines(workspace_dir: Path) -> list[str]:
    """Linjerne i `## Kerne` — dem der altid er i prompten."""
    body = section_body(_read_user_md(workspace_dir), CORE_HEADINGS)
    return [
        " ".join(raw.split()).strip()
        for raw in body.splitlines()
        if raw.strip() and not raw.strip().startswith("#")
    ]


def note_selected(texts: list[str]) -> None:
    """Tæl at disse linjer blev valgt ind. Kuratorens signal. Self-safe."""
    if not texts:
        return
    try:
        from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value
        counts = dict(get_runtime_state_value(_SELECTION_COUNTER_KEY, {}) or {})
        for text in texts:
            key = " ".join(str(text or "").split()).lower()[:120]
            if key:
                counts[key] = int(counts.get(key, 0)) + 1
        # Loft: hold tælleren lille (de 200 mest brugte).
        if len(counts) > 200:
            counts = dict(sorted(counts.items(), key=lambda kv: -int(kv[1]))[:200])
        set_runtime_state_value(_SELECTION_COUNTER_KEY, counts)
    except Exception as exc:
        logger.debug("learned_about_user: note_selected failed: %s", exc)


def selection_counts() -> dict[str, int]:
    try:
        from core.runtime.db_core import get_runtime_state_value
        return {
            str(k): int(v)
            for k, v in dict(get_runtime_state_value(_SELECTION_COUNTER_KEY, {}) or {}).items()
        }
    except Exception:
        return {}


def select_learned_lines(
    user_message: str,
    *,
    workspace_dir: Path,
    max_lines: int = _MAX_LINES,
    max_chars: int = _MAX_CHARS,
    min_coverage: float = _MIN_COVERAGE,
    count_selection: bool = True,
) -> list[dict[str, str]]:
    """De mest relevante `## Lært`-linjer for det Bjørn lige skrev.

    Tom liste når beskeden er for kort eller intet dækker ``min_coverage``.
    Nyere linjer vinder ved lige dækning (rækkefølgen i filen er kronologisk).
    """
    msg = " ".join(str(user_message or "").split()).strip()
    if len(msg) < 8:
        return []
    try:
        rows = learned_lines(workspace_dir)
    except Exception as exc:
        logger.debug("learned_about_user: read failed: %s", exc)
        return []
    scored: list[tuple[float, int, dict[str, str]]] = []
    for index, row in enumerate(rows):
        coverage = lexical_coverage(msg, row["text"])
        if coverage >= min_coverage:
            scored.append((coverage, index, row))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    out: list[dict[str, str]] = []
    used = 0
    seen: set[str] = set()
    for _cov, _idx, row in scored:
        key = row["text"].lower()[:80]
        if key in seen:
            continue
        if used + len(row["text"]) > max_chars and out:
            break
        seen.add(key)
        out.append(row)
        used += len(row["text"])
        if len(out) >= max_lines:
            break
    if out and count_selection:
        note_selected([row["text"] for row in out])
    return out


def build_learned_section(
    user_message: str,
    *,
    workspace_dir: Path,
    max_lines: int = _MAX_LINES,
    max_chars: int = _MAX_CHARS,
) -> str:
    """Prompt-linjen til `[HUKOMMELSE]` — "" når intet er relevant."""
    rows = select_learned_lines(
        user_message, workspace_dir=workspace_dir,
        max_lines=max_lines, max_chars=max_chars,
    )
    if not rows:
        return ""
    parts = []
    for row in rows:
        suffix = f" ({row['date']})" if row["date"] else ""
        parts.append(f"• {row['text']}{suffix}")
    return "Lært om Bjørn (relevant for det han skriver nu):\n" + "\n".join(parts)
