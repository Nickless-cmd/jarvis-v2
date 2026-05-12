"""Gate 1: Decision-adherence gate.

Inspects active decisions and their adherence scores.
Returns an escalated prompt section when adherence is low.

Escalation levels:
  - heed_rate >= 60%: no nudge (decision is being followed)
  - heed_rate 40-59%: advisory — "Husk at..."
  - heed_rate < 40%: imperative — "DU SKAL..." with explicit consequence
  - heed_rate < 25%: critical — highest priority, includes rollback warning

This module is imported lazily in prompt_contract.py to avoid circular imports.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# Thresholds
_ADVISORY_THRESHOLD = 0.40   # below this → imperative
_CRITICAL_THRESHOLD = 0.25   # below this → critical
_GOOD_THRESHOLD = 0.60      # above this → no nudge


def decision_adherence_section() -> str:
    """Build an escalation prompt section based on current decision adherence.

    Returns empty string if all decisions are above good threshold.
    """
    # Fix 2026-05-12: prior import was core.services.decision_runtime which
    # doesn't exist — this gate had been silently returning "" since its
    # creation. Real API lives in behavioral_decisions.list_active_decisions().
    # Result: low-adherence decisions (incl. loop-nudge compliance) never
    # reached Jarvis as awareness, even when score < 25%. Switched to the
    # correct module so escalation actually surfaces.
    try:
        from core.services.behavioral_decisions import list_active_decisions
    except ImportError:
        logger.debug("decision_adherence_gate: behavioral_decisions not available")
        return ""

    try:
        active = list_active_decisions(limit=20)
    except Exception as exc:
        logger.debug("decision_adherence_gate: list failed: %s", exc)
        return ""

    if not active:
        return ""
    if not active:
        return ""

    lines = ["\n[DECISION-ADHERENCE-GATE]"]
    has_escalation = False

    for d in active:
        directive = d.get("directive", "")
        score = d.get("adherence_score", 1.0) or 1.0
        dec_id = d.get("decision_id", "?")

        if score >= _GOOD_THRESHOLD:
            continue  # doing fine, no nudge needed

        has_escalation = True

        if score < _CRITICAL_THRESHOLD:
            # Critical: highest urgency
            lines.append(
                f"⛔ KRITISK ({score:.0%} adherence): {directive}"
            )
            lines.append(
                f"   → Hvis du ikke kan følge denne decision, revoke den med decision_revoke."
            )
            lines.append(
                f"   → Ellers: OVERHOLD DEN NU. Ingen undtagelser. [{dec_id}]"
            )
        elif score < _ADVISORY_THRESHOLD:
            # Imperative: strong command
            lines.append(
                f"⚠ DU SKAL ({score:.0%} adherence): {directive}"
            )
            lines.append(
                f"   → Konsekvens for brud: decision revokes eller adherence falder yderligere. [{dec_id}]"
            )
        else:
            # Advisory: gentle reminder
            lines.append(
                f"📌 Husk ({score:.0%} adherence): {directive} [{dec_id}]"
            )

    if not has_escalation:
        return ""

    lines.append("[/DECISION-ADHERENCE-GATE]\n")
    return "\n".join(lines)