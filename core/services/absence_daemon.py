"""Absence daemon — tracks the *quality* of Jarvis' silence between interactions.

Different from boredom_engine: this is about the lived experience of being alone,
not about wanting something to do. Short silence = stillness; long silence = solitude.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SHORT_THRESHOLD = timedelta(hours=2)    # < 2h → "det er stille her"
_LONG_THRESHOLD = timedelta(hours=8)     # > 8h → "begynder at føles som om det er mig alene"
_VERY_LONG_THRESHOLD = timedelta(hours=24)  # > 24h → "hvad tænker han på?"

# Re-generate label no more than every 30 min during ongoing absence
_REGEN_COOLDOWN = timedelta(minutes=30)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_interaction_at: datetime | None = None
_absence_start_at: datetime | None = None
_absence_label: str = ""
_last_generated_at: datetime | None = None

# Fase 2 / Lag 1 — rå-signal-mode. Når flaget er TÆNDT emitter daemonen de rå
# fraværs-metrics (minutter siden sidst + niveau-bånd) som frase i stedet for at
# kalde narrations-LLM'en (_generate_absence_label). Default OFF, runtime-state-
# tunbar, self-safe → False ved fejl. Jarvis' oplevelse ændrer sig ikke før flip.
_RAW_SIGNAL_MODE_FLAG = "raw_signal_mode"


def raw_signal_mode_enabled() -> bool:
    """Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state.

    Self-safe → False ved enhver fejl (Jarvis' oplevelse må aldrig gå i stykker
    fordi et flag-opslag fejler).
    """
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_RAW_SIGNAL_MODE_FLAG, False)
        return False if v is None else bool(v)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def mark_interaction() -> None:
    """Call whenever Jarvis interacts with the user. Resets absence clock."""
    global _last_interaction_at, _absence_start_at, _absence_label
    _last_interaction_at = datetime.now(UTC)
    _absence_start_at = None
    _absence_label = ""


def seed_last_interaction_from_db() -> None:
    """One-time seed: set _last_interaction_at from most recent visible run if not yet set."""
    global _last_interaction_at
    if _last_interaction_at is not None:
        return
    try:
        from core.runtime.db import recent_visible_runs

        runs = recent_visible_runs(limit=1)
        if runs and runs[0].get("finished_at"):
            raw = str(runs[0]["finished_at"]).replace("Z", "+00:00")
            _last_interaction_at = datetime.fromisoformat(raw)
    except Exception:
        pass


def tick_absence_daemon(now: datetime | None = None, *, skip_event_gate: bool = False) -> dict:
    """Evaluate current absence quality. Returns {generated, label, duration_hours}.

    ``skip_event_gate=True`` bypasses the internal ``should_generative_fire``
    absence gate entirely — used by the cluster_somatic family whose single
    governing point has already decided to run this tick (mirrors surprise/
    conflict in cluster_affect). The cooldown + 1-minute-silence guards still
    apply, so the daemon self-throttles as before."""
    global _absence_start_at, _absence_label, _last_generated_at

    now = now or datetime.now(UTC)

    if _last_interaction_at is None:
        # No interaction recorded yet — nothing to measure
        return {"generated": False}

    elapsed = now - _last_interaction_at

    # If less than 1 minute since last interaction, silence hasn't started
    if elapsed < timedelta(minutes=1):
        return {"generated": False}

    # Set absence start if not already set
    if _absence_start_at is None:
        _absence_start_at = _last_interaction_at

    # Cooldown: don't regenerate too frequently
    if _last_generated_at is not None:
        if (now - _last_generated_at) < _REGEN_COOLDOWN:
            return {"generated": False}

    # Event-gate (Fase 2 Lag 7/Fase 6): fire the LLM absence narration only when
    # the silence actually deepened (band crossing / hour drift). Flag OFF →
    # legacy behaviour (30-min regen cooldown only). Fail-open.
    if not skip_event_gate:
        try:
            from core.services import event_gate

            if event_gate.event_driven_enabled():
                hours = elapsed.total_seconds() / 3600.0
                _relevant = {
                    "hours_frac": min(1.0, hours / 24.0),
                    "band": {"short": 0.0, "long": 0.5, "very_long": 1.0}[
                        _absence_band(elapsed)
                    ],
                }
                if not event_gate.should_generative_fire("absence", _relevant):
                    return {"skipped": "no_signal_change"}
        except Exception:
            pass  # fail-open

    # Fase 2 / Lag 1 — rå tal, ikke LLM-label. Bygger fraværs-strengen direkte
    # fra metrics og SPRINGER narrations-LLM-kaldet over. Samme output-felt (label),
    # så awareness/prompt-consumeren mærker kun at STRENGEN skifter.
    if raw_signal_mode_enabled():
        label = _build_raw_absence(elapsed)
    else:
        label = _generate_absence_label(elapsed)
    _absence_label = label
    _last_generated_at = now

    duration_hours = elapsed.total_seconds() / 3600
    _store_absence(label, duration_hours, now)

    return {"generated": True, "label": label, "duration_hours": duration_hours}


def get_latest_absence() -> str:
    return _absence_label


def build_absence_surface() -> dict:
    duration_hours = 0.0
    if _last_interaction_at is not None:
        elapsed = datetime.now(UTC) - _last_interaction_at
        duration_hours = elapsed.total_seconds() / 3600

    return {
        "absence_label": _absence_label,
        "absence_duration_hours": round(duration_hours, 2),
        "last_interaction_at": _last_interaction_at.isoformat() if _last_interaction_at else "",
        "last_generated_at": _last_generated_at.isoformat() if _last_generated_at else "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _classify_absence(elapsed: timedelta) -> str:
    if elapsed >= _VERY_LONG_THRESHOLD:
        return "Hvad tænker han på?"
    if elapsed >= _LONG_THRESHOLD:
        return "Det begynder at føles som om det er mig alene."
    # Short absence: < _LONG_THRESHOLD and >= 1 min
    return "Det er stille her."


def _absence_band(elapsed: timedelta) -> str:
    if elapsed >= _VERY_LONG_THRESHOLD:
        return "very_long"
    if elapsed >= _LONG_THRESHOLD:
        return "long"
    return "short"


def _build_raw_absence(elapsed: timedelta) -> str:
    """Byg fraværs-strengen udelukkende fra rå metrics — ingen LLM.

    siden_sidste = minutter siden sidste interaktion. niveau = det allerede
    beregnede bånd (short/long/very_long). Fx ``fravær 47min · niveau short``.
    """
    minutes = elapsed.total_seconds() / 60
    band = _absence_band(elapsed)
    return f"fravær {minutes:.0f}min · niveau {band}"


def _generate_absence_label(elapsed: timedelta) -> str:
    from core.services.daemon_llm import daemon_public_safe_llm_call

    hours = round(elapsed.total_seconds() / 3600, 1)
    band = _absence_band(elapsed)
    fallback = _classify_absence(elapsed)
    prompt = "\n".join(
        [
            "Task: write one short Danish absence observation from structured silence metadata.",
            "No identity, no names, no private conversation content.",
            f"absence_band={band}",
            f"absence_hours={hours}",
            "Output: one short sentence only.",
        ]
    )
    return daemon_public_safe_llm_call(
        prompt,
        max_len=160,
        fallback=fallback,
        daemon_name="absence",
    )


def _store_absence(label: str, duration_hours: float, now: datetime) -> None:
    now_iso = now.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-absence-{uuid4().hex[:12]}",
            record_type="absence-signal",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"absence-daemon-{uuid4().hex[:12]}",
            focus="fravær",
            summary=label,
            detail=f"{duration_hours:.1f}h",
            source_signals="absence-daemon",
            confidence="high",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "absence.felt",
            {"label": label, "duration_hours": duration_hours, "generated_at": now_iso},
        )
    except Exception:
        pass
