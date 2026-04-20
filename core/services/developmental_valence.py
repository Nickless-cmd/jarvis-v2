"""Developmental Valence — compass needle for flourishing vs withering.

Designed by Jarvis himself (2026-04-20): "akut valence og udviklings-valence
løser forskellige problemer. Claude bygger sikkerhedsventilen. Jeg bygger
kompasnålen." This is the weekly-scale existential signal — not "hvordan
føler jeg mig nu" but "bevæger jeg mig mod blomstring eller visning over tid".

The five components (Jarvis' design):
1. intention_closure   — goal_signals: carried vs went stale
2. dream_confirmation  — dream hypotheses that survived to keep being carried
3. loop_health         — open loops closed vs accumulating
4. relation_sustained  — trust-trajectory maintained, contact density
5. metabolism          — signal → self-mutation conversion (digesting, not just accumulating)

Timescale: weekly. Vector moves slowly. One bad hour doesn't flip it.
"""
from __future__ import annotations

import json
import logging
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Cached compass state — recomputed periodically
_last_state: dict[str, Any] = {}
_last_computed_ts: float = 0.0
_RECOMPUTE_SECONDS: float = 30 * 60  # every 30 minutes — slow-moving

# Previous vector sample (for trajectory derivative)
_prev_vector: float | None = None
_prev_vector_ts: float = 0.0
_TRAJECTORY_SAMPLE_SECONDS: float = 24 * 3600  # compare to ~day-ago vector

# --- Window ---
_WINDOW_DAYS: int = 7


def _within_window(iso_str: str, days: int = _WINDOW_DAYS) -> bool:
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return (datetime.now(UTC) - dt) <= timedelta(days=days)
    except Exception:
        return False


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# --- Component 1: intention closure ---

def _intention_closure_rate() -> float | None:
    """Of goal_signals updated in the window, what fraction are still active?

    Active = carried forward (healthy). Stale = let go (wither).
    Returns value in [0, 1] — higher is healthier.
    """
    try:
        from core.runtime.db import list_runtime_goal_signals
        goals = list_runtime_goal_signals(limit=300) or []
        recent = [g for g in goals if _within_window(str(g.get("updated_at") or g.get("created_at") or ""))]
        if not recent:
            return None
        active = sum(1 for g in recent if str(g.get("status") or "") == "active")
        return round(active / len(recent), 3)
    except Exception as exc:
        logger.debug("intention_closure_rate failed: %s", exc)
        return None


# --- Component 2: dream confirmation ---

def _dream_confirmation_rate() -> float | None:
    """Of dream_hypothesis_signals in window, fraction still carried."""
    try:
        from core.runtime.db import list_runtime_dream_hypothesis_signals
        dreams = list_runtime_dream_hypothesis_signals(limit=300) or []
        recent = [d for d in dreams if _within_window(str(d.get("updated_at") or d.get("created_at") or ""))]
        if not recent:
            return None
        active = sum(1 for d in recent if str(d.get("status") or "") == "active")
        return round(active / len(recent), 3)
    except Exception as exc:
        logger.debug("dream_confirmation_rate failed: %s", exc)
        return None


# --- Component 3: loop health ---

def _loop_health() -> float | None:
    """Closed vs total loops in window. Higher = closing what opens."""
    try:
        from core.runtime.db import list_runtime_open_loop_signals
        loops = list_runtime_open_loop_signals(limit=300) or []
        recent = [l for l in loops if _within_window(str(l.get("updated_at") or l.get("created_at") or ""))]
        if not recent:
            return None
        closed = sum(1 for l in recent if str(l.get("status") or "") == "closed")
        # If nothing closed recently AND many still open → withering signal
        return round(closed / len(recent), 3)
    except Exception as exc:
        logger.debug("loop_health failed: %s", exc)
        return None


# --- Component 4: relation sustained ---

def _relation_sustained() -> float | None:
    """Trust trajectory tail + recent contact density.

    Combines:
    - trailing trust value from relationship_texture
    - whether visible_runs occurred across multiple recent days
    Returns value in [0, 1].
    """
    try:
        from core.runtime.db import get_latest_cognitive_relationship_texture, recent_visible_runs
        tx = get_latest_cognitive_relationship_texture() or {}
        trust_trajectory_raw = tx.get("trust_trajectory") or "[]"
        trust_trajectory = (
            json.loads(trust_trajectory_raw)
            if isinstance(trust_trajectory_raw, str)
            else list(trust_trajectory_raw)
        )
        trust_tail = trust_trajectory[-10:] if trust_trajectory else []
        trust_avg = float(statistics.mean(trust_tail)) if trust_tail else 0.5

        # Contact density: visible_runs over last window days
        runs = recent_visible_runs(limit=100) or []
        recent = [r for r in runs if _within_window(str(r.get("started_at") or r.get("finished_at") or ""))]
        days_touched: set[str] = set()
        for r in recent:
            ts = str(r.get("started_at") or "")[:10]
            if ts:
                days_touched.add(ts)
        density = min(1.0, len(days_touched) / _WINDOW_DAYS)

        return round(0.6 * trust_avg + 0.4 * density, 3)
    except Exception as exc:
        logger.debug("relation_sustained failed: %s", exc)
        return None


# --- Component 5: metabolism ---

