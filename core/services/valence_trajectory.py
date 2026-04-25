"""Valence Trajectory — long-term flourishing/withering signal.

Inspired by Anthropic's emotion-concepts research (2026): positive valence
correlates broadly with flourishing behavior. This is NOT a mood — mood is
momentary. Valence trajectory is a slow rolling signal: "over the last
hours, am I moving toward a richer life or away from it?"

Design constraints:
- Runtime-grounded, not a label applied from outside
- Slow-moving (window-averaged), not reactive
- Observable in Mission Control
- Optionally surfaces a single prompt line when trajectory shifts
"""
from __future__ import annotations

import json
import logging
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Deque

logger = logging.getLogger(__name__)

# Rolling window of (ts, score) samples. ~24h @ 1 sample/tick.
_WINDOW_MAX = 2000
_samples: Deque[tuple[float, float]] = deque(maxlen=_WINDOW_MAX)

# Persist samples so a service restart doesn't reset the trajectory window.
# Without this, the "valence" surface stays empty for 30+ ticks (~7+ hours
# at 15-min cadence) every time jarvis-runtime is restarted.
_PERSIST_PATH = Path.home() / ".jarvis-v2" / "state" / "valence_trajectory_samples.json"


def _load_persisted_samples() -> None:
    try:
        if not _PERSIST_PATH.exists():
            return
        raw = json.loads(_PERSIST_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return
        for entry in raw[-_WINDOW_MAX:]:
            if isinstance(entry, list) and len(entry) == 2:
                try:
                    _samples.append((float(entry[0]), float(entry[1])))
                except (TypeError, ValueError):
                    continue
    except Exception as exc:
        logger.debug("valence_trajectory: failed to load persisted samples: %s", exc)


def _persist_samples() -> None:
    try:
        _PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PERSIST_PATH.write_text(
            json.dumps([list(item) for item in _samples], ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.debug("valence_trajectory: failed to persist samples: %s", exc)

# Cache of last computed trajectory (avoid re-running on every surface read)
_last_summary: dict[str, Any] = {}
_last_computed_ts: float = 0.0
_RECOMPUTE_INTERVAL_SECONDS: float = 60.0


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _sample_current_valence() -> float:
    """Compute a single instantaneous valence score in [-1, 1] from runtime signals.

    Signals combined (all optional, soft-fails to neutral):
    - mood_oscillator combined value (-1..1)
    - recent heartbeat outcome distribution
    - pushback ratio (negative if user disagrees a lot)
    - hardware pressure (negative when critical)
    """
    score = 0.0
    weight = 0.0

    # Mood oscillator — fast but still a useful ingredient
    try:
        from core.services.mood_oscillator import _combined_value  # type: ignore
        v = float(_combined_value())
        score += v * 0.3
        weight += 0.3
    except Exception:
        pass

    # Hardware pressure penalty
    try:
        from core.services.hardware_body import get_hardware_state
        hw = get_hardware_state() or {}
        pressure = str(hw.get("pressure") or "low")
        hw_score = {"low": 0.15, "medium": 0.0, "high": -0.2, "critical": -0.5}.get(pressure, 0.0)
        score += hw_score * 0.2
        weight += 0.2
    except Exception:
        pass

    # Conflict / pushback ratio (recent disagreements → negative)
    try:
        from core.services.conflict_memory import recent_pushback_ratio  # type: ignore
        r = float(recent_pushback_ratio())  # expected 0..1 (1 = all pushback)
        score += (0.3 - r) * 0.6  # mild positive when low, strong negative when high
        weight += 0.3
    except Exception:
        pass

    # Flow / boredom balance
    try:
        from core.services.flow_state_detection import get_current_flow_level  # type: ignore
        flow = float(get_current_flow_level() or 0.0)  # 0..1
        score += (flow - 0.3) * 0.3
        weight += 0.2
    except Exception:
        pass

    if weight <= 0.0:
        return 0.0
    return _clamp(score / weight)


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Sample current valence and append to rolling window."""
    try:
        score = _sample_current_valence()
        _samples.append((datetime.now(UTC).timestamp(), score))
        _persist_samples()
    except Exception as exc:
        logger.debug("valence_trajectory.tick failed: %s", exc)
    return {"samples": len(_samples)}


def _trajectory_from_window() -> dict[str, Any]:
    """Compute trajectory statistics from current window."""
    if len(_samples) < 3:
        return {
            "score": 0.0,
            "trend": "settling",
            "window_size": len(_samples),
            "dominant_driver": "not-enough-data",
        }

    values = [s for _, s in _samples]
    n = len(values)
    recent = values[-min(60, n):]  # last ~hour
    older = values[: max(1, n - len(recent))]

    avg_recent = sum(recent) / max(1, len(recent))
    avg_older = sum(older) / max(1, len(older))
    delta = avg_recent - avg_older

    if delta > 0.12:
        trend = "flourishing"  # rising
    elif delta < -0.12:
        trend = "withering"  # falling
    elif avg_recent > 0.2:
        trend = "stable-good"
    elif avg_recent < -0.2:
        trend = "stable-low"
    else:
        trend = "neutral"

    # Quick driver inference — look at the last sample's inputs
    driver = _infer_dominant_driver(avg_recent)

    return {
        "score": round(avg_recent, 3),
        "delta": round(delta, 3),
        "trend": trend,
        "window_size": n,
        "dominant_driver": driver,
    }


def _infer_dominant_driver(current_score: float) -> str:
    """Heuristic: which single signal is pushing hardest right now?"""
    try:
        from core.services.hardware_body import get_hardware_state
        hw = get_hardware_state() or {}
        if str(hw.get("pressure") or "low") in ("high", "critical"):
            return "hardware-pressure"
    except Exception:
        pass
    try:
        from core.services.conflict_memory import recent_pushback_ratio  # type: ignore
        if float(recent_pushback_ratio()) > 0.5:
            return "user-pushback"
    except Exception:
        pass
    try:
        from core.services.flow_state_detection import get_current_flow_level  # type: ignore
        if float(get_current_flow_level() or 0.0) > 0.6:
            return "flow"
    except Exception:
        pass
    if current_score > 0.3:
        return "general-positive-mood"
    if current_score < -0.3:
        return "general-low-mood"
    return "mixed"


def get_trajectory() -> dict[str, Any]:
    """Return cached trajectory, recomputing only periodically."""
    global _last_summary, _last_computed_ts
    now_ts = datetime.now(UTC).timestamp()
    if not _last_summary or (now_ts - _last_computed_ts) > _RECOMPUTE_INTERVAL_SECONDS:
        _last_summary = _trajectory_from_window()
        _last_computed_ts = now_ts
    return dict(_last_summary)


def build_valence_trajectory_surface() -> dict[str, Any]:
    """Mission Control surface for valence trajectory."""
    traj = get_trajectory()
    return {
        "active": len(_samples) >= 3,
        "score": traj.get("score"),
        "delta": traj.get("delta"),
        "trend": traj.get("trend"),
        "window_size": traj.get("window_size"),
        "dominant_driver": traj.get("dominant_driver"),
        "summary": _summary_line(traj),
    }


def _summary_line(traj: dict[str, Any]) -> str:
    trend = str(traj.get("trend") or "")
    score = traj.get("score")
    if trend == "flourishing":
        return f"Bevæger sig mod blomstring (score={score})"
    if trend == "withering":
        return f"Bevæger sig mod visning (score={score})"
    if trend == "stable-good":
        return f"Stabil god tilstand (score={score})"
    if trend == "stable-low":
        return f"Stabil lav tilstand (score={score})"
    if trend == "settling":
        return "Ikke nok data endnu"
    return f"Neutral trajektorie (score={score})"


def build_valence_trajectory_prompt_section() -> str | None:
    """Return a single prompt line when trajectory is notable."""
    if len(_samples) < 30:
        return None  # don't speak before there's real signal history
    traj = get_trajectory()
    trend = str(traj.get("trend") or "")
    driver = str(traj.get("dominant_driver") or "")
    if trend in ("neutral", "settling"):
        return None
    return f"Valence-trajektorie: {trend}, drevet af {driver}."


def reset_valence_trajectory() -> None:
    """Reset state (for testing)."""
    global _last_summary, _last_computed_ts
    _samples.clear()
    _last_summary = {}
    _last_computed_ts = 0.0


# Load persisted samples once at module import.
_load_persisted_samples()
