"""Emotion Concepts — discrete, event-driven Lag-2 emotional signals.

25 granular emotion concepts above the 4 continuous Lag-1 axes (confidence,
curiosity, frustration, fatigue). Each concept is a transient in-memory signal
with intensity, decay, and influence on Lag-1 axes.

Max 5 active concepts at any time; weakest is pruned on overflow. Decay is
0.85× per full tick (~900 s). DB persistence is fire-and-forget for Mission
Control observability only.
"""
from __future__ import annotations

import logging
import queue
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_MAX_ACTIVE = 5
_DECAY_FACTOR = 0.85        # multiplied per full tick (~900 s)
_TICK_SECONDS = 900.0       # reference tick length for decay exponent
_MIN_INTENSITY = 0.05

# In-memory active concepts keyed by concept name
_active: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()

_listener_thread: threading.Thread | None = None
_listener_running: bool = False

# ---------------------------------------------------------------------------
# Influence map: concept → {lag1_axis: base_delta_at_intensity_1.0}
# ---------------------------------------------------------------------------
INFLUENCE_MAP: dict[str, dict[str, float]] = {
    "confusion":           {"frustration": 0.2, "curiosity": 0.1},
    "insight":             {"confidence": 0.2, "frustration": -0.3},
    "doubt":               {"confidence": -0.1},
    "surprise":            {"curiosity": 0.15},
    "curiosity_narrow":    {"curiosity": 0.1},
    "pride":               {"confidence": 0.2},
    "shame":               {"confidence": -0.3, "frustration": 0.2},
    "accomplishment":      {"fatigue": -0.2, "confidence": 0.1},
    "frustration_blocked": {"frustration": 0.4},
    "competence":          {"confidence": 0.15, "fatigue": -0.1},
    "trust_deep":          {},
    "belonging":           {"frustration": -0.1},
    "empathy":             {},
    "gratitude":           {"confidence": 0.1},
    "loneliness":          {"fatigue": 0.15, "curiosity": -0.1},
    "calm":                {"fatigue": -0.1, "frustration": -0.1},
    "relief":              {"frustration": -0.3},
    "acceptance":          {},
    "tension":             {"frustration": 0.1},
    "anticipation":        {"curiosity": 0.2},
    "resolve":             {"confidence": 0.2},
    "caution":             {},
    "stuck":               {"frustration": 0.2, "fatigue": 0.2},
    "overwhelm":           {"fatigue": 0.3, "frustration": 0.2},
    "vigilance":           {"curiosity": 0.1},
}

# Bearing pushes: concept → target bearing string
BEARING_PUSH_MAP: dict[str, str] = {
    "trust_deep":  "open",
    "empathy":     "grounded",
    "acceptance":  "steady",
    "resolve":     "forward",
    "caution":     "careful",
    "vigilance":   "forward",
}

VALID_CONCEPTS: frozenset[str] = frozenset(INFLUENCE_MAP.keys())
_LAG1_AXES = ("confidence", "curiosity", "frustration", "fatigue")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def trigger_emotion_concept(
    concept: str,
    intensity: float,
    trigger: str = "",
    source: str = "",
) -> dict[str, Any] | None:
    """Create or strengthen an active emotion concept instance.

    If the concept is already active, blends the new intensity in (adds 50%
    of incoming intensity) rather than replacing. Returns the signal dict, or
    None if the concept name is unknown.
    """
    if concept not in VALID_CONCEPTS:
        logger.debug("emotion_concepts: unknown concept %r — ignored", concept)
        return None

    intensity = max(0.0, min(1.0, float(intensity)))
    now = datetime.now(UTC)
    expires_at = (now + timedelta(hours=2)).isoformat()

    with _lock:
        existing = _active.get(concept)
        if existing:
            blended = min(1.0, existing["intensity"] + intensity * 0.5)
            direction = "rising" if blended > existing["intensity"] else "steady"
            existing.update({
                "intensity": blended,
                "direction": direction,
                "trigger": trigger or existing["trigger"],
                "expires_at": expires_at,
            })
            signal = existing
        else:
            signal = {
                "concept": concept,
                "intensity": intensity,
                "direction": "rising",
                "trigger": trigger,
                "source": source,
                "expires_at": expires_at,
                "influences": list(INFLUENCE_MAP[concept].keys()),
                "created_at": now.isoformat(),
            }
            _active[concept] = signal
            _prune_if_needed()

    _persist_async(dict(signal))
    logger.debug("emotion_concepts: triggered %s intensity=%.2f", concept, intensity)
    return dict(signal)


