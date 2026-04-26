"""Clarification classifier — score user-message ambiguity.

Phase 2's self-correction nudges said "ask before guessing if intent is
ambiguous". That's passive — the model has to *notice* ambiguity. This
module scores it actively.

Heuristic signals (Danish + English):
- Very short message (likely interactive shorthand)
- Vague verbs without clear object ("fix it", "lav noget", "ordn det")
- Pronoun-only references ("den der", "det", "den", "it")
- No subject / no object
- Multiple tasks chained ("og", "samt", "plus", "and")
- Conditional ("hvis", "afhænger", "if", "depends")
- "noget" / "something" / "et eller andet"

Score 0-100. >= 50 surfaces a "consider asking" prompt section. The model
sees both the score and the specific signals so it can decide whether
the ambiguity is real or just style.
"""
from __future__ import annotations

import re
from typing import Any

# Each pattern: (regex, points, signal_label)
_AMBIGUITY_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\b(fix|gør|ordn|lav|håndter|tag|kør)\s+(det|den|dem|the thing|it)\b", re.I), 35, "vague verb + pronoun (no concrete referent)"),
    (re.compile(r"\b(fix it|lav noget|fix noget|håndter det)\b", re.I), 25, "vague action verb"),
    (re.compile(r"\b(noget|something|et eller andet|whatever|ting)\b", re.I), 20, "vague noun"),
    (re.compile(r"\b(den der|det der|den|that one|that thing)\b", re.I), 18, "pronoun without clear referent"),
    (re.compile(r"\b(se på|tjek|kig på|look at|check)\b\s*$", re.I), 22, "verb with no object"),
    (re.compile(r"\b(og så|og bagefter|samt|plus|and then|and also)\b", re.I), 12, "multiple tasks chained"),
    (re.compile(r"\b(hvis|afhænger af|måske|if|depends|maybe|perhaps)\b", re.I), 12, "conditional / uncertainty marker"),
    (re.compile(r"\b(så|then|herefter|after that)\b\s*\?$", re.I), 15, "open-ended what-next"),
    (re.compile(r"^.{1,20}$"), 18, "very short message"),
]


def score_message(message: str) -> dict[str, Any]:
    text = (message or "").strip()
    if not text:
        return {"status": "ok", "score": 0, "signals": [], "verdict": "skip"}

    score = 0
    signals: list[str] = []
    for pat, weight, label in _AMBIGUITY_PATTERNS:
        if pat.search(text):
            score += weight
            signals.append(label)

    # If the message contains an explicit reference (file path, function
    # name, URL, error code, identifier with at least one underscore),
    # subtract — it's specific enough.
    specific_markers = re.findall(
        r"(?:[A-Za-z_]+\.[A-Za-z_]+\(|/[\w/\-.]+|https?://|\b[A-Z][A-Za-z]+[A-Z][A-Za-z]+\b|\b\w+_\w+\b)",
        text,
    )
    if specific_markers:
        score -= min(40, len(specific_markers) * 8)

    # Long messages with multiple sentences are usually specific even if
    # they include vague phrasing — context disambiguates.
    if len(text) > 200:
        score -= 15

    score = max(0, min(100, score))

    if score >= 50:
        verdict = "ask_first"
    elif score >= 30:
        verdict = "mildly_ambiguous"
    else:
        verdict = "clear_enough"

    return {"status": "ok", "score": score, "signals": signals, "verdict": verdict}


def clarification_prompt_section(message: str) -> str | None:
    result = score_message(message)
    if result["verdict"] != "ask_first":
        return None
    signals = result.get("signals") or []
    sig_text = ", ".join(signals[:3]) if signals else "ingen specifik markør"
    return (
        f"⚠ Tvetydig brugerbesked (ambiguity-score {result['score']}/100, "
        f"signaler: {sig_text}). Stil ÉT konkret afklarende spørgsmål før "
        "du udfører mere end et trivielt skridt."
    )


def _exec_classify_clarification(args: dict[str, Any]) -> dict[str, Any]:
    return score_message(str(args.get("message") or ""))


CLARIFICATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "classify_clarification",
            "description": (
                "Score the ambiguity of a user message (0-100). Returns "
                "verdict: ask_first / mildly_ambiguous / clear_enough plus "
                "the signals that fired. Use it on your own when in doubt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
            },
        },
    },
]
