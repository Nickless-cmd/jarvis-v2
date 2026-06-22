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
    """Kør Commit-clusterens decision-conflict-check og returnér ét Verdict.

    ctx: {tool_name, tool_args, user_message, run_id, session_id}.
    Tool-kald i konflikt med en aktiv beslutning → RED (block). For nu = decision_gate
    alene; flere delgates kan kombineres via worst-decision senere.
    """
    from core.services.decision_gate import check_decision_gate

    allowed, reason = check_decision_gate(
        str(ctx.get("tool_name") or ""),
        tool_args=ctx.get("tool_args") or {},
        user_message=str(ctx.get("user_message") or ""),
    )
    if not allowed:
        return Verdict("decision_gate", Decision.RED,
                       str(reason or "decision-konflikt"),
                       action="block", klass=GateClass.COGNITIVE)
    return Verdict("decision_gate", Decision.GREEN, "ok", klass=GateClass.COGNITIVE)
