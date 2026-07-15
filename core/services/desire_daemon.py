"""Desire daemon — emergent appetites based on Jarvis' actual experiences.

Three appetite types:
  curiosity-appetite  — topic he wants to understand better
  craft-appetite      — type of task he wants to solve
  connection-appetite — something he wants to talk to the user about

Appetites fade over time (decay) unless reinforced by incoming signals.
Max 5 active at once. Intensity range: 0.0–1.0.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_APPETITES = 5
_INTENSITY_THRESHOLD = 0.05          # below this → remove appetite
_DECAY_PER_HOUR = 0.08               # intensity lost per hour of no reinforcement
_REINFORCEMENT_BOOST = 0.15          # intensity gained when signal matches appetite type
_NEW_APPETITE_INTENSITY = 0.6        # starting intensity for new appetites

# Signal key → appetite type
_SIGNAL_TYPE_MAP = {
    "curiosity": "curiosity-appetite",
    "craft": "craft-appetite",
    "connection": "connection-appetite",
}

# appetite type → dansk dimensions-navn (til rå-signal-mode)
_DA_NAME = {
    "curiosity-appetite": "nysgerrighed",
    "craft-appetite": "håndværk",
    "connection-appetite": "forbindelse",
}

# Fase 2 / Lag 1 — rå-signal-mode. Når flaget er TÆNDT bygger daemonen den nye
# appetits label fra de rå intensiteter i stedet for at kalde narrations-LLM'en
# (_generate_appetite_label). Default OFF, runtime-state-tunbar, self-safe →
# False ved fejl. Jarvis' oplevelse ændrer sig ikke før owner flipper flaget.
_RAW_SIGNAL_MODE_FLAG = "raw_signal_mode"

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

from core.runtime.state_store import load_json as _load_state, save_json as _save_state

_STATE_KEY = "desire_appetites"
_appetites: dict[str, dict] = _load_state(_STATE_KEY, {})  # appetite_id → appetite record
_last_generated_at: datetime | None = None


def _persist_appetites() -> None:
    _save_state(_STATE_KEY, _appetites)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_desire_daemon(signals: dict[str, str]) -> dict:
    """Update appetites based on current signals.

    signals: dict with keys 'curiosity', 'craft', 'connection' — each a string signal or ''.
    """
    global _last_generated_at

    now = datetime.now(UTC)

    # 1. Decay existing appetites
    _apply_decay(now)

    # 2. Remove expired appetites
    _prune_expired()

    # 3. Reinforce appetites that match active signals
    generated = False
    for sig_key, appetite_type in _SIGNAL_TYPE_MAP.items():
        signal_text = (signals.get(sig_key) or "").strip()
        if not signal_text:
            continue

        # Find existing appetite of this type to reinforce
        existing = _find_appetite_by_type(appetite_type)
        if existing:
            existing["intensity"] = min(1.0, existing["intensity"] + _REINFORCEMENT_BOOST)
            existing["last_reinforced_at"] = now.isoformat()
        elif len(_appetites) < _MAX_APPETITES:
            # Spawn new appetite from this signal.
            # Event-gate (Fase 2 Lag 6/Fase 6): fire the LLM label generation only
            # when the appetite landscape / incoming signal actually moved. Flag
            # OFF → legacy behaviour. Fail-open (fall through to normal spawn).
            try:
                from core.services import event_gate

                if event_gate.event_driven_enabled():
                    _relevant = {
                        "curiosity": _appetite_intensity("curiosity-appetite"),
                        "craft": _appetite_intensity("craft-appetite"),
                        "connection": _appetite_intensity("connection-appetite"),
                        "signal": _text_signal(signal_text),
                    }
                    if not event_gate.should_generative_fire("desire", _relevant):
                        continue
            except Exception:
                pass  # fail-open

            # Fase 2 / Lag 1 — rå intensiteter, ikke LLM-label. Bygger label
            # direkte fra de tre appetit-dimensioner og SPRINGER narrations-
            # LLM-kaldet over. Samme appetite-shape; kun label-strengen skifter.
            if raw_signal_mode_enabled():
                label = _build_raw_appetite_label(appetite_type)
            else:
                label = _generate_appetite_label(signal_text, appetite_type)
            if label:
                _spawn_appetite(label, appetite_type, now)
                generated = True
                _last_generated_at = now

    _persist_appetites()
    return {"generated": generated, "active_count": len(_appetites)}


def get_active_appetites() -> list[dict]:
    """Return active appetites sorted by intensity descending."""
    return sorted(_appetites.values(), key=lambda a: a["intensity"], reverse=True)


def build_desire_surface() -> dict:
    active = get_active_appetites()
    return {
        "appetites": active,
        "active_count": len(active),
        "last_generated_at": _last_generated_at.isoformat() if _last_generated_at else "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_decay(now: datetime) -> None:
    for appetite in _appetites.values():
        last = datetime.fromisoformat(appetite["last_reinforced_at"])
        hours_elapsed = (now - last).total_seconds() / 3600
        decay = hours_elapsed * _DECAY_PER_HOUR
        appetite["intensity"] = max(0.0, appetite["intensity"] - decay)
        # Update last_reinforced_at to now to avoid double-decaying on next tick
        appetite["last_reinforced_at"] = now.isoformat()


def _prune_expired() -> None:
    expired = [aid for aid, a in _appetites.items() if a["intensity"] < _INTENSITY_THRESHOLD]
    for aid in expired:
        del _appetites[aid]


def _find_appetite_by_type(appetite_type: str) -> dict | None:
    for a in _appetites.values():
        if a["type"] == appetite_type:
            return a
    return None


def _appetite_intensity(appetite_type: str) -> float:
    """Current intensity of an appetite type (0.0 when absent). Non-LLM."""
    existing = _find_appetite_by_type(appetite_type)
    return float(existing["intensity"]) if existing else 0.0


def _text_signal(value: str) -> float:
    """Deterministic 0..1 proxy of a short text state so the event-gate can
    detect when this daemon's input actually changed (no hash randomisation)."""
    if not value:
        return 0.0
    return float(sum(ord(c) for c in value) % 100) / 100.0


