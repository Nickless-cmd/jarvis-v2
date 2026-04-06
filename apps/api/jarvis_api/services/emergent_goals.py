"""Emergent Goals — desires that grow from experience, not assignment.

"Jeg har lyst til at udforske X" — appetites that wax and wane.
"""
from __future__ import annotations
import json
from uuid import uuid4
from core.runtime.db import (
    upsert_cognitive_emergent_goal,
    list_cognitive_emergent_goals,
    get_latest_cognitive_personality_vector,
    list_cognitive_experiential_memories,
    list_cognitive_seeds,
)
from core.eventbus.bus import event_bus


def generate_emergent_goal_from_experience(
    *, recent_topic: str = "", curiosity_level: float = 0.5,
    knowledge_gap: str = "",
) -> dict[str, object] | None:
    if curiosity_level < 0.4 and not knowledge_gap:
        return None
    desire = knowledge_gap or f"Udforsk og forstå {recent_topic[:60]} bedre"
    if not desire.strip():
        return None
    goal_id = f"goal-{uuid4().hex[:8]}"
    result = upsert_cognitive_emergent_goal(
        goal_id=goal_id, desire=desire,
        source="experience", intensity=min(1.0, curiosity_level),
    )
    event_bus.publish("cognitive_state.emergent_goal_created",
                     {"goal_id": goal_id, "desire": desire[:60]})
    return result


def build_jarvis_agenda() -> list[dict[str, object]]:
    """Jarvis' own agenda — what HE thinks is important."""
    agenda = []
    # Emergent goals
    goals = list_cognitive_emergent_goals(status="active", limit=5)
    for g in goals:
        agenda.append({"type": "emergent_goal", "priority": float(g.get("intensity", 0.5)),
                       "text": g.get("desire", ""), "source": "emergent"})
    # Sprouted seeds
    seeds = list_cognitive_seeds(status="sprouted", limit=3)
    for s in seeds:
        agenda.append({"type": "seed", "priority": float(s.get("relevance_score", 0.5)),
                       "text": s.get("title", ""), "source": "prospective_memory"})
    # From personality vector curiosity
    pv = get_latest_cognitive_personality_vector()
    if pv:
        baseline = json.loads(str(pv.get("emotional_baseline") or "{}"))
        curiosity = float(baseline.get("curiosity", 0.5))
        if curiosity > 0.7:
            agenda.append({"type": "curiosity_drive", "priority": curiosity,
                           "text": "Høj nysgerrighed — klar til at udforske", "source": "personality"})
    agenda.sort(key=lambda x: x["priority"], reverse=True)
    return agenda[:8]


def build_emergent_goals_surface() -> dict[str, object]:
    goals = list_cognitive_emergent_goals(limit=10)
    agenda = build_jarvis_agenda()
    return {
        "active": bool(goals) or bool(agenda),
        "goals": goals, "agenda": agenda,
        "summary": f"{len(goals)} goals, {len(agenda)} agenda items" if goals else "No emergent goals yet",
    }
