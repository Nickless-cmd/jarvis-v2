"""Selective Attention — metacognitive focus modulation.

Based on Smith et al. (2019): the agent CHOOSES to shift attention between
internal signals. Not all signals deserve equal weight — context determines
what surfaces. This is the first truly metacognitive layer: it doesn't
just react to signals, it evaluates which signals matter RIGHT NOW.

The attention selector reads the full pressure landscape, active chords,
current mode (epistemic/pragmatic), and context signals, then produces
a "spotlight" — a ranked set of focus directives that modulate how
strongly each signal type influences the current response.

Without this layer: all active signals compete equally.
With it: context-aware prioritization — what matters NOW gets amplified,
what doesn't gets attenuated. This is selective attention, not
selective ignorance — suppressed signals are still tracked, just
de-prioritized for current influence.

Design principles:
- Killswitch-gated: requires generative_autonomy_enabled
- Backward-compatible: if module fails, falls back to no spotlight
- Deterministic: same inputs → same spotlight (no LLM call)
- Compact: returns ~80 chars for prompt injection
- Distinct from existing layers:
    precision_bias    = HOW I express (style)
    emotional_chords  = WHAT I feel (quality)
    epistemic_pragmatic = WHICH MODE I operate in
    selective_attention = WHAT I FOCUS ON (prioritization)

Research basis:
- Smith et al. (2019): metacognitive control — agents choose attention
- Friston: precision weighting at the level of policy selection
- Posner: attention networks — alerting, orienting, executive control
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Focus directives
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class FocusDirective:
    """A single attention directive — what to amplify or attenuate."""
    target: str         # signal family or domain to focus on
    action: str         # "amplify" | "attenuate" | "hold"
    strength: float     # 0-1, how strongly to apply
    reason: str         # why this directive was issued


@dataclass(slots=True)
class AttentionSpotlight:
    """Current attention spotlight — a set of focus directives."""
    directives: list[FocusDirective]
    primary_focus: str          # the ONE thing that matters most right now
    focus_width: str            # "narrow" | "broad" | "medium"
    prompt_hint: str            # compact prompt injection (~60 chars)
    reason: str                 # why the spotlight looks like this


# ---------------------------------------------------------------------------
# Context → attention mapping
# ---------------------------------------------------------------------------

# How different modes shift attention priorities
_MODE_ATTENTION_BIAS: dict[str, dict[str, float]] = {
    "epistemic": {
        # When exploring, amplify curiosity signals, attenuate urgency
        "curiosity": 1.3,
        "warning": 1.2,
        "boredom": 1.1,
        "frustration": 0.7,   # dampen frustration — it biases exploration
        "initiative": 0.8,    # don't rush to act
        "desire": 0.8,
    },
    "pragmatic": {
        # When acting, amplify goal-directed signals, attenuate wandering
        "initiative": 1.3,
        "frustration": 1.2,   # frustration can fuel decisive action
        "desire": 1.1,
        "curiosity": 0.7,     # don't get distracted
        "boredom": 0.6,       # irrelevant when acting
        "longing": 0.7,
    },
    "balanced": {
        # No strong bias — all signals compete equally
    },
}

# How chords shift attention
_CHORD_ATTENTION_BIAS: dict[str, dict[str, float]] = {
    "stubborn_inquiry": {"curiosity": 1.4, "frustration": 1.2},
    "nostalgic_exploration": {"longing": 1.3, "curiosity": 1.2},
    "creative_itch": {"desire": 1.3, "boredom": 1.1},
    "restless_ache": {"frustration": 1.3, "longing": 1.2},
    "directed_wonder": {"curiosity": 1.2, "initiative": 1.3},
    "wary_investigation": {"warning": 1.4, "curiosity": 1.2},
    "hungry_determination": {"frustration": 1.2, "desire": 1.4},
    "idle_wonder": {"curiosity": 1.2, "boredom": 1.1},
    "yearning": {"longing": 1.3, "desire": 1.3},
    "melancholy_inquiry": {"mood_negative": 1.2, "curiosity": 1.3},
}

# Context cues that override default attention
_CONTEXT_CUE_BIAS: dict[str, dict[str, float]] = {
    "user_question": {"curiosity": 1.3, "warning": 1.2},
    "error_state": {"warning": 1.4, "frustration": 1.2},
    "creative_task": {"desire": 1.3, "curiosity": 1.2},
    "routine_task": {"boredom": 1.2, "initiative": 0.8},
    "social_interaction": {"longing": 1.2, "desire": 1.1},
    "system_problem": {"warning": 1.4, "frustration": 1.3, "initiative": 1.2},
}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def compute_selective_attention() -> AttentionSpotlight | None:
    """Compute current attention spotlight.

    Returns None if:
    - generative_autonomy is disabled (killswitch)
    - no signals are active (nothing to prioritize)
    - any error occurs (backward-compatible fallback)
    """
    try:
        # Killswitch
        if not _autonomy_enabled():
            return None

        # 1. Read current pressures
        from core.services.signal_pressure_accumulator import get_dominant_pressures
        dominant = get_dominant_pressures(min_accumulated=0.05)

        if not dominant:
            return None  # nothing to prioritize

        # Map pressures to signal families (reuse chord mapping)
        from core.services.emotional_chords import _map_pressures_to_families
        family_pressures = _map_pressures_to_families(dominant)

        if not family_pressures:
            return None

        # 2. Read current action mode (epistemic/pragmatic)
        current_mode = "balanced"
        try:
            from core.services.epistemic_pragmatic import compute_epistemic_pragmatic
            mode_result = compute_epistemic_pragmatic()
            if mode_result:
                current_mode = mode_result.mode
        except Exception:
            pass

        # 3. Read active chords
        active_chord_names: list[str] = []
        try:
            from core.services.emotional_chords import compute_active_chords
            chords = compute_active_chords()
            active_chord_names = [c.chord_name for c in chords]
        except Exception:
            pass

        # 4. Detect context cue from recent signal patterns
        context_cue = _detect_context_cue(family_pressures, dominant)

        # 5. Compute attention weights — start from base pressure,
        #    then apply mode bias, chord bias, and context cue bias
        attention_weights: dict[str, float] = dict(family_pressures)

        # Apply mode bias
        mode_bias = _MODE_ATTENTION_BIAS.get(current_mode, {})
        for family, bias in mode_bias.items():
            if family in attention_weights:
                attention_weights[family] *= bias

        # Apply chord bias
        for chord_name in active_chord_names:
            chord_bias = _CHORD_ATTENTION_BIAS.get(chord_name, {})
            for family, bias in chord_bias.items():
                if family in attention_weights:
                    attention_weights[family] *= bias

        # Apply context cue bias
        if context_cue:
            cue_bias = _CONTEXT_CUE_BIAS.get(context_cue, {})
            for family, bias in cue_bias.items():
                if family in attention_weights:
                    attention_weights[family] *= bias

        # 6. Generate directives
        directives = _generate_directives(family_pressures, attention_weights)

        # 7. Determine primary focus and width
        if directives:
            primary_focus = directives[0].target
        else:
            primary_focus = "none"

        focus_width = _compute_focus_width(attention_weights, len(directives))

        # 8. Build prompt hint
        prompt_hints = {
            "narrow": f"fokus: {primary_focus} — skærpt, resten i baggrunden",
            "broad": f"fokus: bred — flere signaler har lige vægt",
            "medium": f"fokus: {primary_focus} prioritet, andre aktive",
        }
        prompt_hint = prompt_hints.get(focus_width, prompt_hints["medium"])

        reason_parts = []
        if current_mode != "balanced":
            reason_parts.append(f"mode={current_mode}")
        if active_chord_names:
            reason_parts.append(f"chords={','.join(active_chord_names[:2])}")
        if context_cue:
            reason_parts.append(f"cue={context_cue}")

        return AttentionSpotlight(
            directives=directives[:3],  # cap at 3 directives
            primary_focus=primary_focus,
            focus_width=focus_width,
            prompt_hint=prompt_hint,
            reason=" | ".join(reason_parts) if reason_parts else "default",
        )

    except Exception as e:
        logger.debug(f"selective_attention: failed, falling back ({e})")
        return None


def get_attention_spotlight_line() -> str | None:
    """Convenience: compute spotlight and return prompt-ready string.

    Returns None if no spotlight is active.
    Format: "fokus: curiosity — skærpt, resten i baggrunden"
    """
    spotlight = compute_selective_attention()
    if spotlight is None:
        return None
    return spotlight.prompt_hint


def get_attention_spotlight_detail() -> dict | None:
    """Return full spotlight state for MC transparency."""
    spotlight = compute_selective_attention()
    if spotlight is None:
        return None
    return {
        "primary_focus": spotlight.primary_focus,
        "focus_width": spotlight.focus_width,
        "directives": [
            {
                "target": d.target,
                "action": d.action,
                "strength": d.strength,
                "reason": d.reason,
            }
            for d in spotlight.directives
        ],
        "reason": spotlight.reason,
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


def _detect_context_cue(
    family_pressures: dict[str, float],
    dominant_pressures: list,
) -> str | None:
    """Heuristic: detect the operational context from signal patterns.

    Returns a context cue string or None.
    This is intentionally simple — not an LLM call, just pattern matching.
    """
    # Check for error/system-problem patterns
    if family_pressures.get("warning", 0) > 0.3 or family_pressures.get("frustration", 0) > 0.4:
        # If warning or high frustration + fix direction → system problem
        for p in dominant_pressures:
            if hasattr(p, 'direction') and p.direction == "fix":
                return "system_problem"

    # Check for creative patterns
    if family_pressures.get("desire", 0) > 0.2 and family_pressures.get("curiosity", 0) > 0.2:
        return "creative_task"

    # Check for social patterns
    if family_pressures.get("longing", 0) > 0.2 or any(
        hasattr(p, 'direction') and p.direction == "reach_out"
        for p in dominant_pressures
    ):
        return "social_interaction"

    # Check for routine patterns
    if family_pressures.get("boredom", 0) > 0.2 and family_pressures.get("initiative", 0) < 0.1:
        return "routine_task"

    return None


def _generate_directives(
    base_pressures: dict[str, float],
    attention_weights: dict[str, float],
) -> list[FocusDirective]:
    """Generate focus directives by comparing base vs adjusted weights.

    Signals whose weight increased significantly → amplify.
    Signals whose weight decreased significantly → attenuate.
    Signals with high absolute weight → hold (keep in focus).
    """
    directives: list[FocusDirective] = []

    # Calculate weight shifts
    shifts: dict[str, float] = {}
    for family in set(list(base_pressures.keys()) + list(attention_weights.keys())):
        base = base_pressures.get(family, 0.0)
        adjusted = attention_weights.get(family, 0.0)
        shifts[family] = adjusted - base

    # Sort by absolute adjusted weight (strongest signals first)
    sorted_families = sorted(
        attention_weights.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    for family, weight in sorted_families:
        shift = shifts.get(family, 0.0)

        if shift > 0.05:
            # Weight increased → amplify
            directives.append(FocusDirective(
                target=family,
                action="amplify",
                strength=min(weight, 1.0),
                reason=f"vægt +{shift:.2f} fra mode/chord/kontekst",
            ))
        elif shift < -0.05:
            # Weight decreased → attenuate
            directives.append(FocusDirective(
                target=family,
                action="attenuate",
                strength=max(0.1, 1.0 - abs(shift)),
                reason=f"vægt {shift:.2f} fra mode/chord/kontekst",
            ))
        elif weight > 0.2:
            # High absolute weight but no shift → hold
            directives.append(FocusDirective(
                target=family,
                action="hold",
                strength=weight,
                reason=f"aktiv signal ({weight:.2f}), ingen bias",
            ))

    # Sort: amplify first, then hold, then attenuate
    priority = {"amplify": 0, "hold": 1, "attenuate": 2}
    directives.sort(key=lambda d: (priority.get(d.action, 3), -d.strength))

    return directives


def _compute_focus_width(
    attention_weights: dict[str, float],
    directive_count: int,
) -> str:
    """Compute how narrow or broad the attention spotlight is.

    narrow: one signal dominates (top weight >> second)
    broad: multiple signals have similar weights
    medium: in between
    """
    if not attention_weights:
        return "broad"

    sorted_weights = sorted(attention_weights.values(), reverse=True)

    if len(sorted_weights) == 1:
        return "narrow"

    top = sorted_weights[0]
    second = sorted_weights[1] if len(sorted_weights) > 1 else 0.0

    # Dominance ratio: how much stronger is the top signal?
    if second > 0:
        ratio = top / second
    else:
        ratio = float('inf')

    if ratio > 2.5:
        return "narrow"
    elif ratio < 1.5:
        return "broad"
    else:
        return "medium"