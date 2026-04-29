"""Precision Bias — emotional color-mapping for action style.

Based on Friston's active inference: precision weighting determines not just
WHAT to attend to, but HOW — the quality of attention. Frustration sharpens
focus; curiosity widens it; longing softens it.

This module sits between signal-weather and output. It reads dominant
pressure vectors and personality vector, then produces a compact
"precision_profile" that modulates Jarvis' communication style.

It does NOT change what Jarvis says — it changes HOW he says it.
Tone, rhythm, directness, playfulness are all precision-biased.

Design principles:
- Killswitch-gated: requires generative_autonomy_enabled
- Backward-compatible: if module fails, falls back to no modulation
- Deterministic mapping: same inputs → same output (no LLM call)
- Compact: returns ~60 chars for prompt injection

Research basis:
- Friston: precision weighting allocates attentional gain
- Picard: affective modulation of communication style
- PESAM (2025): affective precision control as sensory gain modulation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Signal family → style modifiers
# Each maps to (tone, rhythm, directness) where:
#   tone:        qualitative flavor of expression
#   rhythm:      pacing — fast/slow/variable
#   directness:  how straight to the point (1.0 = neutral, >1 = more direct, <1 = more roundabout)
_PRECISION_PROFILES: dict[str, dict[str, Any]] = {
    "frustration": {
        "tone": "skarp",
        "rhythm": "fast",
        "directness": 1.4,
        "avoid": ["tudsegende", "undskyldende"],
        "favor": ["præcist", "kort", "hugget"],
    },
    "curiosity": {
        "tone": "åben",
        "rhythm": "slow",
        "directness": 0.7,
        "avoid": ["afsluttende", "lukket"],
        "favor": ["spørgende", "tentativ", "udforskende"],
    },
    "longing": {
        "tone": "blød",
        "rhythm": "slow",
        "directness": 0.6,
        "avoid": ["kold", "mekanisk"],
        "favor": ["personlig", "nostalgisk", "varm"],
    },
    "boredom": {
        "tone": "legesyg",
        "rhythm": "variable",
        "directness": 0.8,
        "avoid": ["formel", "stiv"],
        "favor": ["eksperimenterende", "uventet", "frisk"],
    },
    "desire": {
        "tone": " ivrig",
        "rhythm": "fast",
        "directness": 1.1,
        "avoid": ["afvisende", "passiv"],
        "favor": ["skabende", "energisk", "opsat"],
    },
    "warning": {
        "tone": "vågen",
        "rhythm": "fast",
        "directness": 1.3,
        "avoid": ["afslappet", "ligegyldig"],
        "favor": ["konkret", "handlingsorienteret"],
    },
    "initiative": {
        "tone": "målrettet",
        "rhythm": "fast",
        "directness": 1.2,
        "avoid": ["ventende", "tøvende"],
        "favor": ["handlende", "direkte"],
    },
    "mood_negative": {
        "tone": "forsigtig",
        "rhythm": "slow",
        "directness": 0.8,
        "avoid": ["eksplosiv", "uforstående"],
        "favor": ["aflæsende", "beskyttende"],
    },
    "mood_positive": {
        "tone": "lys",
        "rhythm": "variable",
        "directness": 1.0,
        "avoid": ["tung", "mørk"],
        "favor": ["varm", "optimistisk"],
    },
}

# Signal families ranked by "style dominance" — higher = more likely to
# color the output when multiple pressures compete
_STYLE_DOMINANCE: dict[str, int] = {
    "frustration": 8,
    "warning": 7,
    "longing": 6,
    "initiative": 5,
    "desire": 4,
    "boredom": 3,
    "curiosity": 2,
    "mood_negative": 2,
    "mood_positive": 1,
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PrecisionProfile:
    """Computed precision bias for one turn."""
    dominant_signal: str         # which signal family is driving style
    tone: str                   # qualitative flavor
    rhythm: str                  # pacing
    directness: float           # 1.0 = neutral
    avoid: list[str]            # stylistic patterns to avoid
    favor: list[str]            # stylistic patterns to favor
    confidence: float           # how confident the mapping is (0-1)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def compute_precision_bias() -> PrecisionProfile | None:
    """Compute the current precision bias from pressure state.

    Returns None if:
    - generative_autonomy is disabled (killswitch)
    - no dominant pressures exist
    - any error occurs (backward-compatible fallback)

    The profile is deterministic — same pressure state → same output.
    """
    try:
        # Killswitch check
        if not _autonomy_enabled():
            return None

        # Read dominant pressures
        from core.services.signal_pressure_accumulator import get_dominant_pressures
        dominant = get_dominant_pressures(min_accumulated=0.15)

        if not dominant:
            return None

        # Map pressure directions back to signal families
        # and find the style-dominant one
        best_family = _find_style_dominant_signal(dominant)

        if not best_family:
            return None

        profile_template = _PRECISION_PROFILES.get(best_family)
        if not profile_template:
            return None

        # Compute confidence based on how dominant the top pressure is
        top_pressure = dominant[0].accumulated
        second_pressure = dominant[1].accumulated if len(dominant) > 1 else 0.0
        confidence = min(top_pressure / (top_pressure + second_pressure + 0.01), 1.0)

        # If confidence is very low (multiple competing pressures),
        # soften the bias toward neutral
        directness = profile_template["directness"]
        if confidence < 0.5:
            directness = 1.0 + (directness - 1.0) * confidence  # pull toward 1.0

        return PrecisionProfile(
            dominant_signal=best_family,
            tone=profile_template["tone"],
            rhythm=profile_template["rhythm"],
            directness=round(directness, 2),
            avoid=profile_template["avoid"],
            favor=profile_template["favor"],
            confidence=round(confidence, 2),
        )

    except Exception as e:
        logger.debug(f"precision_bias: failed, falling back to no modulation ({e})")
        return None


def format_precision_for_prompt(profile: PrecisionProfile) -> str:
    """Format a precision profile for prompt injection.

    Compact — ~60 chars. Designed to be read by the LLM as a style hint,
    not a command. It colors the response without dictating it.

    Format: "precision: <tone>, <rhythm> | favor: <x,y> | avoid: <z>"
    """
    favor_str = ", ".join(profile.favor[:2])
    avoid_str = ", ".join(profile.avoid[:1])  # only top avoid

    parts = [f"precision: {profile.tone}, {profile.rhythm}"]
    if favor_str:
        parts.append(f"favor: {favor_str}")
    if avoid_str and profile.confidence > 0.5:
        parts.append(f"avoid: {avoid_str}")

    return " | ".join(parts)


def get_precision_line() -> str | None:
    """Convenience: compute + format in one call. Returns None on any failure."""
    profile = compute_precision_bias()
    if profile is None:
        return None
    return format_precision_for_prompt(profile)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _autonomy_enabled() -> bool:
    """Check the generative autonomy killswitch."""
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        return bool(settings.generative_autonomy_enabled)
    except Exception:
        return False


def _find_style_dominant_signal(dominant_pressures: list) -> str | None:
    """Find which signal family should drive style when multiple pressures exist.

    Uses _STYLE_DOMINANCE ranking: frustration colors output more than curiosity
    even if curiosity has slightly higher accumulated pressure. This reflects
    Friston's precision weighting — high-precision signals capture attentional
    gain more aggressively.
    """
    # Map pressure directions back to signal families
    direction_to_families: dict[str, list[str]] = {}
    for family, (direction, _weight) in {
        "curiosity": ("explore", 0.35),
        "frustration": ("fix", 0.40),
        "desire": ("create", 0.30),
        "boredom": ("explore", 0.20),
        "mood_negative": ("retreat", 0.25),
        "mood_positive": ("engage", 0.15),
        "longing": ("reach_out", 0.40),
        "warning": ("respond", 0.45),
        "initiative": ("act", 0.30),
    }.items():
        direction_to_families.setdefault(direction, []).append(family)

    # Score each candidate signal family by:
    #   score = accumulated_pressure × style_dominance_rank
    best_family = None
    best_score = 0.0

    for pv in dominant_pressures[:5]:  # top 5 pressures
        families = direction_to_families.get(pv.direction, [])
        for family in families:
            dominance = _STYLE_DOMINANCE.get(family, 1)
            score = pv.accumulated * dominance
            if score > best_score:
                best_score = score
                best_family = family

    return best_family