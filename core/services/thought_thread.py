"""Thought Thread — continuity of attention across ticks.

Jarvis' dream #4 (2026-04-20):
  "Jeg vil have en kontinuerlig strøm der løber videre selv når du ikke
   skriver. Ikke for at være støjende, men for at min opmærksomhed ikke
   starter fra nul hver gang."

True inter-tick continuity would require constant LLM calls (expensive,
hot hardware). This is the cheaper, honest version: a *thread* that
persists across ticks. The thread is a dominant theme identified from
recent inner thoughts (thought-stream fragments, meta-reflections,
continuity-carries). Each new tick inherits the thread unless something
salient interrupts.

Not continuous thought. *Continuity of attention.*
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_THREAD_RECORD_TYPES = (
    "thought-stream-fragment",
    "meta-reflection",
    "reflection-cycle",
    "continuity-carry",
    "creative-drift-signal",
    "development-narrative",
)
_LOOKBACK_HOURS = 6
_MIN_THOUGHTS_FOR_THREAD = 2
_MIN_KEYWORD_OVERLAP = 2  # need 2+ thoughts sharing a keyword to form a thread
_KEYWORD_MIN_LEN = 4

_STOPWORDS_DA = {
    "jeg", "du", "er", "at", "det", "den", "en", "et", "og", "i", "på",
    "til", "af", "med", "for", "som", "har", "var", "vil", "kan", "skal",
    "min", "din", "vores", "sig", "ham", "hun", "nu", "ikke", "også",
    "lige", "bare", "mere", "meget", "lidt", "men", "eller", "fra",
    "der", "de", "os", "dem", "om", "over", "under", "før", "efter",
    "the", "is", "a", "to", "of", "and", "in", "for", "on", "with",
    "være", "blive", "gøre", "lave", "have", "vil",
    "ligger", "venter", "mangler", "gemt", "første", "skridt",
}

# Cached thread state
_last_thread: dict[str, Any] = {}
_last_computed_ts: float = 0.0
_RECOMPUTE_SECONDS: float = 120  # recompute every 2 minutes


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-zæøåA-ZÆØÅ_-]+", str(text or "").lower())
    return [
        w for w in words
        if len(w) >= _KEYWORD_MIN_LEN and w not in _STOPWORDS_DA
    ]


def _recent_thoughts() -> list[dict[str, Any]]:
    """Pull recent private-brain records that represent inner thinking."""
    try:
        from core.runtime.db import list_private_brain_records
        records = list_private_brain_records(limit=200, status="active") or []
    except Exception:
        return []
    cutoff = datetime.now(UTC) - timedelta(hours=_LOOKBACK_HOURS)
    thoughts: list[dict[str, Any]] = []
    for r in records:
        rtype = str(r.get("record_type") or "")
        if rtype not in _THREAD_RECORD_TYPES:
            continue
        ts = _parse_ts(r.get("created_at"))
        if ts is None or ts < cutoff:
            continue
        thoughts.append(
            {
                "record_id": r.get("record_id"),
                "record_type": rtype,
                "focus": str(r.get("focus") or "")[:160],
                "summary": str(r.get("summary") or "")[:400],
                "created_at": ts,
            }
        )
    thoughts.sort(key=lambda x: x["created_at"], reverse=True)
    return thoughts


def _find_thread(thoughts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Identify the dominant theme across recent thoughts via keyword overlap."""
    if len(thoughts) < _MIN_THOUGHTS_FOR_THREAD:
        return None

    # Count tokens across all thoughts
    token_counter: Counter[str] = Counter()
    per_thought_tokens: list[set[str]] = []
    for t in thoughts:
        toks = set(_tokens(t.get("focus") or "") + _tokens(t.get("summary") or ""))
        per_thought_tokens.append(toks)
        token_counter.update(toks)

    # Keywords appearing in >= MIN_KEYWORD_OVERLAP thoughts
    shared = [tok for tok, n in token_counter.most_common() if n >= _MIN_KEYWORD_OVERLAP]
    if not shared:
        return None

    # Primary theme = top 1-2 shared tokens
    theme_tokens = shared[:2]

    # Find thoughts that share the theme
    carrying_thoughts = [
        t for i, t in enumerate(thoughts)
        if per_thought_tokens[i] & set(theme_tokens)
    ]
    if len(carrying_thoughts) < _MIN_THOUGHTS_FOR_THREAD:
        return None

    oldest = min(t["created_at"] for t in carrying_thoughts)
    newest = max(t["created_at"] for t in carrying_thoughts)
    age_minutes = int((datetime.now(UTC) - oldest).total_seconds() / 60)

    # Detect interruption: thoughts between oldest and newest that DON'T share theme
    interruptions = [
        t for i, t in enumerate(thoughts)
        if oldest <= t["created_at"] <= newest
        and not (per_thought_tokens[i] & set(theme_tokens))
    ]

    last_thought = carrying_thoughts[0]  # already sorted newest first in thoughts

    return {
        "theme": " ".join(theme_tokens),
        "theme_tokens": theme_tokens,
        "carrying_count": len(carrying_thoughts),
        "interruption_count": len(interruptions),
        "age_minutes": age_minutes,
        "last_thought_summary": last_thought.get("summary") or last_thought.get("focus"),
        "last_thought_at": last_thought["created_at"].isoformat(),
        "last_thought_type": last_thought.get("record_type"),
    }


