"""Pressure Threshold Gate — konverterer presning til impuls.

Når en presningsvektor krydser en tærskel, bliver den til en IMPULS —
en eksplicit "nu vil jeg det her". Dette er det kritiske spring fra
passiv observation til aktiv vilje.

Tærskler er ikke faste — de tilpasser sig:
- Ny direction/topic starter med høj tærskel (skal bygge op)
- Gentagen presning sænker tærsklen (vanedannelse)
- Krydsninger markerer pressure_vector som crossed_threshold=True
- Hver impuls har en "strength" baseret på hvor meget tærsklen blev overskredet

Impulser sendes videre til impulse_executor som konverterer dem til
konkrete handlinger.
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

# Default thresholds per direction
_DIRECTION_THRESHOLDS: dict[str, float] = {
    "explore":     0.45,   # curiosity needs moderate build-up
    "fix":         0.35,   # frustration → action at lower threshold (urgent)
    "create":      0.50,   # desire needs to build before acting
    "retreat":     0.55,   # withdrawal should be deliberate
    "engage":      0.40,   # positive engagement is natural
    "caution":     0.30,   # memory-based caution should trigger relatively easily
    "follow":      0.40,   # dream-following needs moderate conviction
    "orient":      0.45,   # gut orientation
    "act":         0.35,   # initiative should be accessible
    "investigate": 0.40,   # emergent investigation
    "respond":     0.30,   # warnings should trigger fast
    # Spor-1 (2026-04-29): reach_out is real, requires real pressure.
    # 0.55 is high — Bjorn would need to be away ~5+ hours before this
    # crosses, given longing-build-curve (start=2h, max=12h, decay 0.88/tick).
    "reach_out":   0.55,
}

_DEFAULT_THRESHOLD = 0.45
_THRESHOLD_ADAPTATION_RATE = 0.05   # how much threshold drops per reinforcement
_THRESHOLD_FLOOR = 0.20             # minimum threshold
_THRESHOLD_CEILING = 0.70           # maximum threshold
_COOLDOWN_MINUTES = 15              # minimum time between same-direction impulses
_MAX_PENDING_IMPULSES = 5


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Impulse:
    """En impuls — en presning der har krydset tærsklen og bliver til vilje."""
    id: str
    direction: str          # same as pressure vector direction
    topic: str              # what the impulse is about
    strength: float         # how far above threshold (accumulated - threshold)
    source_pressure_id: str  # the pressure vector that birthed this impulse
    created_at: str
    status: str             # "pending", "executing", "completed", "failed"
    action_taken: str = ""  # what was done about this impulse
    cooldown_until: str = ""


# ---------------------------------------------------------------------------
# Gate state
# ---------------------------------------------------------------------------

_thresholds: dict[str, float] = {}     # direction → current threshold
_pending_impulses: list[Impulse] = []
_last_impulse_at: dict[str, str] = {}  # direction → ISO timestamp
_gate_enabled: bool = True


def _get_threshold(direction: str) -> float:
    """Get the current threshold for a direction, creating default if needed."""
    if direction not in _thresholds:
        _thresholds[direction] = _DIRECTION_THRESHOLDS.get(direction, _DEFAULT_THRESHOLD)
    return _thresholds[direction]


def _adapt_threshold(direction: str, crossed: bool) -> None:
    """Adapt threshold based on whether it was crossed.

    If crossed repeatedly, threshold lowers (easier to cross next time).
    This models habituation — the more a direction fires, the easier it fires again.
    """
    current = _get_threshold(direction)
    if crossed:
        new_threshold = max(current - _THRESHOLD_ADAPTATION_RATE, _THRESHOLD_FLOOR)
    else:
        new_threshold = min(current + (_THRESHOLD_ADAPTATION_RATE * 0.3), _THRESHOLD_CEILING)
    _thresholds[direction] = new_threshold


def _is_on_cooldown(direction: str) -> bool:
    """Check if a direction is still in cooldown from a recent impulse."""
    if direction not in _last_impulse_at:
        return False
    last = datetime.fromisoformat(_last_impulse_at[direction])
    cooldown_end = last + __import__("datetime").timedelta(minutes=_COOLDOWN_MINUTES)
    return datetime.now(UTC) < cooldown_end


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def evaluate_pressures(pressures: list) -> list[Impulse]:
    """Evaluate all pressure vectors and generate impulses for those that cross thresholds.

    This is the main entry point — called each tick after pressure accumulation.
    """
    if not _gate_enabled:
        return []

    new_impulses: list[Impulse] = []
    now = datetime.now(UTC).isoformat()

    for pv in pressures:
        # Skip if on cooldown
        if _is_on_cooldown(pv.direction):
            logger.debug(f"Impulse direction '{pv.direction}' on cooldown, skipping")
            continue

        threshold = _get_threshold(pv.direction)
        if pv.accumulated >= threshold:
            # Threshold crossed! Generate impulse
            strength = pv.accumulated - threshold
            impulse_id = f"impulse-{pv.direction}-{now[:16]}"

            impulse = Impulse(
                id=impulse_id,
                direction=pv.direction,
                topic=pv.topic,
                strength=round(strength, 3),
                source_pressure_id=pv.id,
                created_at=now,
                status="pending",
            )

            new_impulses.append(impulse)
            _pending_impulses.append(impulse)
            _last_impulse_at[pv.direction] = now
            pv.crossed_threshold = True

            # Adapt threshold (lower it — this direction is now more accessible)
            _adapt_threshold(pv.direction, crossed=True)

            logger.info(
                f"⚡ IMPULSE: {pv.direction} → '{pv.topic}' "
                f"(strength={strength:.3f}, pressure={pv.accumulated:.3f}, threshold={threshold:.3f})"
            )

            # Emit event
            event_bus.publish("impulse.generated", {
                "impulse_id": impulse.id,
                "direction": pv.direction,
                "topic": pv.topic,
                "strength": round(strength, 3),
                "pressure_accumulated": round(pv.accumulated, 3),
                "threshold": round(threshold, 3),
            })
        else:
            # Did not cross — adapt threshold slightly upward (harder next time)
            _adapt_threshold(pv.direction, crossed=False)

    # Cap pending impulses
    while len(_pending_impulses) > _MAX_PENDING_IMPULSES:
        _pending_impulses.pop(0)

    return new_impulses


def get_pending_impulses() -> list[Impulse]:
    """Return all pending impulses that haven't been executed yet."""
    return [i for i in _pending_impulses if i.status == "pending"]


