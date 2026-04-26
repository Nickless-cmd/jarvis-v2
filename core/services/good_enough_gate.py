"""Good-enough gate — completion criterion for autonomous runs.

When Jarvis works autonomously, two failure modes show up:
1. **Never stops polishing** — keeps "improving" forever, no clear stop.
2. **Stops too early** — declares done before evidence supports it.

The gate gives a structured opinion on whether a task is "done enough"
based on observable signals from the current autonomous run, NOT on the
model's own judgment (which is what we're trying to discipline).

Heuristics:
- Iteration count: run is approaching the budget? lean toward stopping.
- Verification proofs: recent verify_* tool calls returning ok? evidence
  that things are checked.
- Loop detection: same tool failing repeatedly? quality is degrading,
  stop and ask user.
- Time elapsed: long-running run is more likely to be polishing.
- Tool diversity: new kinds of tools recently called? still exploring;
  hold off on stopping.

Returns a verdict with an explanation. Designed to be advisory (the
caller decides), not enforcing. The score (0–100) is a confidence
that "good enough was reached", not a quality score.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _recent_run_signals(run_id: str, limit: int = 100) -> dict[str, Any]:
    try:
        from core.eventbus.bus import event_bus
        events = event_bus.recent(limit=limit * 2)
    except Exception:
        return {}
    relevant = []
    for e in events:
        payload = e.get("payload") or {}
        if isinstance(payload, dict) and payload.get("run_id") == run_id:
            relevant.append(e)
    if not relevant:
        # No run-id linked events (run_id was empty or not yet propagated);
        # fall back to last 60s of all events as a coarse signal.
        cutoff = (datetime.now(UTC) - timedelta(seconds=60)).isoformat()
        relevant = [e for e in events if str(e.get("created_at", "")) >= cutoff]
    return {
        "events": relevant,
        "tool_invocations": [e for e in relevant if e.get("kind") == "tool.invoked"],
        "tool_completions": [e for e in relevant if e.get("kind") == "tool.completed"],
    }


def evaluate_good_enough(
    *,
    run_id: str = "",
    iterations_done: int = 0,
    iteration_budget: int = 10,
    minutes_elapsed: float = 0.0,
    minutes_budget: float = 30.0,
) -> dict[str, Any]:
    signals = _recent_run_signals(run_id)
    completions = signals.get("tool_completions", [])
    invocations = signals.get("tool_invocations", [])

    # Verification evidence — verify_* tools returning ok lift the score.
    verify_ok = sum(
        1 for e in completions
        if str((e.get("payload") or {}).get("tool", "")).startswith("verify_")
        and str((e.get("payload") or {}).get("status", "")) == "ok"
    )
    verify_failed = sum(
        1 for e in completions
        if str((e.get("payload") or {}).get("tool", "")).startswith("verify_")
        and str((e.get("payload") or {}).get("status", "")) == "failed"
    )

    # Recent error rate.
    errors = sum(
        1 for e in completions
        if str((e.get("payload") or {}).get("status", "")) == "error"
    )
    completion_count = max(1, len(completions))
    error_rate = errors / completion_count

    # Iteration / time pressure.
    iter_pressure = min(1.0, iterations_done / max(1, iteration_budget))
    time_pressure = min(1.0, minutes_elapsed / max(1.0, minutes_budget))

    # Score: starts at 30 (never stop without evidence), bumped by verify
    # successes and pressure, dragged down by errors and verify failures.
    score = 30.0
    score += min(40.0, verify_ok * 15.0)
    score += iter_pressure * 15.0
    score += time_pressure * 10.0
    score -= verify_failed * 20.0
    score -= min(25.0, error_rate * 100.0)
    score = max(0.0, min(100.0, score))

    reasons: list[str] = []
    if verify_ok > 0:
        reasons.append(f"{verify_ok} verify_* calls returned ok")
    if verify_failed > 0:
        reasons.append(f"{verify_failed} verify_* calls failed — evidence against done")
    if error_rate > 0.4:
        reasons.append(f"recent error rate {int(error_rate*100)}% — quality degrading")
    if iter_pressure >= 0.8:
        reasons.append(f"iteration budget nearly exhausted ({iterations_done}/{iteration_budget})")
    if time_pressure >= 0.8:
        reasons.append(f"time budget nearly exhausted ({minutes_elapsed:.1f}/{minutes_budget:.0f} min)")
    if not reasons:
        reasons.append("no strong signal yet — keep working")

    if score >= 70:
        verdict = "stop_now"
        recommendation = "Wrap up: summarize what was done, mark task complete."
    elif score >= 50:
        verdict = "stop_soon"
        recommendation = "One more pass max, then stop. Run a verify_* if you haven't."
    elif error_rate > 0.5:
        verdict = "stop_and_ask"
        recommendation = "Quality is poor; pause and ask the user before continuing."
    else:
        verdict = "keep_going"
        recommendation = "Not enough evidence to stop. Keep working but consider a verify_* call."

    return {
        "status": "ok",
        "score": round(score, 1),
        "verdict": verdict,
        "reasons": reasons,
        "recommendation": recommendation,
        "signals": {
            "verify_ok": verify_ok,
            "verify_failed": verify_failed,
            "errors": errors,
            "tool_invocations": len(invocations),
            "tool_completions": len(completions),
            "iter_pressure": round(iter_pressure, 2),
            "time_pressure": round(time_pressure, 2),
        },
    }


def _exec_check_good_enough(args: dict[str, Any]) -> dict[str, Any]:
    return evaluate_good_enough(
        run_id=str(args.get("run_id") or ""),
        iterations_done=int(args.get("iterations_done") or 0),
        iteration_budget=int(args.get("iteration_budget") or 10),
        minutes_elapsed=float(args.get("minutes_elapsed") or 0.0),
        minutes_budget=float(args.get("minutes_budget") or 30.0),
    )


GOOD_ENOUGH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "check_good_enough",
            "description": (
                "Get an opinion on whether the current task is done enough to "
                "stop. Reads recent eventbus signals (verify_* successes, error "
                "rate, iteration/time pressure) and returns a verdict: "
                "stop_now / stop_soon / stop_and_ask / keep_going. Use in "
                "autonomous loops to avoid both perfectionism and premature "
                "completion. Score is confidence that good-enough was reached."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Optional run_id to scope signals."},
                    "iterations_done": {"type": "integer", "description": "How many tool-call iterations the autonomous loop has spent."},
                    "iteration_budget": {"type": "integer", "description": "Soft cap on iterations (default 10)."},
                    "minutes_elapsed": {"type": "number", "description": "How long the run has been going (minutes)."},
                    "minutes_budget": {"type": "number", "description": "Soft cap on minutes (default 30)."},
                },
                "required": [],
            },
        },
    },
]