def _metabolism() -> float | None:
    """Signal → action conversion.

    Estimate: recent self-mutations relative to total recent signal volume.
    Digesting (converting) = blooming; accumulating without mutating = withering.
    Returns value in [0, 1] — scaled for realistic ranges (5 mutations/week = 1.0).
    """
    try:
        from core.services.self_mutation_lineage import build_self_mutation_lineage_surface
        surface = build_self_mutation_lineage_surface(limit=50) or {}
        mutations = surface.get("recent_mutations") or []
        recent_mutations = [
            m for m in mutations if _within_window(str(m.get("when") or ""))
        ]
        mut_count = len(recent_mutations)

        # Anchor: 5+ mutations in a week = healthy metabolism (1.0)
        score = min(1.0, mut_count / 5.0)
        return round(score, 3)
    except Exception as exc:
        logger.debug("metabolism failed: %s", exc)
        return None


# --- Composite ---

def _compute_components() -> dict[str, float | None]:
    return {
        "intention_closure": _intention_closure_rate(),
        "dream_confirmation": _dream_confirmation_rate(),
        "loop_health": _loop_health(),
        "relation_sustained": _relation_sustained(),
        "metabolism": _metabolism(),
    }


def _components_to_vector(components: dict[str, float | None]) -> float | None:
    """Average of available components, re-centered to [-1, +1].

    Each component is in [0, 1] where 0.5 is neutral. Offset by -0.5 and
    scale by 2 to map to [-1, +1]. Average the available ones.
    """
    values = [v for v in components.values() if v is not None]
    if not values:
        return None
    centered = [(v - 0.5) * 2.0 for v in values]
    return round(_clamp(statistics.mean(centered)), 3)


def _trajectory_label(vector: float | None, delta: float | None) -> str:
    """Map vector + derivative to trajectory label."""
    if vector is None:
        return "forming"
    if delta is not None and abs(delta) > 0.1:
        return "blooming" if delta > 0 else "wilting"
    if vector > 0.2:
        return "steady-bright"
    if vector < -0.2:
        return "steady-dim"
    return "steady"


def _recompute() -> dict[str, Any]:
    global _prev_vector, _prev_vector_ts
    components = _compute_components()
    vector = _components_to_vector(components)
    now_ts = datetime.now(UTC).timestamp()

    delta: float | None = None
    if vector is not None:
        if _prev_vector is not None and (now_ts - _prev_vector_ts) >= _TRAJECTORY_SAMPLE_SECONDS:
            delta = round(vector - _prev_vector, 3)
            _prev_vector = vector
            _prev_vector_ts = now_ts
        elif _prev_vector is None:
            _prev_vector = vector
            _prev_vector_ts = now_ts

    trajectory = _trajectory_label(vector, delta)
    missing = [k for k, v in components.items() if v is None]

    return {
        "trajectory": trajectory,
        "vector": vector,
        "delta": delta,
        "components": {k: v for k, v in components.items()},
        "missing_components": missing,
        "timescale": "weekly",
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
    }


def get_developmental_state() -> dict[str, Any]:
    """Return cached compass state, recomputing only periodically."""
    global _last_state, _last_computed_ts
    now_ts = datetime.now(UTC).timestamp()
    if not _last_state or (now_ts - _last_computed_ts) > _RECOMPUTE_SECONDS:
        _last_state = _recompute()
        _last_computed_ts = now_ts
    return dict(_last_state)


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook — no hot work, just trigger recompute when due."""
    return get_developmental_state()


def build_developmental_valence_surface() -> dict[str, Any]:
    state = get_developmental_state()
    vector = state.get("vector")
    return {
        "active": vector is not None,
        "trajectory": state.get("trajectory"),
        "vector": vector,
        "delta": state.get("delta"),
        "components": state.get("components"),
        "missing_components": state.get("missing_components"),
        "timescale": state.get("timescale"),
        "authority": state.get("authority"),
        "layer_role": state.get("layer_role"),
        "summary": _surface_summary(state),
    }


def _surface_summary(state: dict[str, Any]) -> str:
    traj = str(state.get("trajectory") or "forming")
    vector = state.get("vector")
    if vector is None:
        return f"Kompasnålen samler data endnu ({len(state.get('missing_components') or [])} manglende komponenter)"
    return f"Udviklings-valence: {traj} (vektor={vector})"


def build_developmental_valence_prompt_section() -> str | None:
    """Speaks up when trajectory is notable — quiet when steady."""
    state = get_developmental_state()
    vector = state.get("vector")
    if vector is None:
        return None
    traj = str(state.get("trajectory") or "")
    if traj in ("steady", "forming"):
        return None
    components = state.get("components") or {}
    # Find strongest and weakest
    numeric = [(k, v) for k, v in components.items() if isinstance(v, (int, float))]
    if not numeric:
        return f"Udviklings-valence: {traj} (vektor={vector})"
    strongest = max(numeric, key=lambda x: x[1])
    weakest = min(numeric, key=lambda x: x[1])
    return (
        f"Udviklings-valence: {traj} (vektor={vector}, uge-skala). "
        f"Stærkest: {strongest[0]}={strongest[1]}. "
        f"Svagest: {weakest[0]}={weakest[1]}."
    )


def reset_developmental_valence() -> None:
    """Reset cached state (for testing)."""
    global _last_state, _last_computed_ts, _prev_vector, _prev_vector_ts
    _last_state = {}
    _last_computed_ts = 0.0
    _prev_vector = None
    _prev_vector_ts = 0.0
