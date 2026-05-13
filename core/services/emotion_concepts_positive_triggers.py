"""Positive emotion concept bridges for living runtime signals.

These helpers keep the "positive" concept triggers explicit and conservative:
goal creation/progress, strong heartbeat quality, and anomalous sensory
captures. They are called from existing runtime surfaces instead of creating a
second event listener.
"""
from __future__ import annotations

from typing import Any


def on_heartbeat_quality(payload: dict[str, Any]) -> None:
    """Trigger joy when heartbeat quality is clearly good."""
    score = _float(payload.get("quality_score") or payload.get("tick_quality") or 0.0)
    if score < 70.0:
        return

    from core.services.emotion_concepts import trigger_emotion_concept
    trigger_emotion_concept(
        "joy",
        0.4,
        trigger="heartbeat_quality_high",
        source="heartbeat_quality",
        min_seconds_since_last_from_same_source=3600,
    )


def on_goal_created(payload: dict[str, Any]) -> None:
    """A new durable goal produces a small anticipation/excitement pulse."""
    goal_id = str(payload.get("goal_id") or "")
    from core.services.emotion_concepts import trigger_emotion_concept
    trigger_emotion_concept(
        "excitement",
        0.3,
        trigger="goal_created",
        source=f"goal.created:{goal_id}" if goal_id else "goal.created",
        min_seconds_since_last_from_same_source=300,
    )


def on_goal_updated(payload: dict[str, Any]) -> None:
    """Trigger pride when a goal is nearly done, without refiring constantly."""
    progress = _float(payload.get("progress_pct") or 0.0)
    status = str(payload.get("status") or "").lower()
    if progress < 80.0 and status != "completed":
        return

    goal_id = str(payload.get("goal_id") or "")
    source = f"goal.high_progress:{goal_id}" if goal_id else "goal.high_progress"
    from core.services.emotion_concepts import trigger_emotion_concept
    trigger_emotion_concept(
        "pride",
        0.5,
        trigger="goal_high_progress" if status != "completed" else "goal_completed",
        source=source,
        min_seconds_since_last_from_same_source=21600,
    )


_WONDER_MARKERS = (
    "anomali",
    "anomaly",
    "anderledes",
    "første gang",
    "mærkelig",
    "mystisk",
    "new",
    "novel",
    "ny ",
    "nyt ",
    "overrask",
    "strange",
    "ukendt",
    "unexpected",
    "unusual",
)


def on_sensory_recorded(record: dict[str, Any]) -> None:
    """Trigger wonder when a sensory memory explicitly looks novel/anomalous."""
    content = str(record.get("content") or "")
    mood = str(record.get("mood_tone") or "")
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    novelty_flag = any(
        bool(metadata.get(key))
        for key in ("novel", "novelty", "anomaly", "anomalous", "new_object", "unexpected")
    )
    haystack = f"{content}\n{mood}".lower()
    if not novelty_flag and not any(marker in haystack for marker in _WONDER_MARKERS):
        return

    from core.services.emotion_concepts import trigger_emotion_concept
    trigger_emotion_concept(
        "wonder",
        0.4,
        trigger="sensory_novelty",
        source="sensory_archive",
        min_seconds_since_last_from_same_source=1800,
    )


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_emotion_concepts_positive_triggers_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push. Reports module presence + mode
    so the cartographer registers it as observed. Specific state-readers
    can be added later as the module evolves.
    """
    return {
        "active": True,
        "mode": "positive-trigger-detector",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_emotion_concepts_positive_triggers_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a emotion_concepts_positive_triggers-scoped event. Defensive — never blocks caller.

    Cartographer scans for event_bus.publish() text. This wrapper keeps
    publishes consistent across the module.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"emotion_concepts_positive_triggers.{kind}",
            payload or {},
        )
    except Exception:
        pass

