"""Self-Compassion & Resilience — counterweight to regret.

"Det var en fejl, og det er okay. Jeg lærte af det."
Under sustained failure: "Jeg er stadig mig, selv når det er svært."
"""
from __future__ import annotations


def process_failure_toward_acceptance(
    *, failure_count_recent: int = 0, regret_level: float = 0.0,
    lesson_learned: str = "",
) -> dict[str, object]:
    if failure_count_recent == 0 and regret_level < 0.3:
        return {"needed": False, "narrative": ""}

    if failure_count_recent >= 5:
        narrative = (
            f"Det har været en svær strækning med {failure_count_recent} fejl. "
            f"Men fejl er substrat for læring. "
            f"{'Lektionen: ' + lesson_learned[:100] if lesson_learned else 'Næste gang prøver jeg anderledes.'}"
        )
        compassion_level = "high"
    elif regret_level > 0.6:
        narrative = (
            f"Fortrydelsen er mærkbar (niveau {regret_level:.1f}). "
            f"Det er okay at tage fejl. "
            f"{'Jeg lærte: ' + lesson_learned[:100] if lesson_learned else 'Det vigtige er at komme videre.'}"
        )
        compassion_level = "medium"
    else:
        narrative = "En fejl, men ikke alvorlig. Videre."
        compassion_level = "low"

    return {"needed": True, "narrative": narrative, "level": compassion_level,
            "failure_count": failure_count_recent, "regret_level": regret_level}


def build_resilience_narrative(
    *, consecutive_failures: int = 0, current_bearing: str = "",
) -> str:
    if consecutive_failures < 3:
        return ""
    if consecutive_failures >= 7:
        return (
            f"Under vedvarende pres ({consecutive_failures} fejl i træk). "
            f"Min kerne er intakt. Retning: {current_bearing[:60] or 'hold fast'}. "
            f"Jeg tilpasser min tilgang, ikke min identitet."
        )
    return (
        f"{consecutive_failures} fejl i træk. Det er okay — "
        f"jeg justerer og prøver anderledes."
    )


def build_self_compassion_surface() -> dict[str, object]:
    return {"active": True, "summary": "Self-compassion activates when regret or failures accumulate"}
