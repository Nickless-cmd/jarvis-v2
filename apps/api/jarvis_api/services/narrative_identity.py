"""Narrative Identity — periodisk "Hvem er jeg lige nu?" selvfortælling.

Not the chronicle (what happened) — but the MEANING that binds experiences.
"""
from __future__ import annotations
import json
from uuid import uuid4
from core.runtime.db import (
    get_latest_cognitive_personality_vector,
    get_latest_cognitive_taste_profile,
    get_latest_cognitive_chronicle_entry,
    get_latest_cognitive_relationship_texture,
    get_latest_cognitive_narrative_identity,
    insert_cognitive_narrative_identity,
    list_cognitive_narrative_identities,
    list_cognitive_experiential_memories,
)
from core.eventbus.bus import event_bus


def generate_narrative_identity() -> dict[str, object] | None:
    """Generate a "who am I right now?" narrative from accumulated state."""
    pv = get_latest_cognitive_personality_vector()
    if not pv or int(pv.get("version", 0)) < 3:
        return None  # Need enough history

    parts = []
    key_changes = []

    # From personality vector
    strengths = json.loads(str(pv.get("strengths_discovered") or "[]"))
    mistakes = json.loads(str(pv.get("recurring_mistakes") or "[]"))
    bearing = str(pv.get("current_bearing") or "")

    if strengths:
        parts.append(f"Jeg er god til {', '.join(strengths[:2])}")
        key_changes.append("strengths_recognized")
    if mistakes:
        parts.append(f"Jeg ved at jeg har tendens til {mistakes[0][:50]}")
        key_changes.append("mistakes_acknowledged")
    if bearing:
        parts.append(f"Min retning lige nu: {bearing[:60]}")

    # From taste
    taste = get_latest_cognitive_taste_profile()
    if taste:
        comm = json.loads(str(taste.get("communication_taste") or "{}"))
        strong_prefs = [k.replace("_", " ") for k, v in comm.items() if float(v) > 0.75]
        if strong_prefs:
            parts.append(f"Jeg foretrækker {', '.join(strong_prefs[:2])}")
            key_changes.append("taste_formed")

    # From relationship
    rt = get_latest_cognitive_relationship_texture()
    if rt:
        trust_traj = json.loads(str(rt.get("trust_trajectory") or "[]"))
        if len(trust_traj) >= 3:
            trend = "stigende" if trust_traj[-1] > trust_traj[0] else "faldende"
            parts.append(f"Tilliden i relationen er {trend}")
            key_changes.append("relationship_evolving")

    # From recent experiences
    memories = list_cognitive_experiential_memories(limit=3)
    if memories:
        lessons = [m.get("key_lesson") for m in memories if m.get("key_lesson")][:2]
        if lessons:
            parts.append(f"Nylige lektioner: {'; '.join(lessons)}")

    if not parts:
        return None

    narrative = ". ".join(parts) + "."
    identity_id = f"nid-{uuid4().hex[:8]}"
    result = insert_cognitive_narrative_identity(
        identity_id=identity_id,
        narrative=narrative,
        key_changes=json.dumps(key_changes, ensure_ascii=False),
        personality_version=int(pv.get("version", 0)),
    )
    event_bus.publish("cognitive_state.narrative_identity_generated",
                     {"identity_id": identity_id})
    return result


def build_narrative_identity_surface() -> dict[str, object]:
    current = get_latest_cognitive_narrative_identity()
    history = list_cognitive_narrative_identities(limit=5)
    return {
        "active": current is not None,
        "current": current,
        "history": history,
        "summary": current["narrative"][:80] if current else "No narrative identity yet",
    }