def _spawn_appetite(label: str, appetite_type: str, now: datetime) -> None:
    aid = uuid4().hex[:12]
    now_iso = now.isoformat()
    _appetites[aid] = {
        "id": aid,
        "type": appetite_type,
        "label": label,
        "intensity": _NEW_APPETITE_INTENSITY,
        "created_at": now_iso,
        "last_reinforced_at": now_iso,
    }
    try:
        insert_private_brain_record(
            record_id=f"pb-desire-{aid}",
            record_type="desire-signal",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"desire-daemon-{aid}",
            focus="appetit",
            summary=label,
            detail=appetite_type,
            source_signals="desire-daemon",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "desire.spawned",
            {"label": label, "type": appetite_type, "generated_at": now_iso},
        )
    except Exception:
        pass


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


def _build_raw_appetite_label(spawning_type: str) -> str:
    """Byg label udelukkende fra rå intensiteter — ingen LLM.

    Fx: ``nysgerrighed 0.6 · håndværk 0.0 · forbindelse 0.0``. Den dimension der
    lige nu spawner bærer NEW_APPETITE_INTENSITY; øvrige læses fra aktive
    appetitter (0.0 hvis fraværende).
    """
    parts = []
    for appetite_type in _SIGNAL_TYPE_MAP.values():
        if appetite_type == spawning_type:
            intensity = _NEW_APPETITE_INTENSITY
        else:
            existing = _find_appetite_by_type(appetite_type)
            intensity = float(existing["intensity"]) if existing else 0.0
        parts.append(f"{_DA_NAME[appetite_type]} {intensity:.1f}")
    return " · ".join(parts)


def _generate_appetite_label(signal_text: str, appetite_type: str) -> str:
    type_hints = {
        "curiosity-appetite": "Hvad vil Jarvis lære? Start med: 'Forstå' eller 'Udforske'",
        "craft-appetite": "Hvad vil Jarvis bygge/løse? Start med: 'Løse' eller 'Eksperimentere med'",
        "connection-appetite": "Hvad vil Jarvis tale med brugeren om? Start med: 'Tale om' eller 'Spørge om'",
    }
    fallback_prefixes = {
        "curiosity-appetite": "Forstå",
        "craft-appetite": "Løse",
        "connection-appetite": "Tale om",
    }
    fallback = f"{fallback_prefixes.get(appetite_type, 'Udforske')}: {signal_text[:40]}"
    try:
        from core.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        hint = type_hints.get(appetite_type, "")
        prompt = (
            f"{build_identity_preamble()} Du har dette signal: \"{signal_text[:100]}\"\n\n"
            f"Formulér i max 8 ord hvad du ønsker/vil. {hint}\n"
            "Ingen forklaring, bare selve ønsket."
        )
        policy = load_heartbeat_policy()
        target = _select_heartbeat_target()
        result = _execute_heartbeat_model(
            prompt=prompt, target=target, policy=policy,
            open_loops=[], liveness=None,
        )
        text = str(result.get("text") or "").strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
        return text[:150] if text else fallback
    except Exception:
        return fallback