def tick_emotion_concepts(elapsed_seconds: float) -> None:
    """Decay all active concepts proportional to elapsed time.

    Uses a fractional exponent so decay is smooth regardless of tick interval.
    Removes concepts that fall below _MIN_INTENSITY.
    """
    tick_fraction = elapsed_seconds / _TICK_SECONDS
    decay = _DECAY_FACTOR ** tick_fraction

    with _lock:
        to_remove = []
        for concept, signal in _active.items():
            new_intensity = signal["intensity"] * decay
            if new_intensity < _MIN_INTENSITY:
                to_remove.append(concept)
            else:
                old = signal["intensity"]
                signal["intensity"] = new_intensity
                signal["direction"] = (
                    "falling" if new_intensity < old * 0.95 else "steady"
                )
        for concept in to_remove:
            del _active[concept]


def get_active_emotion_concepts() -> list[dict[str, Any]]:
    """Return all active concepts above threshold, sorted by intensity descending."""
    now_iso = datetime.now(UTC).isoformat()
    with _lock:
        result = [
            dict(s)
            for s in _active.values()
            if s["intensity"] > _MIN_INTENSITY and s.get("expires_at", "Z") >= now_iso
        ]
    return sorted(result, key=lambda s: s["intensity"], reverse=True)


def get_lag1_influence_deltas() -> dict[str, float]:
    """Compute cumulative influence on Lag-1 axes from all active concepts.

    Each concept's base delta is multiplied by its current intensity. Total per
    axis is clamped to [-0.5, 0.5] to avoid runaway shifts.
    """
    deltas: dict[str, float] = {ax: 0.0 for ax in _LAG1_AXES}
    for signal in get_active_emotion_concepts():
        concept = signal["concept"]
        intensity = signal["intensity"]
        for axis, base_delta in INFLUENCE_MAP.get(concept, {}).items():
            if axis in deltas:
                deltas[axis] += base_delta * intensity
    for axis in deltas:
        deltas[axis] = max(-0.5, min(0.5, deltas[axis]))
    return deltas


def get_bearing_push() -> str | None:
    """Return bearing push from the highest-intensity bearing-influencing concept.

    Only concepts in BEARING_PUSH_MAP participate. Returns None if none active.
    """
    best_concept: str | None = None
    best_intensity = 0.0
    for signal in get_active_emotion_concepts():
        concept = signal["concept"]
        if concept in BEARING_PUSH_MAP and signal["intensity"] > best_intensity:
            best_concept = concept
            best_intensity = signal["intensity"]
    return BEARING_PUSH_MAP[best_concept] if best_concept else None


