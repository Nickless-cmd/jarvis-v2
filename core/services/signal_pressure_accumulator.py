"""Signal Pressure Accumulator — generativ autonomi: fra signal til presning.

Jarvis' indre signaler producerer observationer, men driver intet. Denne
module samler de indre signaler og akkumulerer PRESNING over tid — en
intern kraft der vokser når signaler gentager eller forstærker hinanden,
og forfalder langsomt hvis ikke næret.

Presning er ikke en beslutning. Det er en TENDENS — en indre retning
der siger "noget vil ud". Når presning krydser en tærskel, bliver den
til en impuls (håndteret af pressure_threshold_gate).

Designprincipper:
- Hvert signal bidrager med en pressure_vector (retning + styrke)
- Presning akkumuleres per "vectorspace" (curiosity, frustration, desire, etc.)
- Presning forfalder per tick (decay_factor ~0.92)
- Presning vokser når signaler gentager eller forstærker
- Ingen presning → ingen impuls → ingen handling. Alt kommer indefra.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_PRESSURES = 12
_DECAY_PER_TICK = 0.88          # presning forfalder med 12% per tick
_MIN_PRESSURE = 0.02            # under dette → fjern pressure vector
_MAX_PRESSURE = 1.0             # cap
_PRESSURE_CONTRIBUTION_SCALE = {
    # signal_family → (direction, weight)
    "curiosity":      ("explore",     0.35),
    "frustration":    ("fix",         0.40),
    "desire":         ("create",      0.30),
    "boredom":        ("explore",     0.20),
    "mood_negative":  ("retreat",     0.25),
    "mood_positive":  ("engage",      0.15),
    "memory_signal":  ("caution",     0.20),
    "dream_signal":   ("follow",      0.25),
    "gut_signal":     ("orient",      0.20),
    "initiative":     ("act",         0.30),
    "emergent":       ("investigate", 0.35),
    "warning":        ("respond",     0.45),
}

# Topic-key mapping: certain signals carry a topic that groups pressure
_TOPIC_SIGNALS = {"curiosity", "desire", "frustration", "emergent"}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PressureVector:
    """En akkumuleret presningsvektor — retning + styrke over tid."""
    id: str
    direction: str              # explore, fix, create, retreat, engage, caution, follow, orient, act, investigate, respond
    topic: str                  # what the pressure is about (e.g. "database errors", "personality drift")
    accumulated: float          # current pressure level (0.0–1.0)
    tick_count: int             # how many ticks this pressure has been alive
    source_signals: list[str]   # signal IDs that contributed
    last_reinforced_at: str     # ISO timestamp
    created_at: str             # ISO timestamp
    peak: float                 # highest this pressure has been
    crossed_threshold: bool     # has this ever crossed the threshold?


# ---------------------------------------------------------------------------
# Accumulator state
# ---------------------------------------------------------------------------

_pressures: dict[str, PressureVector] = {}
_last_tick_at: str = ""
_daemon_enabled: bool = True


def _make_id(direction: str, topic: str) -> str:
    """Stable key for a pressure vector based on direction+topic."""
    return f"{direction}::{topic}"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def ingest_signal(signal_family: str, signal_data: dict[str, Any]) -> None:
    """Ingest a single signal into the pressure accumulator.

    This is the main entry point. Each tick, all active signals are fed here.
    The signal contributes its pressure to the matching vector.
    """
    if not _daemon_enabled:
        return

    mapping = _PRESSURE_CONTRIBUTION_SCALE.get(signal_family)
    if not mapping:
        return  # unknown signal family, ignore

    direction, weight = mapping

    # Determine topic
    topic = signal_data.get("canonical_key") or signal_data.get("topic") or "general"
    if signal_family in _TOPIC_SIGNALS:
        topic = signal_data.get("short_summary", topic)[:60]

    # Determine intensity
    intensity = float(signal_data.get("salience", 0.5))
    if signal_data.get("intensity") in ("high", "emerging", "strong"):
        intensity = max(intensity, 0.7)
    elif signal_data.get("intensity") in ("low", "fading"):
        intensity = min(intensity, 0.3)

    contribution = weight * intensity

    vid = _make_id(direction, topic)
    now = datetime.now(UTC).isoformat()

    if vid in _pressures:
        # Reinforce existing pressure
        pv = _pressures[vid]
        pv.accumulated = min(pv.accumulated + contribution, _MAX_PRESSURE)
        pv.tick_count += 1
        pv.last_reinforced_at = now
        pv.peak = max(pv.peak, pv.accumulated)
        pv.source_signals.append(signal_data.get("id", "unknown"))
        if len(pv.source_signals) > 20:
            pv.source_signals = pv.source_signals[-20:]
    else:
        # New pressure vector
        pv = PressureVector(
            id=vid,
            direction=direction,
            topic=topic,
            accumulated=contribution,
            tick_count=1,
            source_signals=[signal_data.get("id", "unknown")],
            last_reinforced_at=now,
            created_at=now,
            peak=contribution,
            crossed_threshold=False,
        )
        _pressures[vid] = pv

    logger.debug(f"Pressure {_pressures[vid].accumulated:.3f} → {direction}:{topic}")


def decay_all() -> None:
    """Apply decay to all pressure vectors. Called once per tick."""
    now = datetime.now(UTC).isoformat()
    to_remove = []

    for vid, pv in _pressures.items():
        pv.accumulated *= _DECAY_PER_TICK
        pv.tick_count += 1

        if pv.accumulated < _MIN_PRESSURE:
            to_remove.append(vid)

    for vid in to_remove:
        logger.debug(f"Pressure faded: {_pressures[vid].direction}:{_pressures[vid].topic}")
        del _pressures[vid]

    # Cap total active pressures
    while len(_pressures) > _MAX_PRESSURES:
        # Remove the weakest
        weakest = min(_pressures.values(), key=lambda p: p.accumulated)
        del _pressures[weakest.id]

    global _last_tick_at
    _last_tick_at = now


def get_all_pressures() -> list[PressureVector]:
    """Return all active pressure vectors, sorted by accumulated (strongest first)."""
    return sorted(_pressures.values(), key=lambda p: p.accumulated, reverse=True)


def get_pressure(direction: str, topic: str) -> PressureVector | None:
    """Get a specific pressure vector."""
    return _pressures.get(_make_id(direction, topic))


def get_dominant_pressures(min_accumulated: float = 0.15) -> list[PressureVector]:
    """Return pressures above a minimum threshold — these are the ones that matter."""
    return [pv for pv in _pressures.values() if pv.accumulated >= min_accumulated]


def snapshot() -> dict[str, Any]:
    """Return a serializable snapshot of current pressure state."""
    return {
        "pressures": {vid: asdict(pv) for vid, pv in _pressures.items()},
        "total_vectors": len(_pressures),
        "dominant": [
            {"direction": pv.direction, "topic": pv.topic, "accumulated": round(pv.accumulated, 3)}
            for pv in get_dominant_pressures()
        ],
        "last_tick_at": _last_tick_at,
    }


# ---------------------------------------------------------------------------
# Daemon runner (called by heartbeat tick)
# ---------------------------------------------------------------------------

def run_pressure_accumulator_tick() -> dict[str, Any]:
    """Run one tick of the pressure accumulator.

    1. Collect active signals from emergent_signal_tracking, desire_daemon,
       initiative_accumulator, etc.
    2. Ingest each signal.
    3. Decay all pressures.
    4. Persist snapshot to private brain.
    5. Emit event with dominant pressures.
    """
    from core.services.emergent_signal_tracking import get_active_signals
    from core.services.desire_daemon import get_appetites
    from core.services.initiative_accumulator import get_wants

    # 1. Ingest emergent signals
    try:
        for sig in get_active_signals():
            ingest_signal("emergent", asdict(sig) if hasattr(sig, "__dataclass_fields__") else sig)
    except Exception:
        logger.debug("No emergent signals available")

    # 2. Ingest desires/appetites
    try:
        for appetite in get_appetites():
            ingest_signal("desire", {
                "id": appetite.get("id", "?"),
                "canonical_key": appetite.get("appetite_type", "unknown"),
                "topic": appetite.get("focus", "general"),
                "short_summary": appetite.get("focus", "general"),
                "salience": appetite.get("intensity", 0.5),
                "intensity": "high" if appetite.get("intensity", 0) > 0.6 else "low",
            })
    except Exception:
        logger.debug("No appetites available")

    # 3. Ingest initiative/wants
    try:
        for want in get_wants():
            ingest_signal("initiative", {
                "id": want.get("id", "?"),
                "canonical_key": want.get("category", "unknown"),
                "topic": want.get("focus", "general"),
                "short_summary": want.get("focus", "general"),
                "salience": want.get("intensity", 0.5),
                "intensity": "medium",
            })
    except Exception:
        logger.debug("No wants available")

    # 4. Ingest mood/affect signals
    try:
        from core.services.mood_oscillator import get_mood_snapshot
        mood = get_mood_snapshot()
        if mood:
            valence = mood.get("valence", 0.5)
            if valence < 0.3:
                ingest_signal("mood_negative", {
                    "id": "mood",
                    "salience": 1.0 - valence,
                    "canonical_key": "mood_negative",
                    "topic": "mood",
                })
            elif valence > 0.7:
                ingest_signal("mood_positive", {
                    "id": "mood",
                    "salience": valence,
                    "canonical_key": "mood_positive",
                    "topic": "mood",
                })
    except Exception:
        logger.debug("No mood data available")

    # 5. Decay
    decay_all()

    # 6. Persist snapshot
    snap = snapshot()
    try:
        insert_private_brain_record(
            record_type="pressure_snapshot",
            content=snap,
            modality="inner",
            metadata={"source": "signal_pressure_accumulator", "tick": True},
        )
    except Exception as e:
        logger.warning(f"Failed to persist pressure snapshot: {e}")

    # 7. Emit event for downstream consumers (threshold gate, action router)
    dominant = get_dominant_pressures()
    if dominant:
        event_bus.emit("pressure.accumulated", {
            "dominant_count": len(dominant),
            "top_direction": dominant[0].direction,
            "top_topic": dominant[0].topic,
            "top_accumulated": round(dominant[0].accumulated, 3),
            "vectors": [
                {"direction": pv.direction, "topic": pv.topic, "accumulated": round(pv.accumulated, 3)}
                for pv in dominant[:5]
            ],
        })

    return snap