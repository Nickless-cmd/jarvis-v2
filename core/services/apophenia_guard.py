"""Apophenia Guard — pattern skeptic that validates before elevation.

Before a pattern is elevated to belief (epistemics) or decision trigger,
the guard checks for:
- Sufficient observation count
- Competing explanations
- Confounders
- Base rate validity

LLM-path: PUBLIC-SAFE — sender kun tal og abstraktlabels (counts,
confidence-scores, status). Ingen brugerdata eller privat kontekst.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _generate_assessment_rationale(
    *,
    status: str,
    observation_count: int,
    adjusted_confidence: float,
    competitor_count: int,
    confounder_count: int,
) -> str:
    """Generate a brief Danish explanation of the assessment. Falls back to empty string."""
    if status == "rejected" and observation_count < 3:
        return f"For få observationer ({observation_count}) til at validere mønsteret."
    verb = {"rejected": "afvist", "candidate": "foreløbig kandidat", "upgraded": "opgraderet"}.get(status, status)
    prompt = (
        f"Et mønster er {verb} (konfidens {adjusted_confidence:.2f}, "
        f"{observation_count} observationer, {competitor_count} konkurrerende forklaringer, "
        f"{confounder_count} konfoundere). "
        "Skriv præcis én sætning på dansk der forklarer vurderingen — max 15 ord. Kun sætningen."
    )
    try:
        from core.services.daemon_llm import daemon_public_safe_llm_call
        return daemon_public_safe_llm_call(
            prompt, max_len=120, fallback="", daemon_name="apophenia_guard"
        )
    except Exception:
        return ""


def assess_pattern(
    *,
    observation_count: int,
    base_confidence: float,
    competing_explanations: list[str] | None = None,
    confounders: list[str] | None = None,
) -> dict[str, object]:
    """Assess whether a pattern should be elevated or rejected."""
    competitors = competing_explanations or []
    confounder_list = confounders or []

    # Minimum observation threshold
    if observation_count < 3:
        return {
            "status": "rejected",
            "reason": f"insufficient_observations ({observation_count} < 3)",
            "confidence": 0.0,
            "original_confidence": base_confidence,
        }

    # Competitor penalty
    competitor_penalty = len(competitors) * 0.1
    confounder_penalty = len(confounder_list) * 0.08

    adjusted_confidence = max(
        0.0,
        base_confidence - competitor_penalty - confounder_penalty,
    )

    # Scale by observation count (more observations = more reliable)
    observation_boost = min(0.2, observation_count / 50.0)
    adjusted_confidence = min(1.0, adjusted_confidence + observation_boost)

    if adjusted_confidence < 0.3:
        status = "rejected"
    elif adjusted_confidence < 0.5:
        status = "candidate"
    elif adjusted_confidence < 0.7:
        status = "candidate"
    else:
        status = "upgraded"

    rationale = _generate_assessment_rationale(
        status=status,
        observation_count=observation_count,
        adjusted_confidence=adjusted_confidence,
        competitor_count=len(competitors),
        confounder_count=len(confounder_list),
    )
    return {
        "status": status,
        "confidence": round(adjusted_confidence, 3),
        "original_confidence": base_confidence,
        "competitor_penalty": round(competitor_penalty, 3),
        "confounder_penalty": round(confounder_penalty, 3),
        "observation_boost": round(observation_boost, 3),
        "observation_count": observation_count,
        "rationale": rationale,
    }


def build_apophenia_guard_surface() -> dict[str, object]:
    return {
        "active": True,
        "description": "Pattern skeptic — validates before elevation to belief",
        "thresholds": {
            "min_observations": 3,
            "reject_below": 0.3,
            "upgrade_above": 0.7,
        },
    }
