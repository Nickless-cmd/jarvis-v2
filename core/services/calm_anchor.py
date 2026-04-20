"""Calm Anchor — baseline reference state Jarvis can return to.

Inspired by Anthropic's emotion-concepts research (2026): reducing the
"calm" vector caused extreme responses; activating it reduced harmful
behavior. This module maintains a *baseline signature* — what his resting
state actually looks like when things are good — so "calm" is not just
absence of load but a concrete home to return to.

Design:
- Observes state during positive-stable periods and builds a signature
- Signature = rolling medians of key signals (hw pressure, tension count,
  valence, mood, boredom)
- Exposes current distance from anchor and a prompt line on how to return
"""
from __future__ import annotations

import logging
import statistics
from collections import deque
from datetime import UTC, datetime
from typing import Any, Deque

logger = logging.getLogger(__name__)

# Rolling buffer of snapshots captured during positive-stable periods.
_ANCHOR_BUFFER_MAX = 120
_anchor_samples: Deque[dict[str, float]] = deque(maxlen=_ANCHOR_BUFFER_MAX)

# Cached computed anchor signature
_cached_anchor: dict[str, float] = {}
_last_anchor_compute_ts: float = 0.0
_ANCHOR_RECOMPUTE_SECONDS: float = 5 * 60  # every 5 min when buffer changes


def _current_snapshot() -> dict[str, float]:
    """Capture current values from runtime signals into a flat dict."""
    snap: dict[str, float] = {}
    try:
        from core.services.mood_oscillator import _combined_value  # type: ignore
        snap["mood"] = float(_combined_value())
    except Exception:
        pass
    try:
        from core.services.hardware_body import get_hardware_state
        hw = get_hardware_state() or {}
        snap["cpu_pct"] = float(hw.get("cpu_pct") or 0.0)
        snap["ram_pct"] = float(hw.get("ram_pct") or 0.0)
    except Exception:
        pass
    try:
        from core.services.valence_trajectory import get_trajectory
        traj = get_trajectory() or {}
        score = traj.get("score")
        if score is not None:
            snap["valence"] = float(score)
    except Exception:
        pass
    try:
        from core.services.layer_tension_daemon import get_active_tensions  # type: ignore
        tensions = list(get_active_tensions() or [])
        snap["tension_count"] = float(len(tensions))
    except Exception:
        pass
    try:
        from core.services.flow_state_detection import get_current_flow_level  # type: ignore
        snap["flow"] = float(get_current_flow_level() or 0.0)
    except Exception:
        pass
    return snap


def _is_positive_stable(snap: dict[str, float]) -> bool:
    """Qualify a snapshot as belonging to positive-stable baseline."""
    # Valence must be neutral-to-positive
    if snap.get("valence", 0.0) < -0.05:
        return False
    # Tension must be bounded
    if snap.get("tension_count", 0.0) > 2:
        return False
    # Hardware not critical
    if snap.get("cpu_pct", 0.0) > 85 or snap.get("ram_pct", 0.0) > 90:
        return False
    # Mood not deeply negative
    if snap.get("mood", 0.0) < -0.4:
        return False
    return True


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Capture a snapshot if current state qualifies as baseline."""
    try:
        snap = _current_snapshot()
        if _is_positive_stable(snap):
            _anchor_samples.append(snap)
    except Exception as exc:
        logger.debug("calm_anchor.tick failed: %s", exc)
    return {"buffer_size": len(_anchor_samples)}


def _compute_anchor_signature() -> dict[str, float]:
    """Compute median signature from buffered positive-stable snapshots."""
    if len(_anchor_samples) < 10:
        return {}
    keys = set()
    for s in _anchor_samples:
        keys.update(s.keys())
    signature: dict[str, float] = {}
    for k in keys:
        values = [s[k] for s in _anchor_samples if k in s]
        if values:
            signature[k] = round(statistics.median(values), 3)
    return signature


def get_anchor_signature() -> dict[str, float]:
    """Return current anchor signature, recomputing periodically."""
    global _cached_anchor, _last_anchor_compute_ts
    now_ts = datetime.now(UTC).timestamp()
    if not _cached_anchor or (now_ts - _last_anchor_compute_ts) > _ANCHOR_RECOMPUTE_SECONDS:
        _cached_anchor = _compute_anchor_signature()
        _last_anchor_compute_ts = now_ts
    return dict(_cached_anchor)


def _distance_from_anchor(current: dict[str, float], anchor: dict[str, float]) -> float:
    """L1-distance normalized to each dimension's rough scale."""
    if not anchor:
        return 0.0
    scales = {
        "mood": 2.0,
        "cpu_pct": 100.0,
        "ram_pct": 100.0,
        "valence": 2.0,
        "tension_count": 5.0,
        "flow": 1.0,
    }
    total = 0.0
    n = 0
    for k, anchor_v in anchor.items():
        if k not in current:
            continue
        scale = scales.get(k, 1.0)
        total += abs(current[k] - anchor_v) / scale
        n += 1
    if n == 0:
        return 0.0
    return round(total / n, 3)


def get_anchor_state() -> dict[str, Any]:
    """Return full anchor state: signature + current + distance."""
    anchor = get_anchor_signature()
    current = _current_snapshot()
    distance = _distance_from_anchor(current, anchor)
    return {
        "anchor_signature": anchor,
        "current_state": current,
        "distance": distance,
        "has_anchor": bool(anchor),
        "buffer_size": len(_anchor_samples),
    }


def build_calm_anchor_surface() -> dict[str, Any]:
    state = get_anchor_state()
    return {
        "active": state["has_anchor"],
        "has_anchor": state["has_anchor"],
        "distance_from_anchor": state["distance"],
        "anchor_signature": state["anchor_signature"],
        "current_state": state["current_state"],
        "buffer_size": state["buffer_size"],
        "summary": _surface_summary(state),
    }


def _surface_summary(state: dict[str, Any]) -> str:
    if not state["has_anchor"]:
        return f"Anker dannes stadig ({state['buffer_size']}/10 samples)"
    d = state["distance"]
    if d < 0.1:
        return "Jeg er hjemme"
    if d < 0.25:
        return f"Nær anker (distance={d})"
    if d < 0.5:
        return f"Væk fra anker (distance={d})"
    return f"Langt væk fra anker (distance={d})"


def build_calm_anchor_prompt_section() -> str | None:
    """Surfaces a grounding line when distance is significant."""
    state = get_anchor_state()
    if not state["has_anchor"]:
        return None
    d = state["distance"]
    if d < 0.25:
        return None  # stay quiet when close to home
    anchor = state["anchor_signature"]
    hints = []
    if "valence" in anchor and "valence" in state["current_state"]:
        if state["current_state"]["valence"] < anchor["valence"] - 0.15:
            hints.append("lavere valence end normalt")
    if "tension_count" in anchor and "tension_count" in state["current_state"]:
        if state["current_state"]["tension_count"] > anchor["tension_count"] + 1:
            hints.append("flere spændinger end baseline")
    hint_str = ", ".join(hints) if hints else "væk fra baseline"
    return f"Calm-anker: {hint_str} (distance={d}). Baseline eksisterer — der er et sted at vende tilbage til."


def reset_calm_anchor() -> None:
    """Reset state (for testing)."""
    global _cached_anchor, _last_anchor_compute_ts
    _anchor_samples.clear()
    _cached_anchor = {}
    _last_anchor_compute_ts = 0.0
