"""
Temporal Depth — predictive coding for internal signals.
Based on Friston's free energy principle: the brain is not a passive receiver,
it actively predicts and compares expectations with observation.

Without temporal depth: signals are interpreted only by their current activation.
With temporal depth: recent history and near-future expectations MODULATE how
current signals are weighted and interpreted.

Three temporal windows:
  - recall (past): what just happened? (last 1-4 hours)
  - anticipation (future): what do I expect next? (next 1-4 hours)
  - rhythm (pattern): what is the recurring cadence?

These are NOT explicit memory retrieval. They are prediction signals that
weight current experience. When recall matches current → amplification.
When anticipation is violated → surprise signal.

Design principles:
  - Backward-compatible: falls back to "neutral horizon" if no history
  - No LLM call: pure state read + arithmetic
  - Produces lightweight injection for assembly: ~60 chars
  - Subtle, not dominant: temporal context modulates, doesn't override
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TemporalSignal:
    """Compact representation of temporal context."""
    recall_strength: float      # 0.0–1.0, how present is recent history
    anticipation_match: float    # 0.0–1.0, does reality match expectation?
    rhythm_alignment: float     # 0.0–1.0, does now match expected cadence?
    summary: str               # human-readable: "↑ momentum", "↓ surprise", etc.


class TemporalDepth:
    """
    Reads current signal state + recent history to produce temporal modulation.
    Uses the cognitive state assembly's internal history and the agent's
    own chronicle/inner-voice records to build predictive context.
    """

    def __init__(self):
        self._cache: Optional[TemporalSignal] = None
        self._cache_ttl: float = 120.0  # recompute every 2 minutes

    def assess(self, assembly_state: dict, now_iso: str) -> TemporalSignal:
        """
        Main entry point. Returns a TemporalSignal that assembly uses
        to modulate how current pressures are interpreted.

        Args:
            assembly_state: output from cognitive_state_assembly (the full dict)
            now_iso: current ISO timestamp

        Returns:
            TemporalSignal with recall_strength, anticipation_match, rhythm_alignment
        """
        # Check cache
        if self._cache is not None:
            return self._cache

        # Compute temporal signals from assembly state
        signal = self._compute_temporal(assembly_state, now_iso)
        self._cache = signal
        return signal

    def invalidate(self):
        """Clear cache so next call recomputes."""
        self._cache = None

    def _compute_temporal(self, state: dict, now_iso: str) -> TemporalSignal:
        """
        Compute temporal modulation from assembly state.

        Signal sources to read:
          - state["cognitive_cadence"] — the rhythm metadata
          - state["pressure_summary"] — what pressures are active
          - state["line"]["body"] — the embodied state narrative
          - state["line"]["affect"] — the affective state narrative
          - recent events from eventbus (heartbeat, tool, channel events)
        """
        # --- RECALL: how present is recent history? ---
        recall_strength = self._compute_recall(state)

        # --- ANTICIPATION: does reality match expectation? ---
        anticipation_match = self._compute_anticipation(state)

        # --- RHYTHM: does now match expected cadence? ---
        rhythm_alignment = self._compute_rhythm(state)

        # Build summary phrase
        summary = self._build_summary(
            recall_strength, anticipation_match, rhythm_alignment
        )

        return TemporalSignal(
            recall_strength=recall_strength,
            anticipation_match=anticipation_match,
            rhythm_alignment=rhythm_alignment,
            summary=summary,
        )

    def _compute_recall(self, state: dict) -> float:
        """
        How present is recent history in current experience?
        Based on: how many pressures are still active vs. recently resolved.
        """
        # If we have active pressures, history is bleeding into now
        pressure_summary = state.get("pressure_summary", [])
        if not pressure_summary:
            return 0.1  # clean slate, no bleed-through

        # Count pressures with high activation (still ringing)
        active_count = sum(
            1 for p in pressure_summary
            if isinstance(p, dict) and p.get("activation", 0) > 0.5
        )
        total = len(pressure_summary)
        if total == 0:
            return 0.1

        # High active ratio = strong recall bleed = high recall_strength
        return 0.3 + (active_count / total) * 0.7

    def _compute_anticipation(self, state: dict) -> float:
        """
        Does reality match what I expected?
        Based on: cognitive cadence state and mode alignment.
        """
        # If we're in a smooth cognitive_cadence, things are going as expected
        cadence = state.get("cognitive_cadence", {})
        cadence_state = cadence.get("state", "unknown")

        if cadence_state == "flow":
            return 0.9  # things are going as predicted
        elif cadence_state == "stuck":
            return 0.2  # reality is NOT matching expectation → surprise
        elif cadence_state == "recovery":
            return 0.6  # partially resolving
        else:
            return 0.5  # neutral

    def _compute_rhythm(self, state: dict) -> float:
        """
        Does now match the expected recurring cadence?
        Based on: time-of-day patterns, session patterns.
        """
        # For now: rhythm is derived from how consistent the assembly
        # state has been over recent ticks (checked via eventbus)
        # Placeholder: return moderate alignment
        # TODO: integrate with rhythm_daemon when it exists
        return 0.6

    def _build_summary(
        self, recall: float, anticipation: float, rhythm: float
    ) -> str:
        """Build a short human-readable phrase for the assembly output."""
        if recall > 0.7 and anticipation < 0.4:
            return "↓ surprise"       # history bleeding + violated expectation
        elif recall > 0.7:
            return "↑ momentum"     # history reinforcing
        elif anticipation < 0.3:
            return "⚡ surprise"    # strong violation
        elif rhythm > 0.8:
            return "→ steady"
        else:
            return "· neutral"


# Singleton for use in assembly
_temporal_depth: Optional[TemporalDepth] = None


def get_temporal_depth() -> TemporalDepth:
    global _temporal_depth
    if _temporal_depth is None:
        _temporal_depth = TemporalDepth()
    return _temporal_depth
