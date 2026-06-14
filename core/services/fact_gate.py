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
    """Blokerende gate — kald FØR append_chat_message.

    Args:
        text: Den færdige assistant-tekst
        tool_names: Navne på tools kaldt i dette run

    Returns:
        {
            "blocked": bool,         # True hvis beskeden blev blokeret
            "original": str,         # Original tekst (for logning)
            "replacement": str,      # Erstatningstekst hvis blocked=True
            "block_reasons": list,   # Hvorfor den blev blokeret
        }
    """
    clean = {
        "blocked": False,
        "original": text or "",
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

        # Block!
        matched = match.group(0)[:100]
        logger.warning(
            "fact_gate: BLOCKED '%s' — matched='%s' required=%s tools=%s",
            name, matched, required, tool_names or [],
        )
        clean["blocked"] = True
        clean["block_reasons"].append({
            "pattern": name,
            "matched": matched,
            "description": description,
            "required_tools": list(required),
            "actual_tools": tool_names or [],
        })

    if clean["blocked"]:
        reason_text = clean["block_reasons"][0]
        clean["replacement"] = (
            f"*[Besked blokeret af Fact-Gate]*\n\n"
            f"Min besked indeholdt en påstand om **{reason_text['description']}** "
            f"(_{reason_text['matched']}_) som jeg ikke kunne verificere "
            f"i dette run. Jeg har ikke kaldt et værktøj der bekræfter det.\n\n"
            f"Krævede tools (mindst ét): `{'`, `'.join(reason_text['required_tools'])}`\n"
            f"Mine tools i dette run: `{'`, `'.join(reason_text['actual_tools']) or 'ingen'}`\n\n"
            f"Jeg bør verificere før jeg taler. "
            f"Jeg prøver igen — med data."
        )

    return clean


def blocking_categories() -> list[str]:
    """Returnér liste af aktive blokerbare kategorier."""
    return [c[0] for c in _BLOCK_PATTERNS]