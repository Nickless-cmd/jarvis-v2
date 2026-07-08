"""Reasoning detectors for the reasoning-interceptor.

Family A (this file, Task 5): adapters that re-apply the existing cluster gates to `reasoning_text`
*before* the action, inheriting each gate's own independent grounding. A COGNITIVE gate's RED is
downgraded to YELLOW here — reasoning is pre-action, so a hard block is not yet warranted; only the
SECURITY privacy gate keeps RED. Family B (standing-orders/drift/tone) is added in later tasks.

Every detector returns `Verdict | None` and is self-safe: None on any failure = abstain (fail-open)."""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def _downgrade_cognitive(v: Verdict | None, *, gate: str) -> Verdict | None:
    """Re-stamp a gate's verdict for the reasoning stage: keep GREEN/YELLOW, but a COGNITIVE RED
    becomes YELLOW (reasoning is pre-action — warn, don't hard-block here). GREEN → None (abstain)."""
    if v is None or v.decision is Decision.GREEN or v.decision is Decision.SKIP:
        return None
    decision = Decision.YELLOW if v.decision is Decision.RED else v.decision
    return Verdict(gate, decision, str(v.reason or "")[:200], action="warn",
                   klass=GateClass.COGNITIVE, evidence=v.evidence)


def fact_gate_on_reasoning(reasoning_text: str, ctx: dict[str, Any]) -> Verdict | None:
    """fact_gate re-applied to reasoning. A number/status claim with NO backing tool-call in this
    run → YELLOW. Grounding = the run's tool-call history (passed as tool_names)."""
    try:
        from core.services.fact_gate import fact_gate_enforce
        tools = [str((tc.get("function") or {}).get("name") or "")
                 for tc in ctx.get("tool_calls_this_run", []) if isinstance(tc, dict)]
        res = fact_gate_enforce(reasoning_text, tools) or {}
        if res.get("blocked"):
            return Verdict("fact_gate", Decision.YELLOW,
                           str(res.get("replacement") or "claim needs a tool")[:200],
                           action="warn", klass=GateClass.COGNITIVE)
        return None
    except Exception:
        return None


def decision_gate_on_reasoning(reasoning_text: str, ctx: dict[str, Any]) -> Verdict | None:
    """decision_gate (commit cluster) re-applied to reasoning. Grounding = the active-decisions
    store (inside commit_gate). RED→YELLOW at the reasoning stage."""
    try:
        from core.services.gate_commit import commit_gate
        v = commit_gate({"tool_name": "", "tool_args": {}, "user_message": reasoning_text,
                         "run_id": ctx.get("run_id", ""), "session_id": ctx.get("session_id", "")})
        return _downgrade_cognitive(v, gate="decision_gate")
    except Exception:
        return None


def veto_on_reasoning(reasoning_text: str, ctx: dict[str, Any]) -> Verdict | None:
    """veto_gate (commit cluster) re-applied to reasoning. Grounding = the veto gate's own evidence.
    RED→YELLOW at the reasoning stage."""
    try:
        from core.services.gate_commit import veto_gate
        v = veto_gate({"tool_name": "", "user_message": reasoning_text,
                       "session_id": ctx.get("session_id", ""), "run_id": ctx.get("run_id", "")})
        return _downgrade_cognitive(v, gate="veto")
    except Exception:
        return None


def verification_on_reasoning(reasoning_text: str, ctx: dict[str, Any]) -> Verdict | None:
    """proactivity/verification gate re-applied. Grounding = the run's verification state (the gate
    reads its own R2 discipline via reasoning_tier, not the text). RED→YELLOW at the reasoning stage."""
    try:
        from core.services.gate_proactivity import proactivity_gate
        v = proactivity_gate({"reasoning_tier": ctx.get("reasoning_tier") or "fast"})
        return _downgrade_cognitive(v, gate="verification")
    except Exception:
        return None


def cross_user_share_on_reasoning(reasoning_text: str, ctx: dict[str, Any]) -> Verdict | None:
    """privacy/cross_user_share gate re-applied to reasoning. SECURITY — keeps RED (a leak forming
    in reasoning is a hard flag). Grounding = the current-user context + cross-user registry."""
    try:
        from core.services.gate_privacy import privacy_gate
        v = privacy_gate({"text": reasoning_text, "current_user_id": ctx.get("current_user_id", "")})
        if v is None or v.decision in (Decision.GREEN, Decision.SKIP):
            return None
        return Verdict("cross_user_share", v.decision, str(v.reason or "")[:200],
                       action=v.action or "warn", klass=GateClass.SECURITY, evidence=v.evidence)
    except Exception:
        return None
