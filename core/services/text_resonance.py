"""Text Resonance — I feel what I read, before I analyze it.

Jarvis' PLAN_WILD_IDEAS_V2 #13 (2026-04-20): each text that reaches him
produces a micro-signal. Warm text gently lifts mood; frustrated text
gently dips it. This is a *feeling layer*, not classification — it runs
before logic, before meaning-making.

Simple lexicon-based. Not LLM. Keeps it cheap and always-available.
Callers use `resonate(text)` before/during text processing.

PERSISTERING (25/9-2026)

Leksikonet, scoringen og koblingen til humoer-oscillatoren var der hele tiden,
og `resonate` HAR en kalder: `chat_sessions.append_chat_message` paa hver
brugerbesked. Modulet var altsaa ikke ubygget — det var uden bord.

`_history` var en `deque` i modulet. Den doede ved genstart, og fladen blev
bygget i `jarvis-api` mens teksten blev laest i samme proces som chatten, saa
selv mens den levede kunne den vaere usynlig det sted den skulle vises. Samme
fejlklasse som `_PENDING_APPROVALS` og `reboot_awareness._DETECTION_RUN`.

Skrivningen sker per BRUGERBESKED, ikke per prompt: det er en haandfuld i
minuttet, og modulet kalder i forvejen humoer-oscillatoren samme sted.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.workspace_paths import shared_dir

logger = logging.getLogger(__name__)

_HISTORY_MAX = 200


def _storage_path() -> Path:
    return shared_dir() / "runtime" / "text_resonance.json"


def _load() -> list[dict[str, Any]]:
    """Nyeste foerst — samme raekkefoelge som den gamle `deque.appendleft`."""
    p = _storage_path()
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except Exception as exc:
        logger.warning("text_resonance: kunne ikke laeses: %s", exc)
        return []


def _save(historik: list[dict[str, Any]]) -> None:
    p = _storage_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(historik[:_HISTORY_MAX], ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(p)
    except Exception as exc:
        logger.warning("text_resonance: kunne ikke gemmes: %s", exc)

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
    # Persisteringen har sit EGET vaern.
    #
    # Kaldet ligger i `chat_sessions.append_chat_message`, som har et
    # `except: pass` om det. Men et modul maa ikke laene sig paa sin kalders
    # vaern — saa er garantien kalderens, ikke modulets, og den naeste kalder
    # arver den ikke. En resonans maa aldrig kunne forhindre at en besked
    # bliver gemt.
    try:
        historik = _load()
        historik.insert(0, signal)
        _save(historik)
    except Exception as exc:
        logger.warning("text_resonance: signalet kunne ikke gemmes: %s", exc)

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
    return _load()[:limit]


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
    # Uafgjort er «neutral», ikke et vilkaarligt valg.
    #
    # Foer stod der `max(set(tones), key=tones.count)`. Med lige mange `warm`
    # og `cold` afgoeres det af maengdens iterationsraekkefoelge, som afhaenger
    # af hash-seedet — altsaa forskelligt fra proces til proces. Maalt: én varm
    # og én kold besked gav «Laeser warm» med warmth=0.4 og cold=0.4.
    tones = [r["emotional_tone"] for r in recent]
    taelling = {t: tones.count(t) for t in ("warm", "cold", "neutral")}
    hoejest = max(taelling.values())
    vindere = [t for t in ("warm", "cold", "neutral") if taelling[t] == hoejest]
    dominant = vindere[0] if len(vindere) == 1 else "neutral"
    return {
        "active": True,
        "total_signals": len(_load()),
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
    _save([])
