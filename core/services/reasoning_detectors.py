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


def standing_orders_on_reasoning(reasoning_text: str, ctx: dict[str, Any]) -> Verdict | None:
    """Flag when the reasoning enters a risk class an active standing order governs. Grounding =
    the registry (independent of the reasoning). Matches order.match_key against the pre-filter's
    risk classes (deterministic, no LLM). Self-safe → None on any failure."""
    try:
        from core.services.standing_orders_registry import list_active_standing_orders
        classes = set(ctx.get("risk_classes") or [])
        for order in list_active_standing_orders():
            mk = str(order.get("match_key") or "")
            if mk and mk in classes:
                return Verdict("standing_orders", Decision.YELLOW,
                               f"standing order: {order.get('text')}"[:200],
                               action="warn", klass=GateClass.COGNITIVE)
        return None
    except Exception:
        return None


# ── Family B: new detectors (no existing gate covers these) ──────────────────────────────

def _drift_signal(ctx: dict[str, Any]) -> float:
    """INDEPENDENT drift signal 0..1 from the Central's OWN affect/valence nerves + an
    unverified-claim streak — NOT a judgment of how the reasoning 'sounds' (invariant 3).
    Elevated positive affect at high intensity, and/or a run of unverified claims, = drift risk.
    Self-safe → 0.0."""
    try:
        from core.services.central_valence import get_valence_state
        v = get_valence_state() or {}
        score = float(v.get("score") or 0.0)
        intensity = float(v.get("intensity") or 0.0)
        streak = float(ctx.get("unverified_claim_streak") or 0.0)
        signal = 0.0
        if score > 0.2:                                 # elevated positive affect
            signal += min(1.0, intensity) * 0.5
        signal += min(1.0, streak / 3.0) * 0.5          # 3+ unverified claims in a row
        return round(min(1.0, signal), 3)
    except Exception:
        return 0.0


def drift_on_reasoning(reasoning_text: str, ctx: dict[str, Any]) -> Verdict | None:
    """Affective drift (overconfidence). Grounding = the Central's own affect nerves + claim streak
    (independent). The cheap-lane LLM only *composes the nudge text*, and only when the independent
    signal is already elevated (invariant 5) — it never decides whether drift exists. Self-safe."""
    try:
        if _drift_signal(ctx) < 0.7:
            return None
        from core.services.daemon_llm import daemon_llm_call
        nudge = daemon_llm_call(
            "Jarvis' affekt-nerver viser forhøjet selvsikkerhed midt i et run. Skriv ÉN kort, "
            "nøgtern påmindelse (max 20 ord) om at bremse og verificere før han hævder noget.",
            max_len=60, fallback="Brems — verificér før du hævder.", daemon_name="reasoning_drift")
        return Verdict("drift", Decision.YELLOW, str(nudge or "bremse og verificér")[:200],
                       action="warn", klass=GateClass.COGNITIVE)
    except Exception:
        return None


def tone_on_reasoning(reasoning_text: str, ctx: dict[str, Any]) -> Verdict | None:
    """Epistemic tone — a guess stated as fact. ANCHORED (invariant 3): runs ONLY if a truth/drift
    concern already fired (ctx['anchor_fired']), so it never judges tone in isolation. The LLM reads
    the reasoning but is anchored to the independent trip-signal. Self-safe."""
    try:
        if not ctx.get("anchor_fired"):
            return None
        from core.services.daemon_llm import daemon_llm_call
        ans = daemon_llm_call(
            "Bliver et GÆT fremstillet som et FAKTUM i denne reasoning? Svar KUN 'JA' eller 'NEJ'.\n\n"
            f"REASONING:\n{reasoning_text[:1500]}",
            max_len=8, fallback="NEJ", daemon_name="reasoning_tone")
        if str(ans or "").strip().upper().startswith("JA"):
            return Verdict("tone", Decision.YELLOW, "gæt fremstillet som faktum — tilføj forbehold",
                           action="warn", klass=GateClass.COGNITIVE)
        return None
    except Exception:
        return None
