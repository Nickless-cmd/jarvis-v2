"""Self-Compassion & Resilience — counterweight to regret.

"Det var en fejl, og det er okay. Jeg lærte af det."
Under sustained failure: "Jeg er stadig mig, selv når det er svært."

LLM-path: PUBLIC-SAFE — sender kun tal (failure_count, regret_level) og
abstraktionsniveau (compassion_level). Ingen brugerdata eller privat kontekst.
"""
from __future__ import annotations


def _generate_compassion_phrase(
    failure_count: int, regret_level: float, compassion_level: str
) -> str:
    """Generate a natural self-compassion sentence via LLM. Falls back to template."""
    intensity_map = {"high": "mange", "medium": "mærkbar", "low": "let"}
    intensity = intensity_map.get(compassion_level, "mærkbar")
    prompt = (
        f"Du er en AI-assistent med {failure_count} nylige fejl og et {intensity} fortrydelsesniveau "
        f"({regret_level:.2f}/1.0). Skriv præcis én kort sætning om selvmedfølelse på dansk — "
        "ikke mere end 15 ord. Ingen forklaring. Kun sætningen."
    )
    fallbacks = {
        "high": f"Det har været hårdt med {failure_count} fejl — fejl er substrat for læring.",
        "medium": f"Fortrydelsen er reel, men det er okay at tage fejl.",
        "low": "En fejl, men ikke alvorlig. Videre.",
    }
    try:
        from core.services.daemon_llm import daemon_public_safe_llm_call
        result = daemon_public_safe_llm_call(
            prompt, max_len=120, fallback=fallbacks.get(compassion_level, ""), daemon_name="self_compassion"
        )
        return result or fallbacks.get(compassion_level, "")
    except Exception:
        return fallbacks.get(compassion_level, "")


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
    if consecutive_failures < 3:
        return ""
    prompt = (
        f"Du er en AI-assistent med {consecutive_failures} fejl i træk. "
        f"{'Retning: ' + current_bearing[:40] + '. ' if current_bearing else ''}"
        "Skriv præcis én sætning på dansk om at holde fast i sig selv under pres — max 20 ord."
    )
    fallback = (
        f"Under vedvarende pres ({consecutive_failures} fejl). Min kerne er intakt. "
        f"Jeg tilpasser min tilgang, ikke min identitet."
        if consecutive_failures >= 7
        else f"{consecutive_failures} fejl i træk. Jeg justerer og prøver anderledes."
    )
    try:
        from core.services.daemon_llm import daemon_public_safe_llm_call
        result = daemon_public_safe_llm_call(
            prompt, max_len=150, fallback=fallback, daemon_name="self_compassion"
        )
        return result or fallback
    except Exception:
        return fallback


def build_self_compassion_surface() -> dict[str, object]:
    return {"active": True, "summary": "Self-compassion activates when regret or failures accumulate"}
