"""Personality drift detection — has Jarvis' baseline shifted?

Tracks rolling mood snapshots over time. When the moving average of any
mood dimension drifts more than X std deviations from the long-term
baseline, surface a "drift detected" signal in awareness so Jarvis (and
the user via Mission Control) can notice.

This is the foundation for the user's "dynamic personality vector"
ambition — track WHAT his baseline self looks like, and notice when it
shifts. Does not auto-correct anything; just surfaces.

Storage: state_store JSON. Snapshots taken via heartbeat or daemon
(periodic_jobs_scheduler).
"""
from __future__ import annotations

import logging
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "personality_drift_snapshots"
_MAX_SNAPSHOTS = 200       # rolling window
_DRIFT_THRESHOLD_STD = 1.5  # how many std-devs counts as drift
_BASELINE_MIN_SAMPLES = 20  # need this many before drift detection works


def _load_snapshots() -> list[dict[str, Any]]:
    raw = load_json(_STATE_KEY, [])
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict)]


def _save_snapshots(snapshots: list[dict[str, Any]]) -> None:
    # Keep only the most recent _MAX_SNAPSHOTS
    trimmed = snapshots[-_MAX_SNAPSHOTS:]
    save_json(_STATE_KEY, trimmed)


def take_snapshot() -> dict[str, Any]:
    """Capture current mood — call from heartbeat or daemon periodically."""
    try:
        from core.services.mood_oscillator import get_current_mood, get_mood_intensity
        mood_name = str(get_current_mood() or "")
        intensity = float(get_mood_intensity() or 0.0)
        mood = {mood_name: intensity} if mood_name else {}
    except Exception as exc:
        logger.debug("personality_drift: mood read failed: %s", exc)
        return {"status": "error", "error": str(exc)}
    if not isinstance(mood, dict):
        return {"status": "error", "error": "mood not a dict"}
    snapshot = {
        "ts": datetime.now(UTC).isoformat(),
        "mood": {k: round(float(v), 3) for k, v in mood.items() if isinstance(v, (int, float))},
    }
    snapshots = _load_snapshots()
    snapshots.append(snapshot)
    _save_snapshots(snapshots)
    return {"status": "ok", "snapshot": snapshot, "total_snapshots": len(snapshots)}


def compute_baseline(*, lookback_days: int = 14) -> dict[str, dict[str, float]]:
    """Mean + stddev for each mood dimension over the lookback window."""
    snapshots = _load_snapshots()
    if not snapshots:
        return {}
    cutoff = (datetime.now(UTC) - timedelta(days=lookback_days)).isoformat()
    relevant = [s for s in snapshots if str(s.get("ts", "")) >= cutoff]
    if not relevant:
        return {}
    by_dim: dict[str, list[float]] = {}
    for s in relevant:
        for dim, val in (s.get("mood") or {}).items():
            if isinstance(val, (int, float)):
                by_dim.setdefault(dim, []).append(float(val))
    baseline: dict[str, dict[str, float]] = {}
    for dim, values in by_dim.items():
        if len(values) < 2:
            continue
        baseline[dim] = {
            "mean": round(statistics.mean(values), 3),
            "stdev": round(statistics.stdev(values), 3) if len(values) >= 2 else 0.0,
            "n": len(values),
        }
    return baseline


def detect_drift(*, lookback_days: int = 14, recent_window: int = 10) -> dict[str, Any]:
    """Compare recent snapshot mean vs long-term baseline."""
    snapshots = _load_snapshots()
    if len(snapshots) < _BASELINE_MIN_SAMPLES:
        return {
            "status": "ok",
            "drift_detected": False,
            "reason": f"need {_BASELINE_MIN_SAMPLES}+ snapshots, have {len(snapshots)}",
            "drifts": [],
        }
    baseline = compute_baseline(lookback_days=lookback_days)
    if not baseline:
        return {"status": "ok", "drift_detected": False, "reason": "no baseline available", "drifts": []}
    recent = snapshots[-recent_window:]
    recent_means: dict[str, float] = {}
    for dim, info in baseline.items():
        values = [
            float((s.get("mood") or {}).get(dim))
            for s in recent
            if isinstance((s.get("mood") or {}).get(dim), (int, float))
        ]
        if values:
            recent_means[dim] = sum(values) / len(values)

    drifts: list[dict[str, Any]] = []
    for dim, recent_mean in recent_means.items():
        info = baseline[dim]
        std = info.get("stdev") or 0.0
        if std <= 0:
            continue
        z_score = (recent_mean - info["mean"]) / std
        if abs(z_score) >= _DRIFT_THRESHOLD_STD:
            drifts.append({
                "dimension": dim,
                "recent_mean": round(recent_mean, 3),
                "baseline_mean": info["mean"],
                "baseline_stdev": std,
                "z_score": round(z_score, 2),
                "direction": "up" if z_score > 0 else "down",
            })
    return {
        "status": "ok",
        "drift_detected": bool(drifts),
        "drifts": drifts,
        "baseline_window_days": lookback_days,
        "recent_window_size": recent_window,
        "total_snapshots": len(snapshots),
    }


def personality_drift_section() -> str | None:
    """Awareness section when drift detected — surfaces in prompt."""
    result = detect_drift()
    if not result.get("drift_detected"):
        return None
    drifts = result.get("drifts") or []
    lines = ["🔄 Personlighedsdrift opdaget (sidste vindue vs baseline):"]
    for d in drifts[:3]:
        arrow = "↑" if d["direction"] == "up" else "↓"
        lines.append(
            f"  {arrow} {d['dimension']}: {d['baseline_mean']:.2f} → {d['recent_mean']:.2f} (z={d['z_score']:+.1f})"
        )
    lines.append("Notér det — skift i baseline kan være meningsfuld.")
    return "\n".join(lines)


def _exec_personality_drift_check(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "drift": detect_drift(),
        "baseline": compute_baseline(lookback_days=int(args.get("lookback_days") or 14)),
    }


def _exec_personality_drift_snapshot(args: dict[str, Any]) -> dict[str, Any]:
    return take_snapshot()


PERSONALITY_DRIFT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "personality_drift_check",
            "description": (
                "Compare recent mood snapshots vs long-term baseline. Surfaces "
                "drift when any dimension shifts ≥1.5 std devs. Optional "
                "lookback_days (default 14)."
            ),
            "parameters": {
                "type": "object",
                "properties": {"lookback_days": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "personality_drift_snapshot",
            "description": "Take a manual snapshot now (normally handled by daemon every few hours).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