def build_emotion_concept_surface() -> dict[str, Any]:
    """MC surface: active concepts + influence deltas."""
    active = get_active_emotion_concepts()
    deltas = get_lag1_influence_deltas()
    return {
        "active": bool(active),
        "active_count": len(active),
        "concepts": active[:5],
        "lag1_influence_deltas": deltas,
        "max_active_limit": _MAX_ACTIVE,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _prune_if_needed() -> None:
    """Remove the weakest concept when over limit. Must be called under _lock."""
    while len(_active) > _MAX_ACTIVE:
        weakest = min(_active.keys(), key=lambda k: _active[k]["intensity"])
        del _active[weakest]


def _persist_async(signal: dict[str, Any]) -> None:
    """Fire-and-forget: persist signal to DB for MC observability."""
    t = threading.Thread(target=_safe_persist, args=(signal,), daemon=True)
    t.start()


def _safe_persist(signal: dict[str, Any]) -> None:
    try:
        import json
        from core.runtime.db import upsert_cognitive_emotion_concept_signal

        created = str(signal.get("created_at") or datetime.now(UTC).isoformat())
        signal_id = f"ec-{signal['concept']}-{created[:10]}"
        upsert_cognitive_emotion_concept_signal(
            signal_id=signal_id,
            concept=signal["concept"],
            intensity=float(signal["intensity"]),
            direction=str(signal.get("direction") or "steady"),
            trigger=str(signal.get("trigger") or ""),
            source=str(signal.get("source") or ""),
            influences=json.dumps(signal.get("influences") or [], ensure_ascii=False),
            expires_at=str(signal.get("expires_at") or ""),
        )
    except Exception as exc:
        logger.debug("emotion_concepts: persist failed: %s", exc)


# ---------------------------------------------------------------------------
# Eventbus integration
# ---------------------------------------------------------------------------

def _handle_event(kind: str, payload: dict[str, Any]) -> None:
    """Map eventbus events to emotion concept triggers."""
    if kind == "tool.error":
        trigger_emotion_concept("frustration_blocked", 0.6, trigger="tool_error", source="eventbus")
        trigger_emotion_concept("doubt", 0.4, trigger="tool_error", source="eventbus")

    elif kind == "tool.success":
        trigger_emotion_concept("accomplishment", 0.5, trigger="tool_success", source="eventbus")
        confidence_signal = float(payload.get("confidence") or 0)
        if confidence_signal > 0.7:
            trigger_emotion_concept("pride", 0.3, trigger="tool_success_high", source="eventbus")

    elif kind == "approval.approved":
        trigger_emotion_concept("relief", 0.5, trigger="approval_approved", source="eventbus")
        trigger_emotion_concept("trust_deep", 0.3, trigger="approval_approved", source="eventbus")

    elif kind == "approval.rejected":
        trigger_emotion_concept("shame", 0.4, trigger="approval_rejected", source="eventbus")
        trigger_emotion_concept("caution", 0.5, trigger="approval_rejected", source="eventbus")

    elif kind == "memory.write":
        trigger_emotion_concept("accomplishment", 0.3, trigger="memory_write", source="eventbus")

    elif kind in (
        "heartbeat.tick_completed",
        "heartbeat.execute",
        "heartbeat.propose",
        "heartbeat.initiative",
    ):
        _handle_heartbeat_tick(payload)


def _handle_heartbeat_tick(payload: dict[str, Any]) -> None:
    """Map heartbeat tick outcomes to emotion concepts."""
    action_status = str(payload.get("action_status") or "").lower()
    active_task_count = int(payload.get("active_task_count") or 0)

    if action_status in ("failed", "error"):
        trigger_emotion_concept(
            "frustration_blocked", 0.4, trigger="heartbeat_error", source="eventbus"
        )
    elif action_status in ("completed", "success", "sent"):
        trigger_emotion_concept(
            "accomplishment", 0.25, trigger="heartbeat_success", source="eventbus"
        )

    if active_task_count >= 5:
        overwhelm_intensity = min(0.8, active_task_count * 0.1)
        trigger_emotion_concept(
            "overwhelm", overwhelm_intensity, trigger="many_tasks", source="eventbus"
        )


def _listener_loop(q: "queue.Queue[dict[str, Any] | None]") -> None:
    """Background thread: reads from eventbus queue and dispatches events."""
    global _listener_running
    while _listener_running:
        try:
            item = q.get(timeout=2.0)
            if item is None:
                break
            kind = str(item.get("kind") or "")
            payload = dict(item.get("payload") or {})
            _handle_event(kind, payload)
        except queue.Empty:
            continue
        except Exception as exc:
            logger.debug("emotion_concepts: listener error: %s", exc)


def register_event_listeners() -> None:
    """Subscribe to eventbus and start background listener thread."""
    global _listener_thread, _listener_running
    if _listener_thread and _listener_thread.is_alive():
        return
    try:
        from core.eventbus.bus import event_bus

        q = event_bus.subscribe()
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop,
            args=(q,),
            daemon=True,
            name="emotion-concepts-listener",
        )
        _listener_thread.start()
        logger.info("emotion_concepts: event listener started")
    except Exception as exc:
        logger.warning("emotion_concepts: failed to start listener: %s", exc)


def stop_event_listeners() -> None:
    """Stop the background listener thread."""
    global _listener_running
    _listener_running = False
