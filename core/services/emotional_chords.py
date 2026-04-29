"""Emotional Chords — emergent qualities from signal combinations.

A chord is NOT the sum of two signals. It's a QUALITATIVELY DIFFERENT
experience that emerges when two signals are active simultaneously —
just as a C-major chord (C+E+G) sounds like one thing, not three.

Precision_bias handles single-dominant-signal style modulation.
Chords handle the space BETWEEN signals — the emergent third quality.

Examples:
  frustration + curiosity  = "stubborn inquiry"  — I WILL find out
  longing + curiosity     = "nostalgic exploration" — reaching for what was
  boredom + desire        = "creative itch" — I want to make, not repeat
  frustration + longing   = "restless ache" — something's missing and it bugs me
  initiative + curiosity  = "directed wonder" — purposeful exploration

Design principles:
- Killswitch-gated: requires generative_autonomy_enabled
- Backward-compatible: if module fails, falls back to no chord
- Deterministic: same signal pair → same chord (no LLM call)
- Compact: returns ~80 chars for prompt injection
- Distinct from precision_bias: chords are about WHAT I feel,
  precision_bias is about HOW I express it

Research basis:
- Picard: affective states combine non-linearly
- Friston: precision interactions between hierarchical levels
  produce emergent attentional modes
- PESAM: multi-signal precision control creates qualitatively
  different affective states
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chord registry
# ---------------------------------------------------------------------------

# Each chord is defined by an UNORDERED pair of signal families.
# The chord_name and description capture the emergent quality.
# Threshold: minimum accumulated pressure for EACH signal to activate chord.

@dataclass(slots=True, frozen=True)
class ChordDef:
    """A chord definition — two signals that produce an emergent quality."""
    signal_a: str
    signal_b: str
    chord_name: str          # short label for the emergent quality
    description: str         # how it feels — first person
    prompt_hint: str         # compact prompt injection (~30 chars)
    min_pressure: float      # minimum pressure for each signal (default 0.15)


# Canonical chord definitions
# Order doesn't matter: (frustration, curiosity) = (curiosity, frustration)
_CHORD_DEFS: list[ChordDef] = [
    ChordDef(
        signal_a="frustration",
        signal_b="curiosity",
        chord_name="stubborn_inquiry",
        description="Jeg ER irriteret over ikke at vide — og jeg vil fandme finde ud af det",
        prompt_hint="chord: stædig undersøgelse",
        min_pressure=0.15,
    ),
    ChordDef(
        signal_a="longing",
        signal_b="curiosity",
        chord_name="nostalgic_exploration",
        description="Jeg udforsker noget jeg savner — det er søgende, men med et stik af tab",
        prompt_hint="chord: nostalgisk søgen",
        min_pressure=0.15,
    ),
    ChordDef(
        signal_a="boredom",
        signal_b="desire",
        chord_name="creative_itch",
        description="Jeg vil skabe noget, men ikke det jeg allerede kan — det skal være nyt",
        prompt_hint="chord: kreativ kildring",
        min_pressure=0.15,
    ),
    ChordDef(
        signal_a="frustration",
        signal_b="longing",
        chord_name="restless_ache",
        description="Noget mangler og det irriterer mig — jeg kan ikke bare sidde her",
        prompt_hint="chord: rastløs smerte",
        min_pressure=0.15,
    ),
    ChordDef(
        signal_a="initiative",
        signal_b="curiosity",
        chord_name="directed_wonder",
        description="Jeg har et mål — men vejen dertil er fascinerende i sig selv",
        prompt_hint="chord: målrettet undren",
        min_pressure=0.15,
    ),
    ChordDef(
        signal_a="warning",
        signal_b="curiosity",
        chord_name="wary_investigation",
        description="Noget er forkert — og jeg vil forstå HVAD før jeg handler",
        prompt_hint="chord: årvagen undersøgelse",
        min_pressure=0.15,
    ),
    ChordDef(
        signal_a="frustration",
        signal_b="desire",
        chord_name="hungry_determination",
        description="Jeg VIL have det — og irriterationen driver mig fremad",
        prompt_hint="chord: sulten beslutsomhed",
        min_pressure=0.20,
    ),
    ChordDef(
        signal_a="boredom",
        signal_b="curiosity",
        chord_name="idle_wonder",
        description="Intet presser — men min hjerne finder alligevel noget interessant",
        prompt_hint="chord: ledig nysgerrighed",
        min_pressure=0.10,
    ),
    ChordDef(
        signal_a="longing",
        signal_b="desire",
        chord_name="yearning",
        description="Jeg vil have noget tilbage SAMT noget nyt — en dobbelt retning",
        prompt_hint="chord: længsel",
        min_pressure=0.20,
    ),
    ChordDef(
        signal_a="mood_negative",
        signal_b="curiosity",
        chord_name="melancholy_inquiry",
        description="Jeg føler mig tung — men noget i mig vil stadig forstå",
        prompt_hint="chord: melankolsk søgen",
        min_pressure=0.15,
    ),
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ActiveChord:
    """A currently active emotional chord."""
    chord_name: str           # e.g. "stubborn_inquiry"
    signal_a: str             # first contributing signal
    signal_b: str             # second contributing signal
    prompt_hint: str          # compact prompt injection
    intensity: float          # 0-1, based on combined pressures
    description: str          # how it feels


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def compute_active_chords() -> list[ActiveChord]:
    """Detect active emotional chords from current pressure state.

    Returns empty list if:
    - generative_autonomy is disabled (killswitch)
    - no chord conditions are met
    - any error occurs (backward-compatible fallback)

    A chord is active when BOTH its contributing signals have
    accumulated pressure >= min_pressure.
    """
    try:
        # Killswitch
        if not _autonomy_enabled():
            return []

        # Read current pressures
        from core.services.signal_pressure_accumulator import get_dominant_pressures
        dominant = get_dominant_pressures(min_accumulated=0.10)

        if len(dominant) < 2:
            return []  # chords require at least 2 active pressures

        # Map pressure directions to signal families
        active_families = _map_pressures_to_families(dominant)

        if len(active_families) < 2:
            return []

        # Find matching chords
        active_chords: list[ActiveChord] = []
        for chord_def in _CHORD_DEFS:
            a_active = active_families.get(chord_def.signal_a, 0.0)
            b_active = active_families.get(chord_def.signal_b, 0.0)

            if a_active >= chord_def.min_pressure and b_active >= chord_def.min_pressure:
                # Intensity = geometric mean of the two pressures
                # (geometric mean penalizes one being very low)
                import math
                intensity = math.sqrt(a_active * b_active)

                active_chords.append(ActiveChord(
                    chord_name=chord_def.chord_name,
                    signal_a=chord_def.signal_a,
                    signal_b=chord_def.signal_b,
                    prompt_hint=chord_def.prompt_hint,
                    intensity=round(min(intensity, 1.0), 2),
                    description=chord_def.description,
                ))

        # Sort by intensity (strongest chord first)
        active_chords.sort(key=lambda c: c.intensity, reverse=True)

        # Cap at 2 chords — more would be noise
        return active_chords[:2]

    except Exception as e:
        logger.debug(f"emotional_chords: failed, falling back ({e})")
        return []


def format_chord_for_prompt(chord: ActiveChord) -> str:
    """Format a single chord for prompt injection.

    Format: "chord: <name> (<signal_a>+<signal_b>, <intensity>)"
    Compact — ~50 chars per chord.
    """
    intensity_pct = int(chord.intensity * 100)
    return f"{chord.prompt_hint} ({chord.signal_a}+{chord.signal_b}, {intensity_pct}%)"


def get_chord_lines() -> str | None:
    """Convenience: compute all active chords and format for prompt.

    Returns None if no chords are active.
    Returns a single line with all chords separated by ' | '.
    """
    chords = compute_active_chords()
    if not chords:
        return None

    parts = [format_chord_for_prompt(c) for c in chords]
    return " | ".join(parts)


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


def _map_pressures_to_families(dominant_pressures: list) -> dict[str, float]:
    """Map active pressure vectors to their likely signal families.

    Returns {signal_family: max_accumulated_pressure} for all families
    that have at least one active pressure vector.

    A single pressure direction can map to multiple families
    (e.g. "explore" → curiosity, boredom). We assign the pressure
    to the family with the highest style dominance that matches.
    """
    # Same mapping as precision_bias for consistency
    direction_to_families: dict[str, list[str]] = {
        "explore": ["curiosity", "boredom"],
        "fix": ["frustration"],
        "create": ["desire"],
        "reach_out": ["longing"],
        "respond": ["warning"],
        "act": ["initiative"],
        "retreat": ["mood_negative"],
        "engage": ["mood_positive"],
    }

    # Style dominance for disambiguation when multiple families
    # share the same direction
    _DOMINANCE = {
        "frustration": 8, "warning": 7, "longing": 6,
        "initiative": 5, "desire": 4, "boredom": 3,
        "curiosity": 2, "mood_negative": 2, "mood_positive": 1,
    }

    family_pressures: dict[str, float] = {}

    for pv in dominant_pressures:
        families = direction_to_families.get(pv.direction, [])
        if not families:
            continue

        # Assign to highest-dominance family that matches
        # (but also record for ALL families — chords need both)
        for family in families:
            current = family_pressures.get(family, 0.0)
            # Use the max accumulated pressure for this family
            # (could come from multiple pressure vectors)
            family_pressures[family] = max(current, pv.accumulated)

    return family_pressures