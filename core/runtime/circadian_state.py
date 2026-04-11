"""Circadian state — energy level from clock + activity density."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.eventbus.bus import event_bus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STATE_PATH = Path.home() / ".jarvis-v2" / "state" / "circadian.json"
_DRAIN_THRESHOLD_HIGH = 20    # events/hour threshold for high drain
_RESTORE_QUIET_MINUTES = 30   # silence required before one restore step
_ENERGY_ORDER = ["høj", "medium", "lav", "udmattet"]

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_activity_log: list[datetime] = []
_last_restore_check: datetime | None = None
_current_energy: str = ""
_last_energy_written: str = ""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_activity_event() -> None:
    """Call on each heartbeat run or visible turn to track activity density."""
    global _activity_log
    now = datetime.now(UTC)
    _activity_log.append(now)
    cutoff = now - timedelta(hours=1)
    _activity_log = [t for t in _activity_log if t > cutoff]


def get_circadian_context() -> dict[str, object]:
    """Compute and return current energy context. Fast — no LLM, no DB."""
    global _current_energy, _last_energy_written, _last_restore_check
    now = datetime.now(UTC)

    baseline = _clock_baseline(now.hour)
    drain_score = _drain_score()
    drain_label = _drain_label(drain_score)

    energy = baseline
    if drain_score >= 0.6:
        energy = _lower_energy(energy)

    quiet_minutes = _quiet_minutes_since_last_activity(now)
    if quiet_minutes >= _RESTORE_QUIET_MINUTES:
        should_restore = (
            _last_restore_check is None
            or (now - _last_restore_check) >= timedelta(minutes=_RESTORE_QUIET_MINUTES)
        )
        if should_restore:
            energy = _raise_energy(energy)
            _last_restore_check = now

    clock_phase = _clock_phase_label(now.hour)
    _current_energy = energy

    if energy != _last_energy_written:
        _persist_state(energy)
        _last_energy_written = energy
        event_bus.publish(
            "circadian.energy_changed",
            {
                "energy_level": energy,
                "clock_phase": clock_phase,
                "drain_score": round(drain_score, 2),
            },
        )

    return {
        "energy_level": energy,
        "clock_phase": clock_phase,
        "drain_score": round(drain_score, 2),
        "drain_label": drain_label,
        "description": f"{clock_phase} med {drain_label} aktivitetsdrain",
    }


def load_persisted_state() -> str | None:
    """Load previously persisted energy level. Call once on startup."""
    global _current_energy, _last_energy_written
    try:
        data = json.loads(_STATE_PATH.read_text())
        energy = str(data.get("energy_level") or "")
        if energy in _ENERGY_ORDER:
            _current_energy = energy
            _last_energy_written = energy
            return energy
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clock_baseline(hour: int) -> str:
    if 6 <= hour < 10:
        return "høj"
    if 10 <= hour < 14:
        return "medium"
    if 14 <= hour < 16:
        return "lav"
    if 16 <= hour < 20:
        return "medium"
    if 20 <= hour < 23:
        return "lav"
    return "udmattet"


def _clock_phase_label(hour: int) -> str:
    if 6 <= hour < 10:
        return "tidlig morgen"
    if 10 <= hour < 12:
        return "formiddag"
    if 12 <= hour < 14:
        return "middag"
    if 14 <= hour < 16:
        return "eftermiddag"
    if 16 <= hour < 20:
        return "sen eftermiddag"
    if 20 <= hour < 23:
        return "aften"
    return "nat"


def _drain_score() -> float:
    return min(len(_activity_log) / _DRAIN_THRESHOLD_HIGH, 1.0)


def _drain_label(score: float) -> str:
    if score >= 0.6:
        return "høj"
    if score >= 0.3:
        return "medium"
    return "lav"


def _quiet_minutes_since_last_activity(now: datetime) -> float:
    if not _activity_log:
        return 9999.0
    last = max(_activity_log)
    return (now - last).total_seconds() / 60.0


def _lower_energy(level: str) -> str:
    idx = _ENERGY_ORDER.index(level) if level in _ENERGY_ORDER else 0
    return _ENERGY_ORDER[min(idx + 1, len(_ENERGY_ORDER) - 1)]


def _raise_energy(level: str) -> str:
    idx = _ENERGY_ORDER.index(level) if level in _ENERGY_ORDER else len(_ENERGY_ORDER) - 1
    return _ENERGY_ORDER[max(idx - 1, 0)]


def _persist_state(energy: str) -> None:
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATE_PATH.write_text(json.dumps({
            "energy_level": energy,
            "updated_at": datetime.now(UTC).isoformat(),
        }))
    except Exception:
        pass
