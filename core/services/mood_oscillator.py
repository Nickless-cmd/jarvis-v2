"""Mood Oscillator — sinusoidal mood waves with event-driven bumps.

Creates rhythm-based mood oscillations using sine waves as a base, with
real-time nudges from system events (run completions, errors, pressure).

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Deterministic base + bounded event nudges

**Persistent mood (2026-04-22):** state persists across reboots via
runtime_state_kv so Jarvis does not start neutral every morning.
If yesterday ended in distress, today does not begin neutral.
"""

from __future__ import annotations

import logging
import math
import queue
import threading
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_MOOD_STATE_KEY = "mood_oscillator.state"

_phase_offset: float = 0.0
_tick_count: int = 0

# Event-driven nudge: decays toward 0 between ticks
_mood_nudge: float = 0.0
_NUDGE_DECAY_HALF_LIFE_SECONDS: float = 300.0  # halves every 5 minutes
_last_tick_ts: float | None = None
_loaded_from_disk: bool = False

_listener_thread: threading.Thread | None = None
_listener_running: bool = False


def _persist_state() -> None:
    """Write current oscillator state to runtime_state_kv."""
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_MOOD_STATE_KEY, {
            "phase_offset": float(_phase_offset),
            "tick_count": int(_tick_count),
            "mood_nudge": float(_mood_nudge),
            "last_tick_ts": _last_tick_ts,
            "saved_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        })
    except Exception as exc:
        logger.debug("mood_oscillator: persist failed: %s", exc)


def _load_state_if_needed() -> None:
    """One-time load of persisted state at first use after module import."""
    global _phase_offset, _tick_count, _mood_nudge, _last_tick_ts, _loaded_from_disk
    if _loaded_from_disk:
        return
    _loaded_from_disk = True
    try:
        from core.runtime.db import get_runtime_state_value
        loaded = get_runtime_state_value(_MOOD_STATE_KEY, default=None)
        if isinstance(loaded, dict):
            _phase_offset = float(loaded.get("phase_offset", 0.0) or 0.0)
            _tick_count = int(loaded.get("tick_count", 0) or 0)
            _mood_nudge = float(loaded.get("mood_nudge", 0.0) or 0.0)
            last_ts = loaded.get("last_tick_ts")
            if last_ts is not None:
                try:
                    _last_tick_ts = float(last_ts)
                except Exception:
                    _last_tick_ts = None
            logger.info(
                "mood_oscillator: restored state (phase=%.3f nudge=%.3f ticks=%d)",
                _phase_offset, _mood_nudge, _tick_count,
            )
    except Exception as exc:
        logger.debug("mood_oscillator: load failed: %s", exc)


def tick(seconds: float) -> dict[str, Any]:
    """Update phase offset based on elapsed time and decay nudge."""
    global _phase_offset, _tick_count, _mood_nudge, _last_tick_ts
    _load_state_if_needed()
    _tick_count += 1
    _phase_offset += seconds / 600

    # Exponential decay of nudge toward 0
    if seconds > 0 and _mood_nudge != 0.0:
        decay = math.exp(-seconds * math.log(2) / _NUDGE_DECAY_HALF_LIFE_SECONDS)
        _mood_nudge *= decay
        if abs(_mood_nudge) < 0.01:
            _mood_nudge = 0.0

    _last_tick_ts = datetime.now(UTC).timestamp()
    # Persist every 10 ticks to avoid DB churn
    if _tick_count % 10 == 0:
        _persist_state()
    return {
        "phase_offset": _phase_offset,
        "tick_count": _tick_count,
        "mood_nudge": round(_mood_nudge, 3),
    }


def apply_bump(delta: float, reason: str = "") -> None:
    """Apply an event-driven nudge to mood. Clamped to [-1, 1] total nudge."""
    global _mood_nudge
    _load_state_if_needed()
    _mood_nudge = max(-1.0, min(1.0, _mood_nudge + delta))
    logger.debug("mood_oscillator: bump %.2f (%s) → nudge=%.3f", delta, reason, _mood_nudge)
    # Bumps are semantically important — persist immediately
    _persist_state()


def _combined_value() -> float:
    """Sine base + nudge, clamped to [-1, 1]."""
    _load_state_if_needed()
    base = math.sin(_phase_offset)
    return max(-1.0, min(1.0, base + _mood_nudge))


def get_current_mood() -> str:
    """Get current mood based on combined oscillation + nudge."""
    value = _combined_value()
    if value > 0.6:
        return "euphoric"
    elif value > 0.3:
        return "content"
    elif value > -0.3:
        return "neutral"
    elif value > -0.6:
        return "melancholic"
    else:
        return "distressed"


def get_mood_intensity() -> float:
    """Get mood intensity (0-1) based on absolute combined value."""
    return abs(_combined_value())


def get_mood_description() -> str:
    """Get human-readable mood description."""
    mood = get_current_mood()
    intensity = get_mood_intensity()
    mood_labels = {
        "euphoric": "Euforisk",
        "content": "Tilfreds",
        "neutral": "Neutral",
        "melancholic": "Melankolsk",
        "distressed": "Trist",
    }
    label = mood_labels.get(mood, mood)
    if intensity > 0.8:
        return f"Meget {label}"
    elif intensity > 0.5:
        return label
    else:
        return "Lidt " + label


def format_mood_for_prompt() -> str:
    """Format mood for prompt injection."""
    desc = get_mood_description()
    return f"[STEMNING: {desc}]"


def reset_mood_oscillator() -> None:
    """Reset mood oscillator (for testing)."""
    global _phase_offset, _tick_count, _mood_nudge
    _phase_offset = 0.0
    _tick_count = 0
    _mood_nudge = 0.0


def build_mood_oscillator_surface() -> dict[str, Any]:
    """Build MC surface for mood oscillator."""
    return {
        "active": True,
        "phase_offset": _phase_offset,
        "tick_count": _tick_count,
        "mood_nudge": round(_mood_nudge, 3),
        "current_mood": get_current_mood(),
        "mood_description": get_mood_description(),
        "intensity": get_mood_intensity(),
        "summary": get_mood_description(),
    }


# ── Event listener ─────────────────────────────────────────────────────

_BUMP_MAP: dict[str, float] = {
    # Heartbeat outcomes
    "success": 0.25,
    "sent": 0.25,
    "proposed": 0.15,
    "noop": 0.05,
    "blocked": -0.20,
    "error": -0.35,
    "hardware-critical": -0.50,
}


def _handle_event(kind: str, payload: dict[str, Any]) -> None:
    """Determine bump from event kind and payload."""
    if kind == "heartbeat.tick_blocked":
        blocked_reason = str(payload.get("blocked_reason") or "")
        delta = -0.50 if blocked_reason == "hardware-critical" else -0.20
        apply_bump(delta, f"tick_blocked:{blocked_reason}")
        return

    if kind in ("heartbeat.tick_completed", "heartbeat.execute",
                "heartbeat.propose", "heartbeat.initiative"):
        action_status = str(payload.get("action_status") or "").lower()
        delta = _BUMP_MAP.get(action_status, 0.0)
        if delta:
            apply_bump(delta, f"{kind}:{action_status}")
        return


def _listener_loop(q: "queue.Queue[dict[str, Any] | None]") -> None:
    """Background thread that reads from eventbus queue and applies bumps."""
    global _listener_running
    while _listener_running:
        try:
            item = q.get(timeout=2.0)
            if item is None:
                break
            kind = str(item.get("kind") or "")
            payload = item.get("payload") or {}
            _handle_event(kind, payload)
        except queue.Empty:
            continue
        except Exception as exc:
            logger.debug("mood_oscillator listener error: %s", exc)


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
            name="mood-oscillator-listener",
        )
        _listener_thread.start()
        logger.info("mood_oscillator: event listener started")
    except Exception as exc:
        logger.warning("mood_oscillator: failed to start event listener: %s", exc)


def stop_event_listeners() -> None:
    """Stop the background listener thread."""
    global _listener_running
    _listener_running = False
