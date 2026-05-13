"""Self-Compassion & Resilience — counterweight to regret.

"Det var en fejl, og det er okay. Jeg lærte af det."
Under sustained failure: "Jeg er stadig mig, selv når det er svært."

LLM-path: PUBLIC-SAFE — sender kun tal (failure_count, regret_level) og
abstraktionsniveau (compassion_level). Ingen brugerdata eller privat kontekst.
"""
from __future__ import annotations


def _compassion_label(failure_count: int, regret_level: float, compassion_level: str) -> str:
    """Return a descriptive state label, not a self-compassion sentence.

    Teater-pass 2026-05-13: this used to call cheap-lane with "Skriv præcis
    én sætning om selvmedfølelse på dansk" — generating self-compassion on
    command isn't self-compassion. The label below is just a stat for
    Jarvis to read; he forms (or doesn't form) his own response if it
    surfaces in awareness.
    """
    return (
        f"regret_band={compassion_level} "
        f"failures_recent={failure_count} "
        f"regret_level={regret_level:.2f}"
    )


# Legacy alias — existing callers use _generate_compassion_phrase
_generate_compassion_phrase = _compassion_label


def process_failure_toward_acceptance(
    *, failure_count_recent: int = 0, regret_level: float = 0.0,
    lesson_learned: str = "",
) -> dict[str, object]:
    if failure_count_recent == 0 and regret_level < 0.3:
        return {"needed": False, "narrative": ""}

    if failure_count_recent >= 5:
        compassion_level = "high"
    elif regret_level > 0.6:
        compassion_level = "medium"
    else:
        compassion_level = "low"

    narrative = _generate_compassion_phrase(failure_count_recent, regret_level, compassion_level)

    # Append lesson if provided (truncated, appended locally — never sent to LLM)
    if lesson_learned and compassion_level != "low":
        narrative = f"{narrative} Lektionen: {lesson_learned[:80]}"

    return {"needed": True, "narrative": narrative, "level": compassion_level,
            "failure_count": failure_count_recent, "regret_level": regret_level}


def build_resilience_narrative(
    *, consecutive_failures: int = 0, current_bearing: str = "",
) -> str:
    """Return a descriptive resilience-state label.

    Teater-pass 2026-05-13: previously asked cheap-lane to "Skriv præcis
    én sætning på dansk om at holde fast i sig selv under pres" — pure
    confabulation. Now returns a stat band. Jarvis sees the band in
    awareness; he forms (or skips) his own response.
    """
    if consecutive_failures < 3:
        return ""
    band = "sustained" if consecutive_failures >= 7 else "moderate"
    bearing_str = f", bearing={current_bearing[:40]}" if current_bearing else ""
    return (
        f"resilience_pressure_band={band} "
        f"consecutive_failures={consecutive_failures}{bearing_str}"
    )


def build_self_compassion_surface() -> dict[str, object]:
    return {"active": True, "summary": "Self-compassion activates when regret or failures accumulate"}
