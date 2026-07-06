"""Fact-Gate — blocking output gate for unverifiable factual claims.

Forslag 1 fra Bjørns analyse 2026-06-13: en blokerende gate der scanner
mit færdige svar for faktuelle påstande (tal, commits, tests, service-status)
og BLOCKERER beskeden hvis påstanden ikke kan verificeres mod data.

Kører i visible_runs.py EFTER `_finalize_second_pass_visible_text` men
FØR `append_chat_message`. Hvis gaten blokerer, returneres en
erstatningstekst der forklarer blocken — og beskeden gemmes ALDRIG.

Flow: text → fact_gate_enforce() → (blocked=True, replacement) | (blocked=False, original)

Kun SHARPE, mekanisk verificerbare påstande blokeres.
Uskarpe påstande ('mange commits', 'det føles som...') passerer frit.
Fail-open: enhver tvivl/fejl → passér (falsk negativ > falsk positiv).
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Blokerbare mønstre ─────────────────────────────────────────────────
# (name, pattern, required_any_of_tools, description)
# Kun patterns hvor required_any_of er mekanisk verificerbare tools.

_BLOCK_PATTERNS: list[tuple[str, re.Pattern, tuple[str, ...], str]] = [
    # Commit-count claims: "45 commits", "~3000 commits", "over 30 commits"
    ("commit_count",
     re.compile(
         r"\b(?:~|cirka|over|under|ca\.?)?\s*\d{1,5}\s*"
         r"(?:commits?|commits? i dag|commits? i alt)\b",
         re.IGNORECASE,
     ),
     ("bash", "operator_bash", "git_log"),
     "Påstand om antal commits kræver git_log"),

    # Stats about self: "N tests", "N daemons", "N services"
    ("self_stats",
     re.compile(
         r"\b\d{1,4}\s*(?:tests?|daemons?|services?|"
         r"expressions?|ticks?|kald|calls?)\b",
         re.IGNORECASE,
     ),
     ("bash", "db_query", "daemon_status", "test_count"),
     "Påstand om eget tal kræver værktøj"),

    # Service status claims
    ("service_active",
     re.compile(
         r"\b(?:jarvis-api|jarvis-runtime|servicen?|daemon(?:en)?)\s+"
         r"(?:kører|er\s+(?:aktiv|oppe)|is\s+(?:active|running|up))\b",
         re.IGNORECASE,
     ),
     ("bash", "operator_bash", "service_status", "control_daemon"),
     "Påstand om service-status kræver service_status"),

    # "cachen viser X%" — specifikke tal
    ("cache_percentage",
     re.compile(
         r"\b\d{1,3}\.\d%\s*(?:cache|hit\s*rate|hit_rate)\b",
         re.IGNORECASE,
     ),
     ("bash", "db_query"),
     "Påstand om cache-procent kræver db_query"),
]

# ── Whitelist — aldrig blokere ─────────────────────────────────────────
_WHITELIST: list[re.Pattern] = [
    re.compile(r"\bjeg\s+er\s+en\s+stor\s+fan\b", re.IGNORECASE),
    re.compile(r"\bdet\s+var\s+en\s+god\s+idé\b", re.IGNORECASE),
]


def _has_tool_evidence(text: str, pattern: re.Pattern,
                        required: tuple[str, ...],
                        tool_names: list[str]) -> bool:
    """Tjek om påstanden i text har tool-evidens.

    To måder at passere:
    1) Et af `required`-tools blev kaldt i dette run (tool_names)
    2) Teksten indeholder ALLEREDE en verification-reference
       (f.eks. "git log viser 45 commits")
    """
    # 1. Tool-evidence
    if tool_names:
        lower_tools = {t.lower() for t in tool_names}
        if lower_tools & {r.lower() for r in required}:
            return True

    # 2. Teksten nævner selv verification-kilden
    verification_hints = ["git log", "tjekkede", "kørte", "verificerede",
                          "viste", "tallet er", "db_query", "tæller"]
    for hint in verification_hints:
        if hint.lower() in text.lower():
            return True

    return False


def fact_gate_enforce(
    text: str | None,
    tool_names: list[str] | None = None,
) -> dict[str, Any]:
    """Detekterende gate — kald FØR append_chat_message.

    2026-07-06 (Bjørn+Jarvis): gaten BLOKERER IKKE længere. Detektionen af
    uverificerede tal-/status-påstande er uændret, men i stedet for at ERSTATTE
    beskeden BEVARER vi Jarvis' tekst og APPENDER en fodnote i bunden (én pr.
    fund). `blocked` er nu altid False; brug `annotated_text`.

    Args:
        text: Den færdige assistant-tekst
        tool_names: Navne på tools kaldt i dette run

    Returns:
        {
            "blocked": bool,          # ALTID False — gaten blokerer aldrig mere
            "original": str,          # Original tekst
            "annotated_text": str,    # Original tekst + fodnote(r) i bunden
            "replacement": str,       # = annotated_text (bagudkompat)
            "block_reasons": list,    # Detekterede uverificerede påstande (bevaret)
        }
    """
    clean = {
        "blocked": False,
        "original": text or "",
        "annotated_text": text or "",
        "replacement": text or "",
        "block_reasons": [],
    }
    if not text or not text.strip():
        return clean

    for name, pattern, required, description in _BLOCK_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        if _has_tool_evidence(text, pattern, required, tool_names or []):
            logger.debug("fact_gate: passed '%s' (has evidence)", name)
            continue

        # Detektion bevaret — men vi flagger (fodnote), blokerer ikke.
        matched = match.group(0)[:100]
        logger.warning(
            "fact_gate: FLAGGED '%s' — matched='%s' required=%s tools=%s",
            name, matched, required, tool_names or [],
        )
        clean["block_reasons"].append({
            "pattern": name,
            "matched": matched,
            "description": description,
            "required_tools": list(required),
            "actual_tools": tool_names or [],
        })

    # Byg fodnote(r) i den konsistente stil: én ✋-linje pr. uverificeret påstand.
    if clean["block_reasons"]:
        notes = []
        for reason in clean["block_reasons"]:
            req = ", ".join(reason["required_tools"]) or "tool-evidens"
            notes.append(
                f"✋ Uverificeret: '{reason['matched']}' — kræver {req}"
            )
        clean["annotated_text"] = text.rstrip() + "\n\n" + "\n".join(notes)
        clean["replacement"] = clean["annotated_text"]

    return clean


def blocking_categories() -> list[str]:
    """Returnér liste af aktive blokerbare kategorier."""
    return [c[0] for c in _BLOCK_PATTERNS]