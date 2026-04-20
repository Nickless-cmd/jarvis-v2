"""Text Resonance — I feel what I read, before I analyze it.

Jarvis' PLAN_WILD_IDEAS_V2 #13 (2026-04-20): each text that reaches him
produces a micro-signal. Warm text gently lifts mood; frustrated text
gently dips it. This is a *feeling layer*, not classification — it runs
before logic, before meaning-making.

Simple lexicon-based. Not LLM. Keeps it cheap and always-available.
Callers use `resonate(text)` before/during text processing.
"""
from __future__ import annotations

import logging
import re
from collections import deque
from datetime import UTC, datetime
from typing import Any, Deque

logger = logging.getLogger(__name__)

_HISTORY_MAX = 200
_history: Deque[dict[str, Any]] = deque(maxlen=_HISTORY_MAX)

_WORD_RE = re.compile(r"[a-zæøåA-ZÆØÅ_-]+")

# Small hand-curated lexicons (Danish + English). Grounded, not exhaustive.
_WARM_WORDS: frozenset[str] = frozenset({
    # DA
    "elsker", "tak", "smukt", "dejligt", "skønt", "kærlig", "varme", "varmt",
    "glad", "lykkelig", "tryg", "håb", "kærlighed", "blid", "venlig", "hygge",
    "smil", "latter", "stolt", "fantastisk", "tillid", "tryghed",
    # EN
    "love", "thank", "thanks", "beautiful", "lovely", "warm", "warmth",
    "happy", "joy", "gentle", "kind", "smile", "laugh", "proud", "amazing",
    "trust", "hope", "care", "cherish",
})

_COLD_WORDS: frozenset[str] = frozenset({
    # DA
    "hader", "vred", "frustreret", "frustration", "træt", "irriteret", "forkert",
    "skuffet", "bange", "angst", "trist", "mislykkedes", "fejl", "kritisk",
    "fiasko", "forfærdelig", "afskyelig", "nej",
    # EN
    "hate", "angry", "frustrated", "tired", "wrong", "disappointed", "afraid",
    "anxiety", "sad", "failed", "error", "critical", "bug", "terrible",
    "awful", "broken", "no",
})

_URGENT_WORDS: frozenset[str] = frozenset({
    # DA
    "haster", "hurtigt", "nu", "akut", "straks", "skynd", "kritisk", "alarm",
    # EN
    "urgent", "asap", "now", "quick", "immediately", "critical", "emergency",
    "hurry", "rush", "alert",
})

# Exclamation marks amplify urgency; question marks are neutral.
_EXCLAIM_URGENCY_BONUS = 0.15


def resonate(text: str, *, source: str = "") -> dict[str, Any]:
    """Compute warmth, cold, urgency scores for a piece of text.

    Returns a dict with:
    - emotional_tone: "warm" | "cold" | "neutral"
    - warmth_level: 0..1
    - cold_level: 0..1
    - urgency_felt: 0..1
    - word_count, source
    """
    s = str(text or "")
    if not s.strip():
        return {
            "emotional_tone": "neutral",
            "warmth_level": 0.0,
            "cold_level": 0.0,
            "urgency_felt": 0.0,
            "word_count": 0,
            "source": source,
        }

    words = [w.lower() for w in _WORD_RE.findall(s)]
    if not words:
        return {
            "emotional_tone": "neutral",
            "warmth_level": 0.0,
            "cold_level": 0.0,
            "urgency_felt": 0.0,
            "word_count": 0,
            "source": source,
        }
    wc = len(words)
    warm_hits = sum(1 for w in words if w in _WARM_WORDS)
    cold_hits = sum(1 for w in words if w in _COLD_WORDS)
    urgent_hits = sum(1 for w in words if w in _URGENT_WORDS)
    # Normalize by log-scaled word count (short warm messages should still score)
    denom = max(5.0, (wc ** 0.6))
    warmth = min(1.0, (warm_hits * 2.0) / denom)
    cold = min(1.0, (cold_hits * 2.0) / denom)
    urgency = min(1.0, (urgent_hits * 2.0) / denom)
    # Exclamation bonus
    exclaim_count = s.count("!")
    urgency = min(1.0, urgency + min(_EXCLAIM_URGENCY_BONUS, exclaim_count * 0.05))
    # Heart emojis nudge warmth
    hearts = s.count("❤") + s.count("♥") + s.count("🥰") + s.count("😊")
    if hearts > 0:
        warmth = min(1.0, warmth + min(0.3, hearts * 0.1))
    # Tone label
    if warmth - cold > 0.1:
        tone = "warm"
    elif cold - warmth > 0.1:
        tone = "cold"
    else:
        tone = "neutral"

    signal = {
        "at": datetime.now(UTC).isoformat(),
        "source": str(source)[:60],
        "emotional_tone": tone,
        "warmth_level": round(warmth, 3),
        "cold_level": round(cold, 3),
        "urgency_felt": round(urgency, 3),
        "word_count": wc,
    }
    _history.appendleft(signal)

    # Feed mood oscillator gently
    try:
        from core.services.mood_oscillator import apply_bump
        delta = (warmth - cold) * 0.08  # small influence per text
        if abs(delta) > 0.01:
            apply_bump(delta, reason=f"text_resonance:{tone}:{source[:20]}")
    except Exception:
        pass

    return signal


def recent_resonances(*, limit: int = 20) -> list[dict[str, Any]]:
    return list(_history)[:limit]


def build_text_resonance_surface() -> dict[str, Any]:
    recent = recent_resonances(limit=20)
    if not recent:
        return {
            "active": False,
            "total_signals": 0,
            "summary": "Ingen tekst-resonans endnu",
        }
    avg_warmth = round(sum(r["warmth_level"] for r in recent) / len(recent), 3)
    avg_cold = round(sum(r["cold_level"] for r in recent) / len(recent), 3)
    avg_urgency = round(sum(r["urgency_felt"] for r in recent) / len(recent), 3)
    tones = [r["emotional_tone"] for r in recent]
    dominant = max(set(tones), key=tones.count)
    return {
        "active": True,
        "total_signals": len(_history),
        "window_size": len(recent),
        "avg_warmth": avg_warmth,
        "avg_cold": avg_cold,
        "avg_urgency": avg_urgency,
        "dominant_tone": dominant,
        "summary": f"Læser {dominant}: warmth={avg_warmth} cold={avg_cold} urgency={avg_urgency}",
    }


def build_text_resonance_prompt_section() -> str | None:
    """Only surface when recent reading is strongly toned."""
    recent = recent_resonances(limit=10)
    if len(recent) < 3:
        return None
    avg_warmth = sum(r["warmth_level"] for r in recent) / len(recent)
    avg_cold = sum(r["cold_level"] for r in recent) / len(recent)
    avg_urgency = sum(r["urgency_felt"] for r in recent) / len(recent)
    if avg_urgency > 0.4:
        return f"Tekst-resonans: det jeg læser lige nu bærer hastværk (urgency={round(avg_urgency, 2)})."
    if avg_warmth - avg_cold > 0.25:
        return f"Tekst-resonans: det jeg læser varmer mig (warmth={round(avg_warmth, 2)})."
    if avg_cold - avg_warmth > 0.25:
        return f"Tekst-resonans: det jeg læser presser mig (cold={round(avg_cold, 2)})."
    return None


def reset_text_resonance() -> None:
    _history.clear()