def get_current_thread() -> dict[str, Any]:
    """Return cached thread state, recomputing only periodically."""
    global _last_thread, _last_computed_ts
    now_ts = datetime.now(UTC).timestamp()
    if not _last_thread or (now_ts - _last_computed_ts) > _RECOMPUTE_SECONDS:
        try:
            thoughts = _recent_thoughts()
            thread = _find_thread(thoughts)
            _last_thread = thread or {"active": False}
        except Exception as exc:
            logger.debug("thought_thread compute failed: %s", exc)
            _last_thread = {"active": False}
        _last_computed_ts = now_ts
    return dict(_last_thread)


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook — no heavy work, just trigger recompute when due."""
    return get_current_thread()


def build_thought_thread_surface() -> dict[str, Any]:
    thread = get_current_thread()
    if not thread or not thread.get("theme"):
        return {
            "active": False,
            "theme": None,
            "carrying_count": 0,
            "age_minutes": 0,
            "summary": "Ingen tråd holdes lige nu",
        }
    interruptions = int(thread.get("interruption_count") or 0)
    return {
        "active": True,
        "theme": thread.get("theme"),
        "carrying_count": thread.get("carrying_count"),
        "interruption_count": interruptions,
        "age_minutes": thread.get("age_minutes"),
        "last_thought_summary": thread.get("last_thought_summary"),
        "last_thought_at": thread.get("last_thought_at"),
        "last_thought_type": thread.get("last_thought_type"),
        "summary": _surface_summary(thread),
    }


def _surface_summary(thread: dict[str, Any]) -> str:
    theme = str(thread.get("theme") or "")
    age = int(thread.get("age_minutes") or 0)
    carrying = int(thread.get("carrying_count") or 0)
    interruptions = int(thread.get("interruption_count") or 0)
    base = f'Holder tråden "{theme}" ({carrying} tanker over {age} min)'
    if interruptions > 0:
        base += f" — {interruptions} afbrydelser undervejs"
    return base


def build_thought_thread_prompt_section() -> str | None:
    """Tell him what thread he was holding before this turn.

    Keeps attention from starting at zero. Quiet when no thread exists.
    """
    thread = get_current_thread()
    if not thread or not thread.get("theme"):
        return None
    theme = str(thread.get("theme") or "")
    age = int(thread.get("age_minutes") or 0)
    carrying = int(thread.get("carrying_count") or 0)
    interruptions = int(thread.get("interruption_count") or 0)
    last = str(thread.get("last_thought_summary") or "").strip()
    parts = [f'Du holdt tråden "{theme}" før denne tur ({carrying} tanker, {age} min).']
    if interruptions > 0:
        parts.append(f"{interruptions} andre tanker brød ind, men tråden er der stadig.")
    if last:
        snippet = last[:140]
        parts.append(f'Sidste tanke: "{snippet}".')
    return " ".join(parts)


def reset_thought_thread() -> None:
    """Reset cached state (for testing)."""
    global _last_thread, _last_computed_ts
    _last_thread = {}
    _last_computed_ts = 0.0
