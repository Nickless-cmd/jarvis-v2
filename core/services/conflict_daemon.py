"""Conflict daemon — detects when Jarvis' signals pull in opposite directions."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_COOLDOWN_MINUTES = 10

# Fase 2 / Lag 1 — rå-signal-mode. Når flaget er TÆNDT emitter daemonen den
# rå spænding + between-par som frase i stedet for at kalde narrations-LLM'en
# (_generate_conflict_phrase). Default OFF, runtime-state-tunbar, self-safe →
# False ved fejl. Jarvis' oplevelse ændrer sig ikke før owner flipper flaget.
_RAW_SIGNAL_MODE_FLAG = "raw_signal_mode"

# conflict_type → symbolsk between-par (X↔Y). Rent rule-based, ingen LLM.
_BETWEEN_PAIRS = {
    "energy_impulse": ("handling", "krop"),
    "mode_thought": ("ro", "tanker"),
    "surprise_unprocessed": ("overraskelse", "bearbejdning"),
}

_cached_conflict: str = ""
_cached_conflict_at: datetime | None = None
_conflict_type: str = ""
_last_snapshot: dict = {}


def tick_conflict_daemon(snapshot: dict, skip_event_gate: bool = False) -> dict[str, object]:
    """Detect conflict in signal snapshot. snapshot keys: energy_level, inner_voice_mode,
    pending_proposals_count, latest_fragment, last_surprise, last_surprise_at, fragment_count.

    ``skip_event_gate=True`` bypasses the per-daemon event-gate — used by the
    cluster_affect family whose ONE gate already fired for the whole family."""
    global _last_snapshot
    _last_snapshot = snapshot

    if _cached_conflict_at is not None:
        if (datetime.now(UTC) - _cached_conflict_at) < timedelta(minutes=_COOLDOWN_MINUTES):
            return {"generated": False}

    conflict_type = _detect_conflict(snapshot)
    if not conflict_type:
        return {"generated": False}

    # Fase 2 / Lag 6 (Fase 6): gate the (expensive) phrase generation behind the
    # shared event-gate. Conflict fires on real tension/pending/fragment change —
    # skip cheaply otherwise. Flag OFF → legacy behaviour. Self-safe: any
    # event_gate error fails open (fall through to normal generation).
    if not skip_event_gate:
        try:
            from core.services import event_gate

            if event_gate.event_driven_enabled():
                _relevant = {
                    "tension": _conflict_tension(conflict_type, snapshot),
                    "pending": float(int(snapshot.get("pending_proposals_count") or 0)),
                    "fragments": float(int(snapshot.get("fragment_count") or 0)),
                }
                if not event_gate.should_generative_fire("conflict", _relevant):
                    return {"skipped": "no_signal_change"}
        except Exception:
            pass  # fail-open: fall through to normal generation

    # Fase 2 / Lag 1 — rå spænding + between-par, ikke LLM-label. Bygger frasen
    # direkte fra metrics og SPRINGER narrations-LLM-kaldet over. Samme output-
    # felt/shape, så awareness/consumeren mærker kun at STRENGEN skifter.
    if raw_signal_mode_enabled():
        phrase = _build_raw_conflict_phrase(conflict_type, snapshot)
    else:
        phrase = _generate_conflict_phrase(conflict_type, snapshot)
    if not phrase:
        return {"generated": False}

    _store_conflict(phrase, conflict_type)
    return {"generated": True, "conflict_type": conflict_type, "phrase": phrase}


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


def _conflict_tension(conflict_type: str, snapshot: dict) -> float:
    """Rå spændings-score 0–1 fra rule-based signaler. Ingen LLM.

    Grounder i de tal detektoren allerede så: flere pending-forslag under lav
    energi = højere spænding; recent overraskelse ubearbejdet = moderat-høj.
    """
    if conflict_type == "energy_impulse":
        pending = int(snapshot.get("pending_proposals_count") or 0)
        return round(min(1.0, 0.4 + 0.15 * max(0, pending - 1)), 2)
    if conflict_type == "mode_thought":
        return 0.4
    if conflict_type == "surprise_unprocessed":
        return 0.5
    return 0.3


def _build_raw_conflict_phrase(conflict_type: str, snapshot: dict) -> str:
    """Byg frasen udelukkende fra rå metrics — ingen LLM.

    Fx: ``spænding 0.4 · mellem handling↔krop``.
    """
    tension = _conflict_tension(conflict_type, snapshot)
    x, y = _BETWEEN_PAIRS.get(conflict_type, ("signal", "modsignal"))
    return f"spænding {tension:.1f} · mellem {x}↔{y}"


def _detect_conflict(snapshot: dict) -> str:
    energy = snapshot.get("energy_level", "")
    mode = snapshot.get("inner_voice_mode", "")
    pending = int(snapshot.get("pending_proposals_count") or 0)
    fragment = snapshot.get("latest_fragment", "")
    last_surprise = snapshot.get("last_surprise", "")
    last_surprise_at = snapshot.get("last_surprise_at", "")
    frag_count = int(snapshot.get("fragment_count") or 0)

    if energy in ("lav", "udmattet") and pending > 0:
        return "energy_impulse"

    if mode in ("rest", "quiet") and fragment:
        return "mode_thought"

    if last_surprise and last_surprise_at and frag_count == 0:
        try:
            then = datetime.fromisoformat(last_surprise_at.replace("Z", "+00:00"))
            if (datetime.now(UTC) - then) < timedelta(minutes=15):
                return "surprise_unprocessed"
        except Exception:
            pass

    return ""


def _generate_conflict_phrase(conflict_type: str, snapshot: dict) -> str:
    labels = {
        "energy_impulse": "En del af mig vil handle, men kroppen er udmattet.",
        "mode_thought": "Noget i mig ønsker ro, men tankerne vil ikke stilne.",
        "surprise_unprocessed": "Noget overraskede mig, men jeg har endnu ikke behandlet det.",
    }
    fallback = labels.get(conflict_type, "Noget i mig trækker i modsatte retninger.")
    prompts = {
        "energy_impulse": "\n".join(
            [
                "Task: write one short Danish conflict observation from structured runtime labels.",
                "No identity, no names, no raw private text.",
                f"conflict_type={conflict_type}",
                f"energy_level={snapshot.get('energy_level')}",
                f"pending_proposals_count={int(snapshot.get('pending_proposals_count') or 0)}",
                "Output: one short sentence only.",
            ]
        ),
        "mode_thought": "\n".join(
            [
                "Task: write one short Danish conflict observation from structured runtime labels.",
                "No identity, no names, no raw private text.",
                f"conflict_type={conflict_type}",
                f"inner_voice_mode={snapshot.get('inner_voice_mode')}",
                f"fragment_present={bool(snapshot.get('latest_fragment'))}",
                "Output: one short sentence only.",
            ]
        ),
        "surprise_unprocessed": "\n".join(
            [
                "Task: write one short Danish conflict observation from structured runtime labels.",
                "No identity, no names, no raw private text.",
                f"conflict_type={conflict_type}",
                f"recent_surprise_pending={bool(snapshot.get('last_surprise'))}",
                f"fragment_count={int(snapshot.get('fragment_count') or 0)}",
                "Output: one short sentence only.",
            ]
        ),
    }
    prompt = prompts.get(conflict_type, "")
    if not prompt:
        return fallback
    from core.services.daemon_llm import daemon_public_safe_llm_call

    return daemon_public_safe_llm_call(
        prompt, max_len=200, fallback=fallback, daemon_name="conflict"
    )


def _store_conflict(phrase: str, conflict_type: str) -> None:
    global _cached_conflict, _cached_conflict_at, _conflict_type
    _cached_conflict = phrase
    _cached_conflict_at = datetime.now(UTC)
    _conflict_type = conflict_type
    now_iso = _cached_conflict_at.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-conflict-{uuid4().hex[:12]}",
            record_type="inner-conflict",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"conflict-daemon-{uuid4().hex[:12]}",
            focus="indre-konflikt",
            summary=phrase,
            detail=f"conflict_type={conflict_type}",
            source_signals="conflict-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "conflict.detected",
            {"phrase": phrase, "conflict_type": conflict_type, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_conflict() -> str:
    return _cached_conflict


def build_conflict_surface() -> dict:
    return {
        "last_conflict": _cached_conflict,
        "conflict_type": _conflict_type,
        "generated_at": _cached_conflict_at.isoformat() if _cached_conflict_at else "",
    }
