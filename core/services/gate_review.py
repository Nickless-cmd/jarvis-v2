"""Review-cluster gate — selv-review-vurdering, GRADERET.

Review-clusteren er observabilitet-først (async selv-review + trackere, ingen request-
path-blok). Dens enforcement-ÆKVIVALENT er selv-review-VURDERINGEN: når Jarvis reviewer
sin egen nylige adfærd, producerer self_review_unified et risk_level (low/med/high).
Den graderes og ruttes gennem Den Intelligente Central:

  RED    = høj-risiko selv-review (failure_rate > 0.5) → flag (incident, så Bjørn/Claude
           kan fange en selv-flagget risiko; self-review er sjælden → ingen spam).
  YELLOW = medium-risiko — follow-up påkrævet.
  GREEN  = sund.

Den BLOKERER ikke (det er en daemon-vurdering, ikke en request-path-gate) — men den
FANGER + FLAGGER + tracer gennem Centralen. Cognitiv → fail-open (GREEN ved tvivl).
"""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def review_gate(ctx: dict[str, Any]) -> Verdict:
    """ctx: {review} hvor review har risk_level (low/med/high) + score."""
    review = ctx.get("review") or {}
    rl = str(review.get("risk_level") or "low").strip().lower()
    score = review.get("score")
    if rl == "high":
        return Verdict("self_review", Decision.RED,
                       f"høj-risiko selv-review (score={score})",
                       action="warn", klass=GateClass.COGNITIVE,
                       evidence={"risk_level": rl, "score": score})
    if rl in ("med", "medium"):
        return Verdict("self_review", Decision.YELLOW,
                       f"medium-risiko selv-review — follow-up (score={score})",
                       action="warn", klass=GateClass.COGNITIVE,
                       evidence={"risk_level": rl, "score": score})
    return Verdict("self_review", Decision.GREEN, "sund selv-review",
                   action="none", klass=GateClass.COGNITIVE)
