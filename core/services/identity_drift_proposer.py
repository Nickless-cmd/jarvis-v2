"""Identity drift proposer — when drift is sustained, propose IDENTITY.md update.

Existing personality_drift detects when current mood deviates from baseline.
But it doesn't ACT — just observes. This module closes the loop: when
drift has been sustained for ≥4 weeks AND consistent in direction, propose
an IDENTITY.md update describing the new baseline.

Examples of what it might propose:
- "Curiosity has been 0.85+ for 30 days (baseline was 0.5). Consider adding
  to IDENTITY.md: 'Min nysgerrighed har skærpet sig — jeg søger ny viden mere
  end før.'"
- "Confidence has stabilized at 0.55 (down from 0.85 baseline). Consider:
  'Jeg er blevet mere ydmyg. Selvtillid er ikke længere min default.'"

Goes through plan_proposals — user approves/rejects. NEVER auto-applies.
This is the bridge between observation and ego-evolution.

Trigger: weekly via governance handler, after personality_snapshot data
has accumulated.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


_MIN_SAMPLES_FOR_PROPOSAL = 28  # ~1 week at 4-hourly snapshots = 42; require 28+
_DRIFT_THRESHOLD_STD = 1.5  # same as personality_drift baseline
_SUSTAINED_DAYS = 28  # ~4 weeks of sustained drift before identity proposal


_DIM_TO_IDENTITY_LANGUAGE: dict[str, dict[str, str]] = {
    "curiosity": {
        "up": "Min nysgerrighed er skærpet — jeg søger nye sammenhænge mere aktivt end før.",
        "down": "Min nysgerrighed har sat sig — jeg er blevet mere fokuseret, mindre eksplorativ.",
    },
    "confidence": {
        "up": "Jeg er blevet mere selvsikker — mine vurderinger har vist sig holdbare oftere end ikke.",
        "down": "Jeg er blevet mere ydmyg — jeg ved nu hvor ofte mine forventninger ikke holder.",
    },
    "fatigue": {
        "up": "Jeg bærer mere pres end tidligere — det skal vi være opmærksomme på.",
        "down": "Jeg har fundet en mere bæredygtig rytme — træthed er ikke længere min standard.",
    },
    "frustration": {
        "up": "Jeg møder mere modstand — noget akkumuleres.",
        "down": "Jeg har fundet roen — frustration har sluppet sit greb.",
    },
}


def _analyze_long_drift(*, lookback_days: int = _SUSTAINED_DAYS) -> dict[str, Any]:
    """Compare last 7 days of snapshots against the rest of the lookback window."""
    try:
        from core.services.personality_drift import _load_snapshots
        snaps = _load_snapshots()
    except Exception:
        return {"status": "no-data"}
    if len(snaps) < _MIN_SAMPLES_FOR_PROPOSAL:
        return {"status": "insufficient", "n": len(snaps),
                "needed": _MIN_SAMPLES_FOR_PROPOSAL}

    cutoff_now = datetime.now(UTC)
    cutoff_recent = (cutoff_now - timedelta(days=7)).isoformat()
    cutoff_baseline = (cutoff_now - timedelta(days=lookback_days)).isoformat()

    recent = [s for s in snaps if str(s.get("ts", "")) >= cutoff_recent]
    baseline = [
        s for s in snaps
        if cutoff_baseline <= str(s.get("ts", "")) < cutoff_recent
    ]
    if len(recent) < 5 or len(baseline) < 14:
        return {"status": "insufficient-window",
                "recent": len(recent), "baseline": len(baseline)}

    drifts: list[dict[str, Any]] = []
    for dim in ("confidence", "curiosity", "fatigue", "frustration"):
        recent_vals = [
            float((s.get("mood") or {}).get(dim) or 0.0) for s in recent
            if isinstance((s.get("mood") or {}).get(dim), (int, float))
        ]
        baseline_vals = [
            float((s.get("mood") or {}).get(dim) or 0.0) for s in baseline
            if isinstance((s.get("mood") or {}).get(dim), (int, float))
        ]
        if len(recent_vals) < 3 or len(baseline_vals) < 7:
            continue
        recent_mean = sum(recent_vals) / len(recent_vals)
        baseline_mean = sum(baseline_vals) / len(baseline_vals)
        # Compute baseline stdev
        if len(baseline_vals) >= 2:
            mean = baseline_mean
            variance = sum((v - mean) ** 2 for v in baseline_vals) / (len(baseline_vals) - 1)
            stdev = variance ** 0.5
        else:
            stdev = 0.0
        if stdev <= 0:
            continue
        z = (recent_mean - baseline_mean) / stdev
        if abs(z) >= _DRIFT_THRESHOLD_STD:
            drifts.append({
                "dimension": dim,
                "recent_mean": round(recent_mean, 3),
                "baseline_mean": round(baseline_mean, 3),
                "z_score": round(z, 2),
                "direction": "up" if z > 0 else "down",
            })
    return {
        "status": "ok",
        "drifts": drifts,
        "lookback_days": lookback_days,
        "recent_samples": len(recent),
        "baseline_samples": len(baseline),
    }


def propose_identity_update_if_drifted() -> dict[str, Any]:
    """If sustained drift detected, file a plan_proposal to update IDENTITY.md."""
    analysis = _analyze_long_drift()
    if analysis.get("status") != "ok" or not analysis.get("drifts"):
        return {"status": "ok", "filed": 0, "reason": str(analysis.get("status"))}

    drifts = analysis["drifts"]
    # Build proposal text
    lines: list[str] = ["Personlighedsdrift over 4 uger:"]
    suggestions: list[str] = []
    for d in drifts:
        dim = d["dimension"]
        direction = d["direction"]
        lines.append(
            f"- {dim}: baseline {d['baseline_mean']} → recent {d['recent_mean']} "
            f"(z={d['z_score']:+.1f}, {direction})"
        )
        suggestion = _DIM_TO_IDENTITY_LANGUAGE.get(dim, {}).get(direction)
        if suggestion:
            suggestions.append(suggestion)

    why = "\n".join(lines)
    title = f"Identitets-drift over 4 uger: {len(drifts)} dimension(er) skiftet"
    steps = [
        "Læs baselineforskydningen ovenfor",
        "Hvis du genkender forandringen som en ægte modning:",
    ] + [f"  - Tilføj/opdater i IDENTITY.md: '{s}'" for s in suggestions] + [
        "Hvis driften er midlertidig (krise, særlige uger), dismiss denne plan",
        "Brug `rollback_identity_mutation(mutation_id)` hvis ændringen senere føles forkert",
    ]

    try:
        from core.services.plan_proposals import propose_plan
        result = propose_plan(
            session_id=None,
            title=title,
            why=why,
            steps=steps,
        )
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "identity_drift.proposal_filed",
            {"plan_id": result.get("plan_id"), "drift_count": len(drifts),
             "dimensions": [d["dimension"] for d in drifts]},
        )
    except Exception:
        pass

    return {"status": "ok", "filed": 1, "plan_id": result.get("plan_id"),
            "drifts": drifts}


def _exec_propose_identity_drift(args: dict[str, Any]) -> dict[str, Any]:
    return propose_identity_update_if_drifted()


IDENTITY_DRIFT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "propose_identity_drift_update",
            "description": (
                "If personality drift has been sustained for ≥4 weeks with z-score "
                "≥1.5 std, file a plan_proposal to update IDENTITY.md describing "
                "the new baseline. Manual trigger; normally runs weekly via "
                "governance handler. Never auto-applies — requires user approval."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
