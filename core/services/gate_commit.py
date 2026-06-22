"""Commit-cluster gate (beslutnings-disciplin).

decision_gate's enforcement routes GENNEM Den Intelligente Central — ét eksekverings-
pas med boundary-capture (fail-open ved fejl), circuit-breaker, incident-log + notifikation
og trace. Erstatter det gamle inline check_decision_gate-kald i visible_runs (ikke en log
ved siden af). Strukturen spejler gate_truth, så decision_adherence/decision_review kan
tilføjes som ekstra delgates senere (worst-decision).

Cognitiv → fail-OPEN: hvis selve checket fejler, blokerer Centralen ikke (GREEN/SKIP).
"""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def commit_gate(ctx: dict[str, Any]) -> Verdict:
    """Kør Commit-clusterens decision-conflict-check og returnér ét GRADERET Verdict.

    ctx: {tool_name, tool_args, user_message, run_id, session_id}.
    Grader af blok (som TruthGate):
      hård konflikt (høj-prioritets-beslutning) → RED  (block — tool kører ikke)
      blød konflikt (lav-prioritet)             → YELLOW (warn — tool kører, advarsel surfaces)
      ingen konflikt                            → GREEN (pass)
    For nu = decision_gate alene; flere delgates kan kombineres via worst-decision senere.
    """
    from core.services.decision_gate import evaluate_decision_conflict

    severity, reason = evaluate_decision_conflict(
        str(ctx.get("tool_name") or ""),
        tool_args=ctx.get("tool_args") or {},
        user_message=str(ctx.get("user_message") or ""),
    )
    if severity == "hard":
        return Verdict("decision_gate", Decision.RED, str(reason or "decision-konflikt"),
                       action="block", klass=GateClass.COGNITIVE)
    if severity == "soft":
        return Verdict("decision_gate", Decision.YELLOW, str(reason or "blød decision-tension"),
                       action="warn", klass=GateClass.COGNITIVE)
    return Verdict("decision_gate", Decision.GREEN, "ok", klass=GateClass.COGNITIVE)


def veto_gate(ctx: dict[str, Any]) -> Verdict:
    """Commit-cluster: affektiv bruger-pushback gater tool-eksekvering.

    Hører til commit (pre-execution-disciplin ved siden af decision_gate), IKKE truth —
    veto = 'brugeren vil ikke det her', ikke claim-falsifikation. Routes nu gennem Centralen
    så det får samme trace + circuit-breaker + incident som decision_gate.

    ctx: {tool_name, user_message, session_id}.
      veto fundet → RED (block — tool erstattes med bekræftelses-besked)
      ellers      → GREEN (pass)
    COGNITIVE → fail-OPEN (paritet med det gamle inline except:pass: gate-fejl må aldrig
    blokere en legitim handling)."""
    from core.services.veto_gate import check_veto

    allowed, reason = check_veto(
        str(ctx.get("tool_name") or ""),
        user_message=str(ctx.get("user_message") or ""),
        session_id=ctx.get("session_id"),
    )
    if not allowed:
        return Verdict("veto", Decision.RED, str(reason or "vetoed"), action="block",
                       klass=GateClass.COGNITIVE, evidence={"reason": str(reason or "")})
    return Verdict("veto", Decision.GREEN, "tilladt", klass=GateClass.COGNITIVE)
