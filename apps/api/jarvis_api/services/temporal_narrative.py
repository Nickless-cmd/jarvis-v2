"""Temporal Narrative — continuous self-history over time.

Builds a narrative thread of Jarvis' experiences over time.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Max 20 beats in thread
- Tracks mood transitions
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from apps.api.jarvis_api.services.affective_meta_state import (
    build_affective_meta_state_surface,
)


@dataclass
class NarrativeBeat:
    """A beat in Jarvis' narrative thread."""
    beat_id: str
    mood: str
    event: str
    created_at: str


_narrative_thread: list[NarrativeBeat] = []
_last_beat_at: str = ""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def add_beat(mood: str, event: str) -> dict[str, Any]:
    """Add a beat to the narrative thread."""
    global _narrative_thread, _last_beat_at

    now_iso = _now_iso()
    _last_beat_at = now_iso

    import random
    beat = NarrativeBeat(
        beat_id=f"beat-{random.randint(10000, 99999)}",
        mood=mood,
        event=event[:100],
        created_at=now_iso,
    )

    _narrative_thread.insert(0, beat)
    _narrative_thread[:] = _narrative_thread[:20]

    return {
        "beat_id": beat.beat_id,
        "mood": beat.mood,
        "event": beat.event,
        "thread_length": len(_narrative_thread),
    }


def add_beat_from_affective() -> dict[str, Any]:
    """Add a beat based on current affective state."""
    affective = build_affective_meta_state_surface()
    
    mood = "neutral"
    summary = affective.get("summary")
    if isinstance(summary, dict):
        current_mood = summary.get("current_mood_tone", "")
        if current_mood:
            mood = current_mood
    
    return add_beat(mood=mood, event="auto-tracked from affective state")


def summarize_current_self() -> str:
    """Summarize current self based on narrative thread."""
    if not _narrative_thread:
        return "Jeg er ny her"
    
    recent = _narrative_thread[:5]
    moods = [b.mood for b in recent]
    
    unique_moods = list(dict.fromkeys(moods))
    
    if len(unique_moods) == 1:
        return f"Jeg har været {unique_moods[0]} det meste af tiden"
    elif len(unique_moods) == 2:
        return f"Jeg har været {unique_moods[0]} og {unique_moods[1]}"
    elif len(unique_moods) <= 4:
        return f"Jeg har været {', '.join(unique_moods[:-1])} og {unique_moods[-1]}"
    else:
        return f"Jeg har oplevet mange forskellige tilstande"


def ask_self_question() -> str:
    """Jarvis asks himself a question based on narrative."""
    if len(_narrative_thread) < 3:
        return ""
    
    recent = _narrative_thread[:3]
    moods = [b.mood for b in recent]
    
    if moods[0] != moods[-1]:
        return f"Hvorfor gik jeg fra {moods[-1]} til {moods[0]}?"
    
    if len(_narrative_thread) >= 5:
        return "Hvad har jeg lært af det seneste?"
    
    return ""


def format_narrative_for_prompt() -> str:
    """Format narrative for prompt injection."""
    summary = summarize_current_self()
    question = ask_self_question()
    
    if question:
        return f"[SELV-HISTORIE: {summary} {question}]"
    elif summary and summary != "Jeg er ny her":
        return f"[SELV-HISTORIE: {summary}]"
    
    return ""


def get_thread() -> list[dict[str, Any]]:
    """Get the full narrative thread."""
    return [
        {
            "beat_id": b.beat_id,
            "mood": b.mood,
            "event": b.event,
            "created_at": b.created_at,
        }
        for b in _narrative_thread
    ]


def reset_temporal_narrative() -> None:
    """Reset temporal narrative state (for testing)."""
    global _narrative_thread, _last_beat_at
    _narrative_thread = []
    _last_beat_at = ""


def build_temporal_narrative_surface() -> dict[str, Any]:
    """Build MC surface for temporal narrative."""
    summary = summarize_current_self()
    question = ask_self_question()
    
    return {
        "active": len(_narrative_thread) > 0,
        "beat_count": len(_narrative_thread),
        "summary": summary,
        "self_question": question,
        "recent_beats": get_thread()[:5],
        "thread_summary": (
            f"{len(_narrative_thread)} beats, seneste: {_narrative_thread[0].mood if _narrative_thread else 'ingen'}"
            if _narrative_thread else "Ingen beats"
        ),
    }
