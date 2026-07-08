"""Reasoning interceptor orchestrator. intercept_round() runs between a round's reasoning and the
next action: pre-filter → detectors → graded InterceptOutcome. SHADOW by default (records the
would-inject verdict, surfaces nothing). ALWAYS fail-open to GREEN — a failure here must never
break a run."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from core.services.gate_kernel import Decision, Verdict


@dataclass
class InterceptOutcome:
    grade: Decision = Decision.GREEN
    correction: str | None = None
    triggers: list[str] = field(default_factory=list)
    shadow: bool = True
    latency_ms: int = 0


def _is_active(grade: Decision) -> bool:
    """Active only if the kill-switch is flipped ON for this grade. Phase 0 stub — always shadow."""
    return False


def _run_detectors(ctx: dict[str, Any]) -> Verdict:
    """Run the tripped cluster-gate adapters + standing-orders; return the WORST Verdict (GREEN if
    none fired). Passed to central().decide so trace/breaker/ledger apply. Self-safe: a detector
    that raises has already returned None (each adapter is self-safe); this fn never raises."""
    from core.services import reasoning_detectors as det
    from core.services.gate_kernel import worst
    classes = set(ctx.get("risk_classes") or [])
    text = ctx.get("reasoning_text") or ""
    dispatch = {
        "fact_gate": det.fact_gate_on_reasoning,
        "decision_gate": det.decision_gate_on_reasoning,
        "veto": det.veto_on_reasoning,
        "verification": det.verification_on_reasoning,
        "cross_user_share": det.cross_user_share_on_reasoning,
    }
    verdicts: list[Verdict] = []
    for cls in classes:
        fn = dispatch.get(cls)
        if fn is not None:
            v = fn(text, ctx)
            if v is not None:
                verdicts.append(v)
    so = det.standing_orders_on_reasoning(text, ctx)  # always — the registry decides relevance
    if so is not None:
        verdicts.append(so)
    # drift — always attempted; self-gates on the independent affect signal (<0.7 → None)
    dr = det.drift_on_reasoning(text, ctx)
    if dr is not None:
        verdicts.append(dr)
    # tone — ANCHORED: only runs if a truth/drift concern already fired (never judges tone alone)
    if any(v.gate in ("fact_gate", "drift") for v in verdicts):
        _ctx_anchor = dict(ctx)
        _ctx_anchor["anchor_fired"] = True
        tn = det.tone_on_reasoning(text, _ctx_anchor)
        if tn is not None:
            verdicts.append(tn)
    if not verdicts:
        return Verdict("reasoning_interceptor", Decision.GREEN)
    worst_dec = worst(verdicts)
    return next(v for v in verdicts if v.decision is worst_dec)


def _observe(outcome: "InterceptOutcome", *, run_id: str, round_num: int) -> None:
    """Egress-free metadata-only pulse to the Central (never the reasoning text). Self-safe."""
    try:
        from core.services.central_private_observe import record_private
        record_private("metacognition", "reasoning_interceptor",
                       value=float({"green": 0, "yellow": 1, "red": 2}.get(outcome.grade.value, 0)),
                       meta={"grade": outcome.grade.value, "triggers": outcome.triggers,
                             "shadow": outcome.shadow, "latency_ms": outcome.latency_ms,
                             "round": round_num})
    except Exception:
        pass


def build_reasoning_interceptor_surface() -> dict[str, object]:
    """Central-CLI view: recent interceptor verdicts. Self-safe, read-only. Returns static shape
    when timeseries reader is unavailable."""
    try:
        from core.services.central_timeseries import recent
        samples = recent("metacognition", "reasoning_interceptor", limit=100)
        grade_counts = {"green": 0, "yellow": 0, "red": 0}
        for sample in samples:
            value = sample.value
            if value == 0:
                grade_counts["green"] += 1
            elif value == 1:
                grade_counts["yellow"] += 1
            elif value == 2:
                grade_counts["red"] += 1
        return {
            "active": True, "recent": len(samples),
            "green": grade_counts["green"],
            "yellow": grade_counts["yellow"],
            "red": grade_counts["red"],
            "shadow_only": True
        }
    except Exception:
        return {"active": True, "recent": 0, "green": 0, "yellow": 0, "red": 0, "shadow_only": True}


async def intercept_round_async(*, run_id: str, round_num: int, reasoning_text: str,
                                tool_calls_this_run: list[dict], ctx: dict | None = None,
                                budget_ms: int = 800) -> InterceptOutcome:
    """Async wrapper (invariant 4 — async/keepalive): runs the sync intercept in a thread with a
    HARD timeout. Timeout/error → GREEN no-op, so a slow/hung detector can never block the agentic
    loop (a silent-SSE cutoff). The caller emits keepalive around this await."""
    import asyncio
    try:
        if not (reasoning_text or "").strip():
            return InterceptOutcome(grade=Decision.GREEN, shadow=True)
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, lambda: intercept_round(
            run_id=run_id, round_num=round_num, reasoning_text=reasoning_text,
            tool_calls_this_run=tool_calls_this_run, ctx=ctx))
        return await asyncio.wait_for(fut, timeout=max(0.05, budget_ms / 1000.0))
    except Exception:
        # includes asyncio.TimeoutError — the executor thread finishes on its own (intercept_round
        # is self-safe and, in shadow, mutates no run state); we ignore its late result.
        return InterceptOutcome(grade=Decision.GREEN, shadow=True)


def intercept_round(*, run_id: str, round_num: int, reasoning_text: str,
                    tool_calls_this_run: list[dict], ctx: dict | None = None) -> InterceptOutcome:
    t0 = time.monotonic()
    try:
        if not (reasoning_text or "").strip():
            return InterceptOutcome(grade=Decision.GREEN, shadow=True)
        from core.services.reasoning_prefilter import prefilter
        classes = prefilter(reasoning_text, ctx=ctx,
                            other_user_ids=(ctx or {}).get("other_user_ids"))
        if not classes:
            return InterceptOutcome(grade=Decision.GREEN, shadow=True)
        _ctx = dict(ctx or {})
        _ctx.update({"reasoning_text": reasoning_text, "risk_classes": sorted(classes),
                     "tool_calls_this_run": tool_calls_this_run, "run_id": run_id,
                     "round_num": round_num})
        # Route through central().decide → trace + circuit-breaker + verdict-ledger for free
        # (no catalog entry needed). A cognitive failure/disable → SKIP, which we treat as GREEN
        # (fail-open: the interceptor is a safety layer, never a blocker on its own failure).
        from core.services.central_core import central
        from core.services.gate_kernel import GateClass
        verdict = central().decide("reasoning_interceptor", _ctx, _run_detectors,
                                   cluster="metacognition", klass=GateClass.COGNITIVE)
        grade = verdict.decision
        if grade is Decision.SKIP:
            grade = Decision.GREEN
        triggers = ([verdict.gate] if grade is not Decision.GREEN
                    and verdict.gate != "reasoning_interceptor" else [])
        active = _is_active(grade) and grade is not Decision.GREEN
        correction = None
        if active:
            correction = f"[interceptor:{verdict.gate}] {verdict.reason}"[:400]
        _out = InterceptOutcome(
            grade=grade, correction=correction, triggers=triggers,
            shadow=not active, latency_ms=int((time.monotonic() - t0) * 1000),
        )
        _observe(_out, run_id=run_id, round_num=round_num)
        return _out
    except Exception:
        return InterceptOutcome(grade=Decision.GREEN, shadow=True,
                                latency_ms=int((time.monotonic() - t0) * 1000))
