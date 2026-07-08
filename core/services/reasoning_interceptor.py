"""Reasoning interceptor orchestrator. intercept_round() runs between a round's reasoning and the
next action: pre-filter → detectors → graded InterceptOutcome. SHADOW by default (records the
would-inject verdict, surfaces nothing). ALWAYS fail-open to GREEN — a failure here must never
break a run."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from core.services.gate_kernel import Decision


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


def _run_detectors(ctx: dict[str, Any]):
    """Phase 0 stub — no detectors yet. Returns None (GREEN)."""
    return None


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
        verdict = _run_detectors(_ctx)
        grade = verdict.decision if verdict is not None else Decision.GREEN
        triggers = [verdict.gate] if (verdict is not None and verdict.decision is not Decision.GREEN) else []
        active = _is_active(grade) and grade is not Decision.GREEN
        correction = None
        if active and verdict is not None:
            correction = f"[interceptor:{verdict.gate}] {verdict.reason}"[:400]
        return InterceptOutcome(
            grade=grade, correction=correction, triggers=triggers,
            shadow=not active, latency_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception:
        return InterceptOutcome(grade=Decision.GREEN, shadow=True,
                                latency_ms=int((time.monotonic() - t0) * 1000))
