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
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble

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

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_appetites: dict[str, dict] = {}     # appetite_id → appetite record
_last_generated_at: datetime | None = None

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
            # Spawn new appetite from this signal
            label = _generate_appetite_label(signal_text, appetite_type)
            if label:
                _spawn_appetite(label, appetite_type, now)
                generated = True
                _last_generated_at = now

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
            session_id="",
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
        from apps.api.jarvis_api.services.heartbeat_runtime import (
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
