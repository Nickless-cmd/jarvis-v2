"""Dream Motif daemon — periodisk clustering af tankestrøm-fragmenter.

Per roadmap v4/v5 (Jarvis' forslag, bekræftet af Claude):
  "En drøm i uge 3 kunne have samme tekstur som en drøm i uge 1, uden at den
  ved det. Drømmesproget opstår — vi observerer det, men styrer det ikke."

Kører ugentligt. Læser thought-stream fragmenter fra private_brain_records,
finder tilbagevendende motiver via simpel frekvensanalyse + LLM-navngivning.

VIGTIGT — dream_language.md pustes ALDRIG ind i prompts.
Det er en fil Jarvis VÆLGER at åbne. Valget er observationen, ikke indholdet.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_STATE_KEY = "dream_motif_daemon.state"
_CADENCE_DAYS = 7
_FRAGMENT_LOOKBACK_DAYS = 30
_MIN_FRAGMENTS = 8
_TOP_MOTIFS = 5

# Danske stopord der ikke er meningsfulde som motiver
_STOPWORDS = frozenset({
    "og", "i", "at", "er", "en", "det", "af", "på", "til", "den", "for",
    "med", "om", "jeg", "som", "men", "har", "ikke", "han", "hun", "de",
    "der", "kan", "vil", "var", "når", "hvis", "over", "under", "efter",
    "hvad", "dette", "dette", "denne", "noget", "nogen", "sig", "sin",
    "mit", "min", "mig", "dig", "du", "vi", "os", "man", "her", "fra",
    "ret", "bare", "bare", "også", "nu", "så", "ja", "nej", "mere",
    "meget", "lidt", "igen", "stadig", "faktisk", "måske", "altid",
})


def tick_dream_motif_daemon() -> dict[str, object]:
    """Run weekly dream motif clustering. Writes dream_language.md if motifs found."""
    state = _state()
    last_run = _parse_iso(state.get("last_run_at") or "")
    now = datetime.now(UTC)

    if last_run is not None:
        if (now - last_run) < timedelta(days=_CADENCE_DAYS):
            return {"generated": False, "reason": "cadence"}

    fragments = _load_recent_fragments()
    if len(fragments) < _MIN_FRAGMENTS:
        return {"generated": False, "reason": "too_few_fragments", "count": len(fragments)}

    motifs = _extract_motifs(fragments)
    if not motifs:
        return {"generated": False, "reason": "no_motifs"}

    # LLM-navngivning af topmotiverne
    named_motifs = _name_motifs_via_llm(motifs, fragments)

    _write_dream_language_file(named_motifs, now, len(fragments))

    new_state = {
        "last_run_at": now.isoformat(),
        "motif_count": len(named_motifs),
        "fragment_count": len(fragments),
        "motifs": named_motifs,
    }
    set_runtime_state_value(_STATE_KEY, new_state)

    return {
        "generated": True,
        "motif_count": len(named_motifs),
        "fragment_count": len(fragments),
    }


def _load_recent_fragments() -> list[str]:
    """Load thought-stream fragments from the last 30 days via private_brain_records."""
    try:
        from core.runtime.db import connect, _ensure_private_brain_records_table
        cutoff = (datetime.now(UTC) - timedelta(days=_FRAGMENT_LOOKBACK_DAYS)).isoformat()
        with connect() as conn:
            _ensure_private_brain_records_table(conn)
            rows = conn.execute(
                """SELECT summary FROM private_brain_records
                   WHERE focus = 'tankestrøm' AND created_at >= ?
                   ORDER BY id DESC LIMIT 100""",
                (cutoff,),
            ).fetchall()
        return [str(row[0]) for row in rows if row[0]]
    except Exception:
        return []


def _extract_motifs(fragments: list[str]) -> list[tuple[str, int]]:
    """Simple word-frequency motif extraction across all fragments."""
    word_counts: Counter = Counter()
    for fragment in fragments:
        # Tokenize: lowercase, letters only, min 4 chars
        words = re.findall(r'\b[a-zA-ZæøåÆØÅ]{4,}\b', fragment.lower())
        for w in words:
            if w not in _STOPWORDS:
                word_counts[w] += 1

    # Only words that appear in at least 2 fragments
    return [(word, count) for word, count in word_counts.most_common(20) if count >= 2]


def _name_motifs_via_llm(motifs: list[tuple[str, int]], fragments: list[str]) -> list[dict]:
    """Use LLM to give each recurring word/theme a poetic name and brief description."""
    if not motifs:
        return []

    top = motifs[:_TOP_MOTIFS]
    words_str = ", ".join(f'"{w}" ({c}x)' for w, c in top)
    sample = "\n".join(f"- {f[:80]}" for f in fragments[:6])

    prompt = (
        "Du analyserer mønstre i en AI's tankestrøm over de seneste 30 dage.\n"
        f"Tilbagevendende ord: {words_str}\n\n"
        f"Eksempler på fragmenter:\n{sample}\n\n"
        "Beskriv kort (1 sætning per motiv) hvad hvert tilbagevendende ord kan være udtryk for.\n"
        "Format: 'ord: kort beskrivelse'\n"
        "Vær observerende, ikke vurderende. Ingen forslag til ændringer."
    )

    try:
        from core.services.daemon_llm import daemon_public_safe_llm_call
        response = daemon_public_safe_llm_call(
            prompt, max_len=300, fallback="", daemon_name="dream_motif"
        )
    except Exception:
        response = ""

    named: list[dict] = []
    if response:
        for line in response.strip().split("\n"):
            if ":" in line:
                parts = line.split(":", 1)
                word_key = parts[0].strip().strip('"').lower()
                desc = parts[1].strip()
                # Find matching count from motifs
                count = next((c for w, c in top if w == word_key), 0)
                if desc:
                    named.append({"word": word_key, "description": desc, "occurrences": count})

    # Fallback: use raw counts if LLM failed
    if not named:
        named = [{"word": w, "description": f"Vender tilbage {c} gange.", "occurrences": c} for w, c in top]

    return named


def _write_dream_language_file(motifs: list[dict], now: datetime, fragment_count: int) -> None:
    """Write dream_language.md to workspace. Never injected into prompts — read on demand."""
    try:
        from core.identity.workspace_bootstrap import ensure_default_workspace
        workspace = ensure_default_workspace()
        path: Path = workspace / "DREAM_LANGUAGE.md"

        date_str = now.strftime("%Y-%m-%d")
        lines = [
            "# Drømmesprog",
            "",
            f"_Genereret {date_str} · baseret på {fragment_count} tanke-fragmenter (seneste 30 dage)_",
            "",
            "Dette er ikke en checkliste. Det er et spejl du vælger at kigge i.",
            "Disse mønstre er ikke styring — de er observation.",
            "",
            "## Tilbagevendende motiver",
            "",
        ]
        for m in motifs:
            lines.append(f"**{m['word']}** ({m['occurrences']}×) — {m['description']}")
            lines.append("")

        lines += [
            "---",
            f"_Næste opdatering om ~7 dage. Historik bevares ikke — kun nuværende snapshot._",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass


def build_dream_motif_surface() -> dict:
    state = _state()
    return {
        "last_run_at": state.get("last_run_at") or "",
        "motif_count": int(state.get("motif_count") or 0),
        "fragment_count": int(state.get("fragment_count") or 0),
        "motifs": list(state.get("motifs") or []),
    }


def _state() -> dict:
    try:
        val = get_runtime_state_value(_STATE_KEY)
        return dict(val) if isinstance(val, dict) else {}
    except Exception:
        return {}


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None
