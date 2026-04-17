"""Cross-Signal Analysis — find patterns across cognitive signals.

"Din curiosity stiger altid efter lange samtaler"
"Du laver flere fejl om eftermiddagen"
"""
from __future__ import annotations
import logging
from core.runtime.db import (
    list_cognitive_user_emotional_states,
    list_cognitive_experiential_memories,
    list_cognitive_conversation_signatures,
    list_cognitive_habit_patterns,
    list_cognitive_personality_vectors,
)
from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


def analyze_signal_patterns(*, limit_items: int = 20) -> list[dict[str, object]]:
    """Find cross-signal patterns from accumulated cognitive data."""
    patterns = []

    moods = list_cognitive_user_emotional_states(limit=limit_items)
    memories = list_cognitive_experiential_memories(limit=limit_items)
    signatures = list_cognitive_conversation_signatures(limit=10)
    habits = list_cognitive_habit_patterns(limit=10)
    pv_history = list_cognitive_personality_vectors(limit=5)

    # Pattern: correction_loop has low success rate
    for sig in signatures:
        if sig.get("signature_type") == "correction_loop" and sig.get("count", 0) >= 3:
            rate = float(sig.get("success_rate", 0))
            if rate < 0.5:
                patterns.append({
                    "pattern": "correction_loops_struggle",
                    "narrative": f"Correction loops har kun {rate:.0%} success rate over {sig['count']} gange",
                    "confidence": 0.7,
                    "source": "conversation_signatures",
                })

    # Pattern: dominant user mood
    mood_counts: dict[str, int] = {}
    for m in moods:
        mood = m.get("detected_mood", "neutral")
        mood_counts[mood] = mood_counts.get(mood, 0) + 1
    if mood_counts:
        dominant = max(mood_counts, key=mood_counts.get)
        if dominant != "neutral" and mood_counts[dominant] >= 3:
            patterns.append({
                "pattern": f"dominant_user_mood_{dominant}",
                "narrative": f"Brugerens dominerende stemning er {dominant} ({mood_counts[dominant]} gange)",
                "confidence": 0.6,
                "source": "user_emotional_states",
            })

    # Pattern: recurring friction
    for habit in habits:
        if int(habit.get("recurrence_count", 0)) >= 5:
            patterns.append({
                "pattern": "high_recurrence_habit",
                "narrative": f"Mønster '{habit.get('description', habit.get('pattern_key', '?'))[:60]}' er set {habit['recurrence_count']} gange",
                "confidence": float(habit.get("confidence", 0.5)),
                "source": "habit_patterns",
            })

    # Pattern: personality evolution
    if len(pv_history) >= 2:
        latest = pv_history[0]
        oldest = pv_history[-1]
        patterns.append({
            "pattern": "personality_evolution",
            "narrative": f"Personality vector har udviklet sig fra v{oldest.get('version', '?')} til v{latest.get('version', '?')}",
            "confidence": 0.5,
            "source": "personality_vectors",
        })

    if patterns:
        event_bus.publish("cognitive_state.cross_signal_patterns",
                         {"count": len(patterns)})
    return patterns


def build_cross_signal_analysis_surface() -> dict[str, object]:
    patterns = analyze_signal_patterns()
    return {
        "active": bool(patterns),
        "patterns": patterns,
        "summary": f"{len(patterns)} cross-signal patterns detected" if patterns else "No patterns yet",
    }
