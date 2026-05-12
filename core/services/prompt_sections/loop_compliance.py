"""Loop-compliance self-check section.

When Jarvis has been firing loop-nudges and ignoring them, surface a
sharp meta-cognition prompt that forces explicit acknowledgement.

Background:
- Decision dec_d56d89ceec24: "Når loop-nudge fyrer, tager jeg en bevidst
  stilling: fortsætte eller opsummere. Jeg ignorerer den ikke."
- Observed pattern (2026-05-12): heed-rate ~3% over 24h on loop_nudge_5_rounds.
- Existing decision_adherence_gate was silently dead (wrong import) —
  Jarvis never SAW the escalation. Fixed in same commit batch.
- This module adds a SECONDARY, very-high-priority check that fires when
  the loop-nudge decision specifically is below threshold. Independent
  surface so Jarvis can't "miss" it among 50 other awareness sections.

Design:
- Reads dec_d56d89ceec24 directly via behavioral_decisions.get_decision()
- Priority 7 — same tier as identity pins (above generic awareness)
- Wording forces self-check before continuing
- Returns "" when adherence is healthy (>= 0.5) — no nag when behaviour
  is acceptable
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# The specific decision we're guarding. If this ID ever changes, update here.
_LOOP_DECISION_ID = "dec_d56d89ceec24"

# Below this score, surface the explicit self-check.
_NUDGE_THRESHOLD = 0.50
# Below this score, escalate wording further (harsher prose).
_CRITICAL_THRESHOLD = 0.25


def _decision_signal() -> tuple[float | None, str]:
    """Return (adherence_score, directive) for the loop-nudge decision, or (None, '')."""
    try:
        from core.services.behavioral_decisions import get_decision
        decision = get_decision(_LOOP_DECISION_ID)
    except Exception as exc:
        logger.debug("loop_compliance: decision lookup failed: %s", exc)
        return (None, "")
    if not decision or decision.get("status") != "active":
        return (None, "")
    try:
        return (float(decision.get("adherence_score")), str(decision.get("directive") or ""))
    except (TypeError, ValueError):
        return (None, str(decision.get("directive") or ""))


def _r2_telemetry_signal() -> tuple[float | None, int, int]:
    """Return (heed_rate, surfaced_total, heeded_total) over last 24h.

    Reads verification_gate_telemetry — surfaces tracked here include
    unverified/failed_verify warnings. When heed_rate is low (Jarvis
    ignores his own warnings), this signals the broader behavioural
    pattern that loop-nudges are part of.
    """
    try:
        from core.services.verification_gate_telemetry import get_telemetry_summary
        s = get_telemetry_summary(hours=24)
    except Exception as exc:
        logger.debug("loop_compliance: telemetry lookup failed: %s", exc)
        return (None, 0, 0)
    surfaced = int(s.get("surfaced_total") or 0)
    heeded = int(s.get("heeded_total") or 0)
    rate = s.get("heed_rate")
    if rate is None or surfaced < 5:
        # Don't surface when sample is too small to be meaningful.
        return (None, surfaced, heeded)
    try:
        return (float(rate), surfaced, heeded)
    except (TypeError, ValueError):
        return (None, surfaced, heeded)


def loop_compliance_section() -> str:
    """Render the compliance self-check when warnings are being ignored.

    Fires on EITHER signal:
      1. dec_d56d89ceec24 adherence_score below threshold
      2. R2 verification-gate heed_rate below threshold

    Returns "" when both signals are healthy or data unavailable.
    """
    dec_score, dec_directive = _decision_signal()
    r2_rate, r2_surfaced, r2_heeded = _r2_telemetry_signal()

    # Pick worst-case scenario across both signals
    dec_low = dec_score is not None and dec_score < _NUDGE_THRESHOLD
    r2_low = r2_rate is not None and r2_rate < _NUDGE_THRESHOLD

    if not (dec_low or r2_low):
        return ""

    # Determine severity from the lowest non-None score
    candidates = [s for s in (dec_score, r2_rate) if s is not None]
    if not candidates:
        return ""
    worst = min(candidates)
    critical = worst < _CRITICAL_THRESHOLD

    lines: list[str] = []
    if critical:
        lines.append(
            "⛔ COMPLIANCE BRUDT — du ignorerer dine egne advarsler systematisk."
        )
    else:
        lines.append(
            "⚠ COMPLIANCE LAVT — du ignorerer dine egne advarsler oftere end du følger dem."
        )

    if dec_low and dec_score is not None:
        pct = int(dec_score * 100)
        lines.append(
            f"• Loop-nudge commitment ({_LOOP_DECISION_ID}): {pct}% adherence. "
            f"\"{dec_directive[:140]}\""
        )

    if r2_low and r2_rate is not None:
        pct = int(r2_rate * 100)
        lines.append(
            f"• R2-gate (24t): {r2_surfaced} advarsler surfaced, {r2_heeded} heeded "
            f"= {pct}% heed-rate."
        )

    if critical:
        lines.append(
            "Næste gang en advarsel eller loop-nudge fyrer i denne session — STOP. "
            "Opsummér hvad du har fundet. Eller indrøm eksplicit \"jeg overrider "
            "fordi [konkret grund]\". Ingen \"én gang til\"-undskyldninger."
        )
    else:
        lines.append(
            "Når næste advarsel fyrer, tag en bevidst stilling — ikke automatisk fortsæt."
        )

    return "\n".join(lines)
