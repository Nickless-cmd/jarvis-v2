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

logger = logging.getLogger(__name__)

# Thresholds
_ADVISORY_THRESHOLD = 0.40   # below this → imperative
_CRITICAL_THRESHOLD = 0.25   # below this → critical
_GOOD_THRESHOLD = 0.60      # above this → no nudge

# Loft over hvor mange linjer gaten skriver. Rækkerne sorteres værste-først
# nedenfor, så det kritiske bånd aldrig skubbes ud af loftet — og resten
# tælles op i én linje frem for at forsvinde tavst (fix 2026-09-21).
_MAKS_LINJER = 12


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
        from core.services.behavioral_decisions import (
            count_decisions,
            list_active_decisions,
        )
    except ImportError:
        logger.debug("decision_adherence_gate: behavioral_decisions not available")
        return ""

    # Fix 2026-09-21: gaten læste kun 20 af 44 aktive beslutninger — og i en
    # rækkefølge der gjorde det værre end tilfældigt, fordi lageret sorterer
    # efter priority/updated_at og IKKE efter adherence. Høj-prioritets-
    # beslutninger med høj adherence fortrængte de kritiske, som derfor
    # aldrig nåede frem til mig. Læs ALLE aktive og sortér efter score
    # nedenfor, så det kritiske bånd altid kommer med.
    try:
        active = list_active_decisions(limit=max(50, count_decisions(status="active")))
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

    # Saml alt under tærsklen først, sortér værste-først, og skriv så. Uden
    # sorteringen ville loftet kunne skjule en kritisk beslutning bag
    # advisory-støj — præcis den fejlklasse fixet 2026-09-21 retter.
    raekker: list[tuple[float, str, str]] = []
    for d in active:
        directive = d.get("directive", "")
        # Fix 2026-09-21: `d.get("adherence_score", 1.0) or 1.0` behandlede en
        # score på PRÆCIS 0.0 som falsy og løftede den til 1.0 — den værste
        # beslutning af alle blev læst som «doing fine» og sprunget over.
        # Kun None betyder «aldrig reviewet».
        raa = d.get("adherence_score")
        stored_score = float(raa) if raa is not None else 1.0
        dec_id = d.get("decision_id", "?")

        # Overlay R2 telemetry where applicable
        if r2_rate is not None and dec_id in _R2_LINKED_DECISIONS:
            score = min(stored_score, r2_rate)
        else:
            score = stored_score

        if score >= _GOOD_THRESHOLD:
            continue  # doing fine, no nudge needed

        raekker.append((score, dec_id, directive))

    if not raekker:
        return ""

    raekker.sort(key=lambda r: r[0])

    lines = ["\n[DECISION-ADHERENCE-GATE]"]
    for score, dec_id, directive in raekker[:_MAKS_LINJER]:
        if score < _CRITICAL_THRESHOLD:
            # Critical band — adherence below 25%
            lines.append(
                f"Adherence {score:.0%} (kritisk band) — {dec_id}: {directive}"
            )
            lines.append(
                "  Mekanisme: ved fortsat lav adherence revokes decision automatisk."
            )
        elif score < _ADVISORY_THRESHOLD:
            # Imperative band — adherence below 40%
            lines.append(
                f"Adherence {score:.0%} (imperativ band) — {dec_id}: {directive}"
            )
            lines.append(
                "  Mekanisme: adherence falder yderligere ved næste brud, kan trigger revoke."
            )
        else:
            # Advisory band — adherence below good threshold
            lines.append(
                f"Adherence {score:.0%} (advisory band) — {dec_id}: {directive}"
            )

    skjulte = len(raekker) - _MAKS_LINJER
    if skjulte > 0:
        # Aldrig tavs: hellere sige hvor mange der ligger under tærsklen end
        # at lade dem forsvinde ud af prompten uden et spor.
        lines.append(f"… og {skjulte} flere under tærsklen (ikke vist her).")

    lines.append("[/DECISION-ADHERENCE-GATE]\n")
    return "\n".join(lines)