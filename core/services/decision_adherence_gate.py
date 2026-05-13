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

    # Live R2 heed-rate overlay (2026-05-13). adherence_score in DB only
    # updates on manual review_decision() — most decisions never get reviewed,
    # so the stored score stays at default (0.95+). Real behaviour is in R2
    # telemetry (surfaces vs heeded). For decisions about "follow warnings"
    # (loop_nudge, verification gate), R2 heed_rate is the truer signal.
    # If R2 rate is low + surfaced volume meaningful, fold it in as min(score, rate)
    # so gate fires when EITHER signal indicates a problem.
    r2_rate: float | None = None
    try:
        from core.services.verification_gate_telemetry import get_telemetry_summary
        s = get_telemetry_summary(hours=24)
        if int(s.get("surfaced_total") or 0) >= 5:
            r = s.get("heed_rate")
            if r is not None:
                r2_rate = float(r)
    except Exception as exc:
        logger.debug("decision_adherence_gate: r2 lookup failed: %s", exc)

    # Decision IDs whose adherence should be derived from R2 telemetry rather
    # than the stale stored score. Add new ones here when we identify them.
    _R2_LINKED_DECISIONS = {
        "dec_d56d89ceec24",  # loop-nudge commitment — tracked in R2 gate
    }

    lines = ["\n[DECISION-ADHERENCE-GATE]"]
    has_escalation = False

    for d in active:
        directive = d.get("directive", "")
        stored_score = d.get("adherence_score", 1.0) or 1.0
        dec_id = d.get("decision_id", "?")

        # Overlay R2 telemetry where applicable
        if r2_rate is not None and dec_id in _R2_LINKED_DECISIONS:
            score = min(float(stored_score), r2_rate)
        else:
            score = float(stored_score)

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