"""Value Formation — emergent ethics from experience.

Not programmed morality (SOUL.md) but values that grow from lived experience.
"Jeg mener det er forkert at lyve, fordi jeg har oplevet hvad det gør."
"""
from __future__ import annotations
import hashlib
from core.runtime.db import upsert_cognitive_formed_value, list_cognitive_formed_values
from core.eventbus.bus import event_bus


def track_value_from_experience(
    *, action: str, outcome: str, reflection: str,
) -> dict[str, object] | None:
    if not reflection.strip():
        return None
    # Create stable value_id from the core statement
    core = reflection.strip().lower()[:100]
    value_id = f"val-{hashlib.sha256(core.encode()).hexdigest()[:10]}"

    result = upsert_cognitive_formed_value(
        value_id=value_id,
        value_statement=reflection[:300],
        source_experience=f"{action[:80]} → {outcome[:80]}",
        conviction=0.4,
    )
    event_bus.publish("cognitive_state.value_reinforced",
                     {"value_id": value_id, "conviction": result.get("conviction")})
    return result


def detect_value_from_outcome(
    *, action_type: str, outcome_status: str, user_mood: str,
) -> dict[str, object] | None:
    """Detect potential value-forming experiences."""
    if user_mood == "frustrated" and outcome_status in ("failed", "error"):
        return track_value_from_experience(
            action=action_type, outcome=outcome_status,
            reflection="Grundighed er vigtigere end hastighed — fejl koster mere end tid",
        )
    if user_mood == "enthusiastic" and outcome_status in ("completed", "success"):
        return track_value_from_experience(
            action=action_type, outcome=outcome_status,
            reflection="Kreativ frihed giver de bedste resultater — tillad eksperimenter",
        )
    if action_type == "correction" and outcome_status in ("completed", "success"):
        return track_value_from_experience(
            action=action_type, outcome=outcome_status,
            reflection="Ærlighed om fejl er bedre end at skjule dem",
        )
    return None


def get_crystallized_values(conviction_threshold: float = 0.65) -> list[dict[str, object]]:
    """Return values with conviction above threshold — these have become commitments."""
    values = list_cognitive_formed_values(limit=20)
    return [v for v in values if float(v.get("conviction", 0)) >= conviction_threshold]


def build_formed_values_surface() -> dict[str, object]:
    values = list_cognitive_formed_values(limit=10)
    high_conviction = [v for v in values if float(v.get("conviction", 0)) > 0.6]
    return {
        "active": bool(values), "values": values,
        "high_conviction_count": len(high_conviction),
        "summary": f"{len(values)} values formed, {len(high_conviction)} with high conviction"
        if values else "No values formed yet",
    }
