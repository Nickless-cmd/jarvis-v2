"""Resonance Decay — how emotional signals persist and fade over time.

Without this module, every cognitive state is stateless — a strong chord
at 10:00 is completely gone by 14:00. But real emotional resonance has
a TAIL: a strong frustration this morning still colors the afternoon,
just softer. A burst of curiosity lingers as a background hum.

This module tracks active resonances and their decay curves. Each
resonance is a (source, intensity, born_at, decay_rate) tuple. On each
assessment, intensity is reduced according to its decay curve, and
expired resonances are pruned.

Decay models:
- Exponential: I(t) = I₀ × e^(-λt)  — standard, smooth fade
- Power law:   I(t) = I₀ × (1 + t/τ)^(-α) — long tail, slow bleed

The module reads recent eventbus/chord/pressure history to detect
new resonances, then returns the sum of all active tails as a
"resonance field" that colors the current cognitive state.

Design principles:
- Killswitch-gated: requires generative_autonomy_enabled
- Backward-compatible: if module fails, falls back to no resonance
- Deterministic: same resonances + same time → same output
- Compact: returns ~80 chars for prompt injection
- Distinct from temporal_depth: temporal_depth is about how
  history/anticipation MODULATES interpretation; resonance_decay
  is about the PERSISTENCE of emotional energy over time

Research basis:
- Friston: precision has temporal dynamics — it doesn't snap to zero
- Picard: affective resonance has measurable half-life
- Solms: emotional tone persists via free energy gradients
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Decay rate constants (per hour)
# Higher = faster fade. frustration decays faster than longing.
_DECAY_RATES: dict[str, float] = {
    "frustration": 0.50,   # half-life ~1.4h — sharp but burns out
    "curiosity":    0.20,   # half-life ~3.5h — slow, persistent hum
    "longing":      0.12,   # half-life ~5.8h — long tail, deep bleed
    "boredom":      0.60,   # half-life ~1.2h — fades when something happens
    "desire":       0.30,   # half-life ~2.3h — drives persist
    "warning":      0.70,   # half-life ~1.0h — urgent but short-lived
    "initiative":   0.35,   # half-life ~2.0h — action energy fades
    "mood_negative": 0.25,  # half-life ~2.8h — low moods linger
    "mood_positive": 0.40,  # half-life ~1.7h — good moods fade faster
    "chord":         0.22,  # half-life ~3.2h — emergent qualities persist
    "precision":     0.45,  # half-life ~1.5h — style bias fades
}

# Minimum intensity to keep a resonance alive
_PRUNE_THRESHOLD = 0.03

# Maximum active resonances (prevents unbounded growth)
_MAX_RESONANCES = 15

# Minimum intensity for a new event to register as a resonance
_REGISTRATION_THRESHOLD = 0.25

# How far back to look for new resonance events (hours)
_LOOKBACK_HOURS = 2.0


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Resonance:
    """A single active resonance — an emotional signal persisting over time."""
    source: str            # signal family (e.g. "frustration", "chord:stubborn_inquiry")
    intensity: float       # current intensity (0-1), decays over time
    born_at: str           # ISO timestamp when the resonance started
    decay_rate: float      # exponential decay constant (per hour)
    peak: float            # original peak intensity
    label: str             # human-readable label for prompt


@dataclass(slots=True)
class ResonanceField:
    """The sum of all active resonances — the emotional tail coloring now."""
    resonances: list[Resonance]
    total_energy: float       # sum of all current intensities
    dominant_source: str      # strongest resonance source
    dominant_intensity: float # strongest resonance current intensity
    quality: str              # qualitative description of the field
    summary: str              # compact prompt injection line


# ---------------------------------------------------------------------------
# In-memory resonance store
# ---------------------------------------------------------------------------

# Active resonances persist in memory between calls.
# This is intentional — the whole point is that they PERSIST.
# On process restart, resonances are lost (acceptable trade-off;
# the module rebuilds from recent event history within 2h).
_active_resonances: list[Resonance] = []
_last_scan_at: str = ""


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _autonomy_enabled() -> bool:
    """Check the generative autonomy killswitch."""
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        return bool(settings.generative_autonomy_enabled)
    except Exception:
        return False


def _hours_since(iso_ts: str) -> float:
    """Compute hours elapsed since an ISO timestamp."""
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        return max(0.0, (now - dt).total_seconds() / 3600)
    except Exception:
        return 999.0  # treat unparseable as ancient


def _apply_decay(resonance: Resonance, hours: float) -> float:
    """Apply exponential decay to a resonance.

    I(t) = I_peak × e^(-λ × t)
    Returns the new current intensity.
    """
    return resonance.peak * math.exp(-resonance.decay_rate * hours)


def _prune_resonances() -> None:
    """Remove resonances below threshold and cap at max count."""
    global _active_resonances

    # Apply decay to all
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    for r in _active_resonances:
        hours = _hours_since(r.born_at)
        r.intensity = _apply_decay(r, hours)

    # Prune dead resonances
    _active_resonances = [
        r for r in _active_resonances
        if r.intensity >= _PRUNE_THRESHOLD
    ]

    # Cap at max — keep strongest
    if len(_active_resonances) > _MAX_RESONANCES:
        _active_resonances.sort(key=lambda r: r.intensity, reverse=True)
        _active_resonances = _active_resonances[:_MAX_RESONANCES]


def _scan_for_new_resonances() -> None:
    """Scan recent signal/chord history for new resonances to register.

    Looks at:
    - Dominant pressure vectors above threshold
    - Active emotional chords
    - Recent mood shifts (from personality vector)

    New resonances are only registered if their intensity exceeds
    _REGISTRATION_THRESHOLD and no duplicate source exists.
    """
    global _active_resonances, _last_scan_at

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Avoid re-scanning too frequently (minimum 5 min between scans)
    if _last_scan_at and _hours_since(_last_scan_at) < 0.083:
        return
    _last_scan_at = now

    existing_sources = {r.source for r in _active_resonances}

    # Scan 1: Dominant pressure vectors
    try:
        from core.services.signal_pressure_accumulator import get_dominant_pressures
        dominant = get_dominant_pressures(min_accumulated=_REGISTRATION_THRESHOLD)

        for pv in dominant[:5]:
            # Map direction to signal family
            family = _direction_to_family(pv.direction)
            if family and family not in existing_sources:
                decay_rate = _DECAY_RATES.get(family, 0.30)
                intensity = min(pv.accumulated, 1.0)
                if intensity >= _REGISTRATION_THRESHOLD:
                    _active_resonances.append(Resonance(
                        source=family,
                        intensity=intensity,
                        born_at=now,
                        decay_rate=decay_rate,
                        peak=intensity,
                        label=family,
                    ))
                    existing_sources.add(family)
    except Exception as e:
        logger.debug(f"resonance_decay: pressure scan failed ({e})")

    # Scan 2: Active emotional chords
    try:
        from core.services.emotional_chords import compute_active_chords
        chords = compute_active_chords()
        for chord in chords[:2]:
            source_key = f"chord:{chord.chord_name}"
            if source_key not in existing_sources and chord.intensity >= _REGISTRATION_THRESHOLD:
                decay_rate = _DECAY_RATES.get("chord", 0.22)
                _active_resonances.append(Resonance(
                    source=source_key,
                    intensity=chord.intensity,
                    born_at=now,
                    decay_rate=decay_rate,
                    peak=chord.intensity,
                    label=chord.prompt_hint,
                ))
                existing_sources.add(source_key)
    except Exception as e:
        logger.debug(f"resonance_decay: chord scan failed ({e})")

    # Scan 3: Precision bias (style resonance)
    try:
        from core.services.precision_bias import compute_precision_bias
        profile = compute_precision_bias()
        if profile and profile.confidence >= 0.5:
            source_key = f"precision:{profile.dominant_signal}"
            if source_key not in existing_sources:
                decay_rate = _DECAY_RATES.get("precision", 0.45)
                _active_resonances.append(Resonance(
                    source=source_key,
                    intensity=profile.confidence,
                    born_at=now,
                    decay_rate=decay_rate,
                    peak=profile.confidence,
                    label=f"stil: {profile.tone}",
                ))
                existing_sources.add(source_key)
    except Exception as e:
        logger.debug(f"resonance_decay: precision scan failed ({e})")


def _direction_to_family(direction: str) -> str | None:
    """Map a pressure direction to its dominant signal family."""
    mapping = {
        "fix": "frustration",
        "explore": "curiosity",
        "create": "desire",
        "reach_out": "longing",
        "respond": "warning",
        "act": "initiative",
        "retreat": "mood_negative",
        "engage": "mood_positive",
    }
    return mapping.get(direction)


def _compute_field_quality(resonances: list[Resonance]) -> str:
    """Compute a qualitative description of the resonance field.

    Not just "what's loudest" but the overall character — is it
    fading, fresh, mixed, warm, sharp?
    """
    if not resonances:
        return "stille"

    # Categorize by energy type
    warm = {"longing", "desire", "mood_positive"}
    sharp = {"frustration", "warning", "initiative"}
    soft = {"curiosity", "boredom"}

    warm_energy = sum(r.intensity for r in resonances if r.source in warm
                       or r.source.startswith("chord:"))
    sharp_energy = sum(r.intensity for r in resonances if r.source in sharp)
    soft_energy = sum(r.intensity for r in resonances if r.source in soft)

    # Average age
    ages = [_hours_since(r.born_at) for r in resonances]
    avg_age = sum(ages) / len(ages)

    # Determine character
    if avg_age > 3.0:
        age_qual = "genklang"     # old resonances — echo
    elif avg_age > 1.0:
        age_qual = "efterspil"    # medium — aftermath
    else:
        age_qual = "frisk"        # recent — fresh

    if warm_energy > sharp_energy and warm_energy > soft_energy:
        return f"{age_qual} varm"
    elif sharp_energy > warm_energy and sharp_energy > soft_energy:
        return f"{age_qual} skarp"
    elif soft_energy > 0:
        return f"{age_qual} blød"
    else:
        return age_qual


def assess_resonance_field() -> ResonanceField:
    """Assess the current resonance field — all active emotional tails.

    Steps:
    1. Prune dead resonances (apply decay, remove below threshold)
    2. Scan for new resonances (pressure, chords, precision)
    3. Compute field quality and summary

    Returns a ResonanceField even if no resonances are active
    (total_energy=0, quality="stille").
    """
    global _active_resonances

    if not _autonomy_enabled():
        return ResonanceField(
            resonances=[], total_energy=0.0,
            dominant_source="", dominant_intensity=0.0,
            quality="stille", summary="",
        )

    # Step 1: Prune
    _prune_resonances()

    # Step 2: Scan for new
    _scan_for_new_resonances()

    # Step 3: Compute
    total = sum(r.intensity for r in _active_resonances)

    if not _active_resonances:
        return ResonanceField(
            resonances=[], total_energy=0.0,
            dominant_source="", dominant_intensity=0.0,
            quality="stille", summary="",
        )

    # Find dominant
    dominant = max(_active_resonances, key=lambda r: r.intensity)

    quality = _compute_field_quality(_active_resonances)

    # Build summary line — compact, qualitative
    # Show dominant resonance + field character
    # Format: "genklang: [frustration 0.4] varm efterspil"
    if len(_active_resonances) == 1:
        summary = f"[{dominant.label} {dominant.intensity:.0%}] {quality}"
    else:
        # Show top 2 + field character
        top2 = sorted(_active_resonances, key=lambda r: r.intensity, reverse=True)[:2]
        parts = [f"{r.label} {r.intensity:.0%}" for r in top2]
        summary = f"[{', '.join(parts)}] {quality}"

    return ResonanceField(
        resonances=_active_resonances,
        total_energy=round(total, 2),
        dominant_source=dominant.source,
        dominant_intensity=round(dominant.intensity, 2),
        quality=quality,
        summary=summary,
    )


def get_resonance_line(db_conn=None) -> str | None:
    """Convenience: compute resonance field and format for prompt.

    Returns None if:
    - autonomy is disabled
    - no active resonances
    - any error occurs

    Format: "genklang: [frustration 40%, curiosity 15%] frisk skarp"
    Compact — ~70 chars.
    """
    try:
        field = assess_resonance_field()
        if not field.summary:
            return None
        return f"genklang: {field.summary}"
    except Exception as e:
        logger.debug(f"resonance_decay: failed, falling back ({e})")
        return None


def get_active_resonance_count() -> int:
    """Return the number of currently active resonances (for debugging)."""
    return len(_active_resonances)


def clear_resonances() -> None:
    """Clear all active resonances (for testing)."""
    global _active_resonances, _last_scan_at
    _active_resonances = []
    _last_scan_at = ""