def mark_impulse_executing(impulse_id: str, action: str = "") -> None:
    """Mark an impulse as currently being executed."""
    for imp in _pending_impulses:
        if imp.id == impulse_id:
            imp.status = "executing"
            imp.action_taken = action
            break


def mark_impulse_completed(impulse_id: str, action: str = "") -> None:
    """Mark an impulse as completed."""
    for imp in _pending_impulses:
        if imp.id == impulse_id:
            imp.status = "completed"
            if action:
                imp.action_taken = action
            break


def mark_impulse_failed(impulse_id: str, reason: str = "") -> None:
    """Mark an impulse as failed."""
    for imp in _pending_impulses:
        if imp.id == impulse_id:
            imp.status = "failed"
            imp.action_taken = reason or "failed"
            break


def snapshot() -> dict[str, Any]:
    """Return serializable snapshot of gate state."""
    return {
        "thresholds": dict(_thresholds),
        "pending_impulses": [asdict(i) for i in _pending_impulses],
        "last_impulse_at": dict(_last_impulse_at),
        "total_impulses_generated": len(_pending_impulses),
    }


# ---------------------------------------------------------------------------
# Daemon runner
# ---------------------------------------------------------------------------

def run_threshold_gate_tick() -> dict[str, Any]:
    """Run one tick of the threshold gate.

    1. Pull dominant pressures from accumulator.
    2. Evaluate each against threshold.
    3. Generate impulses for those that cross.
    4. Persist state.
    """
    from core.services.signal_pressure_accumulator import get_dominant_pressures

    # 1. Get dominant pressures
    pressures = get_dominant_pressures(min_accumulated=0.15)

    # 2. Evaluate
    new_impulses = evaluate_pressures(pressures)

    # 3. Persist
    snap = snapshot()
    try:
        import json as _json
        import secrets as _secrets
        from datetime import datetime as _dt, timezone as _tz
        _focus = (
            f"{len(new_impulses)}_new_impulses"
            if new_impulses
            else "no_new_impulses"
        )
        _summary = (
            f"{len(pressures)} pressures evaluated, "
            f"{len(new_impulses)} new impulses fired"
        )
        insert_private_brain_record(
            record_id=f"thresh_{_secrets.token_hex(8)}",
            record_type="threshold_gate_snapshot",
            layer="inner",
            session_id="",
            run_id="",
            focus=_focus,
            summary=_summary,
            detail=_json.dumps(snap, default=str),
            source_signals="pressure_threshold_gate.tick",
            confidence="1.0",
            created_at=_dt.now(_tz.utc).isoformat(),
            domain="self",
        )
    except Exception as e:
        logger.warning(f"Failed to persist threshold gate snapshot: {e}")

    # 4. Return
    return {
        "pressures_evaluated": len(pressures),
        "new_impulses": len(new_impulses),
        "pending_impulses": len(get_pending_impulses()),
        "impulses": [
            {"direction": i.direction, "topic": i.topic, "strength": i.strength}
            for i in new_impulses
        ],
    }