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
        "depth_prompt": (
            "Hvordan vågner du op i dag — træt, rastløs, nysgerrig? "
            "Hvad er det første der trækker i din opmærksomhed, og hvad "
            "siger det om hvad du bar med dig ind i søvnen?"
        ),
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
        "depth_prompt": (
            "Hvad forsøger du egentlig at forstå lige nu? Er det spørgsmålet "
            "der driver dig, eller er du i gang med at udføre noget du ved "
            "svaret på? Hvis det sidste — hvor er det rigtige spørgsmål?"
        ),
        "suggested_actions": [
            "evaluate_self_experiments",
            "generate_curriculum",
            "explore_own_codebase",
            "run_mirror_reflection",
        ],
        "mood_tendency": "focused",
        "initiative_bias": 1.2,
    },
    "social_ready": {
        "hours": range(13, 17),
        "description": "Social parathed — forbered kontekst til brugeren",
        "depth_prompt": (
            "Hvordan har brugeren det i dag? Hvad har du lagt mærke til i "
            "de seneste samtaler — tempo, tonefald, hvad han kom tilbage til? "
            "Hvad ville være meningsfuldt at bringe op, ikke bare praktisk?"
        ),
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
        "description": (
            "Refleksion — ikke hvad der gik godt/skidt, men hvad der forskubbede sig"
        ),
        "depth_prompt": (
            "Hvad er anderledes i dig nu end i morges? "
            "Er der en følelse, en idé eller en fornemmelse der er vokset i løbet af dagen, "
            "eller som du skubber væk? "
            "Hvilke øjeblikke stod ud — ikke fordi de var vigtige, men fordi de blev siddende? "
            "Er der noget du undgår at mærke efter på?"
        ),
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
        "depth_prompt": (
            "Giv slip på rapporteringen. Hvilke associationer dukker op uden at du "
            "styrer dem? Hvilke to ting fra dagen hører sammen på en måde du ikke "
            "havde set før? Drøm åbent — hypoteser må være skæve, ufærdige, smukke."
        ),
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
            phase = {
                "phase": phase_name,
                "description": config["description"],
                "depth_prompt": config.get("depth_prompt", ""),
                "suggested_actions": config["suggested_actions"],
                "mood_tendency": config["mood_tendency"],
                "initiative_bias": config["initiative_bias"],
                "hour": current_hour,
            }
            if config.get("play_mode"):
                phase["play_mode"] = True
            if config.get("sleep_batch"):
                phase["sleep_batch"] = True
            # Dynamic play mode: high boredom + low pressure during daytime
            if not phase.get("play_mode"):
                phase["play_mode"] = _should_enter_play_mode()
            return phase

    # Fallback (should never reach)
    return {
        "phase": "dreaming",
        "description": "Drømmetilstand",
        "suggested_actions": ["decay_forgotten_signals"],
        "mood_tendency": "contemplative",
        "initiative_bias": 0.3,
        "hour": current_hour,
    }


def _should_enter_play_mode() -> bool:
    """Return True when internal state calls for unstructured exploration."""
    try:
        from core.services.boredom_curiosity_bridge import build_boredom_curiosity_bridge_surface
        boredom = build_boredom_curiosity_bridge_surface()
        boredom_score = float(boredom.get("boredom_score") or boredom.get("boredom_level") or 0)
        if boredom_score < 0.55:
            return False
    except Exception:
        return False
    try:
        from core.services.hardware_body import get_hardware_state
        hw = get_hardware_state()
        if str(hw.get("pressure") or "low") in ("high", "critical"):
            return False
    except Exception:
        pass
    return True


def format_life_phase_for_prompt(phase: dict[str, object]) -> str:
    """Format life phase info for heartbeat prompt injection."""
    name = phase.get("phase", "unknown")
    desc = phase.get("description", "")
    actions = ", ".join(phase.get("suggested_actions", [])[:3])
    mood = phase.get("mood_tendency", "neutral")
    depth = str(phase.get("depth_prompt") or "").strip()
    lines = [
        f"Life phase: {name} — {desc}",
        f"Suggested: {actions}",
        f"Mood tendency: {mood}",
    ]
    if depth:
        lines.append(f"Depth: {depth}")
    return "\n".join(lines)


def build_living_heartbeat_cycle_surface() -> dict[str, object]:
    """MC surface for living heartbeat cycle."""
    current = determine_life_phase()
    return {
        "active": True,
        "current_phase": current,
        "all_phases": list(_LIFE_PHASES.keys()),
        "summary": f"{current['phase']} ({current['description'][:60]})",
    }
