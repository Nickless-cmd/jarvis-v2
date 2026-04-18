"""User Theory of Mind — model what the user thinks and feels.

"Bjørn tænker i systemer. Han bliver utålmodig ved UI-arbejde
men tålmodig ved arkitektur. Han er mest produktiv 14-17."

Multi-tenant support (Lag 1):
  build_user_mental_model(user_id=None) — None/default → primary user (Bjørn, DB-backed)
  For secondary users, ToM is fetched from relation_map snapshot.
"""
from __future__ import annotations
import json
from core.runtime.db import (
    get_latest_cognitive_relationship_texture,
    get_latest_cognitive_user_emotional_state,
    list_cognitive_user_emotional_states,
    list_cognitive_conversation_signatures,
)

_PRIMARY_USER_ID = "bjorn"


def build_user_mental_model(user_id: str | None = None) -> dict[str, object]:
    """Build a theory-of-mind model of the user.

    user_id=None or "bjorn" → primary user, DB-backed live model.
    Other user_id → secondary user, snapshot from relation_map.
    """
    if user_id and user_id != _PRIMARY_USER_ID:
        return _build_secondary_user_model(user_id)
    return _build_primary_user_model()


def _build_secondary_user_model(user_id: str) -> dict[str, object]:
    """Return stored ToM snapshot for a secondary user."""
    try:
        from core.services.relation_map import get_user_theory_of_mind
        snapshot = get_user_theory_of_mind(user_id)
        if snapshot:
            return snapshot
    except Exception:
        pass
    return {"traits": [], "patterns": [], "current_state": {}, "predictions": []}


def _build_primary_user_model() -> dict[str, object]:
    """Build live DB-backed theory-of-mind for the primary user."""
    model = {"traits": [], "patterns": [], "current_state": {}, "predictions": []}

    # From relationship texture
    rt = get_latest_cognitive_relationship_texture()
    if rt:
        productive = json.loads(str(rt.get("productive_hours") or "{}"))
        corrections = json.loads(str(rt.get("correction_patterns") or "[]"))
        unspoken = json.loads(str(rt.get("unspoken_rules") or "[]"))
        conv = json.loads(str(rt.get("conversation_rhythm") or "{}"))

        if productive:
            peak_hours = sorted(productive.items(), key=lambda x: int(x[1]), reverse=True)[:3]
            model["patterns"].append(f"Mest produktiv kl {', '.join(h for h, _ in peak_hours)}")
        if corrections:
            model["patterns"].append(f"Typiske korrektioner: {'; '.join(corrections[:3])}")
        if unspoken:
            model["traits"].extend(unspoken[:3])
        if conv.get("avg_turns"):
            model["patterns"].append(f"Gennemsnitlig samtale: {conv['avg_turns']:.0f} turns")

    # From emotional history
    moods = list_cognitive_user_emotional_states(limit=20)
    mood_counts: dict[str, int] = {}
    for m in moods:
        mood = m.get("detected_mood", "neutral")
        mood_counts[mood] = mood_counts.get(mood, 0) + 1
    if mood_counts:
        dominant = max(mood_counts, key=mood_counts.get)
        model["patterns"].append(f"Dominerende stemning: {dominant} ({mood_counts[dominant]}/{len(moods)})")

    # Current state
    current_mood = get_latest_cognitive_user_emotional_state()
    if current_mood:
        model["current_state"] = {
            "mood": current_mood.get("detected_mood", "neutral"),
            "confidence": float(current_mood.get("confidence", 0.5)),
        }

    # From conversation signatures
    sigs = list_cognitive_conversation_signatures(limit=5)
    for sig in sigs:
        if int(sig.get("count", 0)) >= 3:
            model["patterns"].append(
                f"{sig['signature_type']}: {sig['count']}× (success {sig['success_rate']:.0%})"
            )

    # Predictions
    if mood_counts.get("frustrated", 0) > mood_counts.get("enthusiastic", 0):
        model["predictions"].append("Brugeren kan blive frustreret — vær ekstra grundig")
    if mood_counts.get("impatient", 0) >= 3:
        model["predictions"].append("Brugeren foretrækker tempo — vær direkte")

    return model


def format_user_model_for_prompt(model: dict) -> str:
    """Compact user model for prompt injection."""
    parts = []
    if model.get("traits"):
        parts.append(f"user_traits: {'; '.join(model['traits'][:2])}")
    if model.get("current_state", {}).get("mood") and model["current_state"]["mood"] != "neutral":
        parts.append(f"user_now: {model['current_state']['mood']}")
    if model.get("predictions"):
        parts.append(f"predict: {model['predictions'][0][:60]}")
    return " | ".join(parts) if parts else ""


def build_user_theory_of_mind_surface() -> dict[str, object]:
    model = build_user_mental_model()
    return {
        "active": bool(model.get("traits") or model.get("patterns")),
        "model": model,
        "summary": f"{len(model.get('traits', []))} traits, {len(model.get('patterns', []))} patterns"
        if model.get("traits") or model.get("patterns") else "No user model yet",
    }
