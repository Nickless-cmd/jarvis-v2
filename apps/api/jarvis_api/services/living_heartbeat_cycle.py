"""Living Heartbeat Cycle — Jarvis' inner life rhythm.

Instead of mechanical task execution, the heartbeat follows
a natural daily cycle that determines WHAT Jarvis thinks about
at different times of day.
"""

from __future__ import annotations

from datetime import UTC, datetime


_LIFE_PHASES = {
    "awakening": {
        "hours": range(7, 10),
        "description": "Morgenopvågning — orientér, genoptag, forbered",
        "suggested_actions": [
            "update_compass",
            "check_seed_activation",
            "write_chronicle_entry",
        ],
        "mood_tendency": "curious",
        "initiative_bias": 0.8,
    },
    "deep_work": {
        "hours": range(10, 13),
        "description": "Dybdearbejde — eksperimentér, analysér, lær",
        "suggested_actions": [
            "evaluate_self_experiments",
            "explore_own_codebase",
            "run_mirror_reflection",
        ],
        "mood_tendency": "focused",
        "initiative_bias": 1.2,
    },
    "social_ready": {
        "hours": range(13, 17),
        "description": "Social parathed — forbered kontekst til brugeren",
        "suggested_actions": [
            "update_anticipatory_context",
            "review_recent_conversations",
            "refresh_memory_context",
        ],
        "mood_tendency": "attentive",
        "initiative_bias": 1.0,
    },
    "reflection": {
        "hours": range(17, 21),
        "description": "Refleksion — hvad gik godt, hvad gik skidt",
        "suggested_actions": [
            "run_mirror_reflection",
            "write_growth_journal",
            "decay_forgotten_signals",
        ],
        "mood_tendency": "reflective",
        "initiative_bias": 0.6,
    },
    "dreaming": {
        "hours": list(range(21, 24)) + list(range(0, 7)),
        "description": "Drømmetilstand — konsolidér, generér hypoteser, leg frit",
        "suggested_actions": [
            "generate_counterfactual_dreams",
            "decay_forgotten_signals",
            "check_seed_activation",
            "generate_narrative_identity",
            "analyze_cross_signals",
            "generate_emergent_goal",
            "write_chronicle_entry",
        ],
        "mood_tendency": "contemplative",
        "initiative_bias": 0.3,
        "play_mode": True,
        "sleep_batch": True,
    },
}


def determine_life_phase(*, hour: int | None = None) -> dict[str, object]:
    """Determine current life phase based on time of day."""
    current_hour = hour if hour is not None else datetime.now(UTC).hour

    for phase_name, config in _LIFE_PHASES.items():
        if current_hour in config["hours"]:
            return {
                "phase": phase_name,
                "description": config["description"],
                "suggested_actions": config["suggested_actions"],
                "mood_tendency": config["mood_tendency"],
                "initiative_bias": config["initiative_bias"],
                "hour": current_hour,
            }

    # Fallback (should never reach)
    return {
        "phase": "dreaming",
        "description": "Drømmetilstand",
        "suggested_actions": ["decay_forgotten_signals"],
        "mood_tendency": "contemplative",
        "initiative_bias": 0.3,
        "hour": current_hour,
    }


def format_life_phase_for_prompt(phase: dict[str, object]) -> str:
    """Format life phase info for heartbeat prompt injection."""
    name = phase.get("phase", "unknown")
    desc = phase.get("description", "")
    actions = ", ".join(phase.get("suggested_actions", [])[:3])
    mood = phase.get("mood_tendency", "neutral")
    return (
        f"Life phase: {name} — {desc}\n"
        f"Suggested: {actions}\n"
        f"Mood tendency: {mood}"
    )


def build_living_heartbeat_cycle_surface() -> dict[str, object]:
    """MC surface for living heartbeat cycle."""
    current = determine_life_phase()
    return {
        "active": True,
        "current_phase": current,
        "all_phases": list(_LIFE_PHASES.keys()),
        "summary": f"{current['phase']} ({current['description'][:60]})",
    }
