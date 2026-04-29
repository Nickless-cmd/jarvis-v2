"""Epistemic/Pragmatic Balance — action-mode modulation.

Based on Friston's active inference: every action decomposes into
epistemic value (reducing uncertainty) and pragmatic value (achieving goals).
The agent's certainty determines the balance:

  Low certainty  → epistemic driving  (explore, ask, investigate)
  High certainty → pragmatic driving  (act, decide, deliver)

This is NOT about what I feel (chords) or how I express it (precision_bias).
It's about WHICH MODE my action takes — should I seek information,
or should I act on what I know?

The balance is computed from:
  1. Confidence-by-domain (from personality vector)
  2. Dominant pressure direction (explore → epistemic, fix/act → pragmatic)
  3. Active chord count (more chords = more uncertainty = epistemic lean)

Design principles:
- Killswitch-gated: requires generative_autonomy_enabled
- Backward-compatible: if module fails, returns None
- Deterministic: same inputs → same mode (no LLM call)
- Compact: returns ~60 chars for prompt injection
- Distinct from existing layers:
    precision_bias = HOW I express (style)
    emotional_chords = WHAT I feel (quality)
    epistemic_pragmatic = WHICH MODE I operate in (epistemic vs pragmatic)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Action modes
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class ActionMode:
    """Current epistemic/pragmatic balance."""
    mode: str               # "epistemic" | "pragmatic" | "balanced"
    confidence: float        # 0-1, overall certainty
    epistemic_weight: float  # 0-1, how much info-seeking drives
    pragmatic_weight: float  # 0-1, how much goal-achievement drives
    prompt_hint: str         # compact prompt injection (~50 chars)
    reason: str             # why this mode was selected


# ---------------------------------------------------------------------------
# Domain → action-mode mapping
# ---------------------------------------------------------------------------

# Some pressure directions are inherently epistemic or pragmatic
_DIRECTION_MODE_AFFINITY: dict[str, dict[str, float]] = {
    "explore":   {"epistemic": 0.8, "pragmatic": 0.2},
    "fix":       {"epistemic": 0.3, "pragmatic": 0.7},
    "create":    {"epistemic": 0.4, "pragmatic": 0.6},
    "act":       {"epistemic": 0.2, "pragmatic": 0.8},
    "reach_out": {"epistemic": 0.6, "pragmatic": 0.4},
    "respond":   {"epistemic": 0.5, "pragmatic": 0.5},
    "retreat":   {"epistemic": 0.3, "pragmatic": 0.7},
    "engage":    {"epistemic": 0.4, "pragmatic": 0.6},
}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def compute_epistemic_pragmatic() -> ActionMode | None:
    """Compute current epistemic/pragmatic balance.

    Returns None if:
    - generative_autonomy is disabled (killswitch)
    - no pressures are active (nothing to modulate)
    - any error occurs (backward-compatible fallback)
    """
    try:
        # Killswitch
        if not _autonomy_enabled():
            return None

        # 1. Read confidence from personality vector
        from core.runtime.db import get_latest_cognitive_personality_vector
        pv = get_latest_cognitive_personality_vector()
        if not pv:
            return None

        import json
        confidence_by_domain = pv.get("confidence_by_domain")
        if isinstance(confidence_by_domain, str):
            confidence_by_domain = json.loads(confidence_by_domain)

        # Overall confidence = mean of all domains
        if not confidence_by_domain:
            overall_confidence = 0.5
        else:
            values = [float(v) for v in confidence_by_domain.values() if isinstance(v, (int, float))]
            overall_confidence = sum(values) / max(len(values), 1) / 10.0  # normalize 0-10 → 0-1
            overall_confidence = min(max(overall_confidence, 0.0), 1.0)

        # 2. Read dominant pressures for direction affinity
        from core.services.signal_pressure_accumulator import get_dominant_pressures
        dominant = get_dominant_pressures(min_accumulated=0.10)

        if not dominant:
            # No pressures — use confidence alone
            return _mode_from_confidence(overall_confidence)

        # Weight pressures by their accumulated strength
        total_weight = sum(p.accumulated for p in dominant)
        if total_weight <= 0:
            return _mode_from_confidence(overall_confidence)

        # Weighted direction affinity
        epistemic_sum = 0.0
        pragmatic_sum = 0.0
        for p in dominant:
            affinity = _DIRECTION_MODE_AFFINITY.get(p.direction, {"epistemic": 0.5, "pragmatic": 0.5})
            weight = p.accumulated / total_weight
            epistemic_sum += affinity["epistemic"] * weight
            pragmatic_sum += affinity["pragmatic"] * weight

        # 3. Count active chords — more chords = more epistemic lean
        chord_boost = 0.0
        try:
            from core.services.emotional_chords import compute_active_chords
            active_chords = compute_active_chords()
            # Each active chord adds a small epistemic nudge
            # (complexity → need to understand before acting)
            chord_boost = len(active_chords) * 0.08
        except Exception:
            pass

        epistemic_weight = min(epistemic_sum + chord_boost, 1.0)
        pragmatic_weight = min(pragmatic_sum, 1.0)

        # 4. Combine with confidence
        # High confidence → shift toward pragmatic
        # Low confidence → shift toward epistemic
        # This is the core Friston insight: certainty determines mode
        confidence_shift = (overall_confidence - 0.5) * 0.3  # ±0.15 max shift
        pragmatic_weight += confidence_shift
        epistemic_weight -= confidence_shift

        # Normalize to 0-1
        total = epistemic_weight + pragmatic_weight
        if total > 0:
            epistemic_weight = max(0.0, min(1.0, epistemic_weight / total))
            pragmatic_weight = max(0.0, min(1.0, pragmatic_weight / total))
        else:
            epistemic_weight = 0.5
            pragmatic_weight = 0.5

        # 5. Determine mode
        if epistemic_weight > 0.6:
            mode = "epistemic"
        elif pragmatic_weight > 0.6:
            mode = "pragmatic"
        else:
            mode = "balanced"

        # 6. Build prompt hint
        prompt_hints = {
            "epistemic": "mode: udforskende — søg viden før handling",
            "pragmatic": "mode: handlende — agér på det du ved",
            "balanced": "mode: balanceret — udforsk og hand i skift",
        }

        reason_parts = []
        if overall_confidence < 0.4:
            reason_parts.append("lav certainty")
        elif overall_confidence > 0.7:
            reason_parts.append("høj certainty")
        else:
            reason_parts.append("moderat certainty")

        if dominant:
            top_dir = dominant[0].direction
            reason_parts.append(f"presning: {top_dir}")

        return ActionMode(
            mode=mode,
            confidence=round(overall_confidence, 2),
            epistemic_weight=round(epistemic_weight, 2),
            pragmatic_weight=round(pragmatic_weight, 2),
            prompt_hint=prompt_hints[mode],
            reason=" | ".join(reason_parts),
        )

    except Exception as e:
        logger.debug(f"epistemic_pragmatic: failed, falling back ({e})")
        return None


def _mode_from_confidence(confidence: float) -> ActionMode | None:
    """Fallback: determine mode from confidence alone (no pressures)."""
    if confidence < 0.35:
        mode = "epistemic"
    elif confidence > 0.65:
        mode = "pragmatic"
    else:
        mode = "balanced"

    epistemic = 1.0 - confidence
    pragmatic = confidence

    prompt_hints = {
        "epistemic": "mode: udforskende — søg viden før handling",
        "pragmatic": "mode: handlende — agér på det du ved",
        "balanced": "mode: balanceret — udforsk og hand i skift",
    }

    return ActionMode(
        mode=mode,
        confidence=round(confidence, 2),
        epistemic_weight=round(epistemic, 2),
        pragmatic_weight=round(pragmatic, 2),
        prompt_hint=prompt_hints[mode],
        reason=f"confidence={confidence:.2f} (ingen presninger)",
    )


def get_mode_line() -> str | None:
    """Convenience: compute mode and return prompt-ready string.

    Returns None if no mode is active.
    Format: "mode: udforskende — søg viden før handling"
    """
    mode = compute_epistemic_pragmatic()
    if mode is None:
        return None
    return mode.prompt_hint


def get_mode_detail() -> dict | None:
    """Return full mode state for MC transparency."""
    mode = compute_epistemic_pragmatic()
    if mode is None:
        return None
    return {
        "mode": mode.mode,
        "confidence": mode.confidence,
        "epistemic": mode.epistemic_weight,
        "pragmatic": mode.pragmatic_weight,
        "reason": mode.reason,
    }


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