"""Surprise daemon — first-person surprise when Jarvis's reactions diverge from baseline."""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble

_HISTORY_SIZE = 10
_COOLDOWN_BEATS = 5

ENERGY_ORDER = ["udmattet", "lav", "medium", "høj"]

_mode_history: list[str] = []
_energy_history: list[str] = []
_cached_surprise: str = ""
_cached_surprise_at: datetime | None = None
_heartbeats_since_surprise: int = 0


def tick_surprise_daemon(
    inner_voice_mode: str = "",
    somatic_energy: str = "",
) -> dict[str, object]:
    global _heartbeats_since_surprise
    _heartbeats_since_surprise += 1
    _record_snapshot(inner_voice_mode, somatic_energy)
    if len(_mode_history) < 3:
        return {"generated": False, "surprise": _cached_surprise}
    if _heartbeats_since_surprise <= _COOLDOWN_BEATS:
        return {"generated": False, "surprise": _cached_surprise}
    divergence = _compute_divergence(inner_voice_mode, somatic_energy)
    if not divergence:
        return {"generated": False, "surprise": _cached_surprise}
    phrase = _generate_surprise(inner_voice_mode, somatic_energy, divergence)
    if not phrase:
        return {"generated": False, "surprise": _cached_surprise}
    _store_surprise(phrase, divergence)
    return {"generated": True, "surprise": phrase, "divergence": divergence}


def get_latest_surprise() -> str:
    return _cached_surprise


def build_surprise_surface() -> dict[str, object]:
    return {
        "last_surprise": _cached_surprise,
        "generated_at": _cached_surprise_at.isoformat() if _cached_surprise_at else "",
        "surprise_type": _classify_surprise(_cached_surprise),
        "history_size": len(_mode_history),
    }


def _record_snapshot(mode: str, energy: str) -> None:
    global _mode_history, _energy_history
    if mode:
        _mode_history.append(mode)
        if len(_mode_history) > _HISTORY_SIZE:
            _mode_history = _mode_history[-_HISTORY_SIZE:]
    if energy:
        _energy_history.append(energy)
        if len(_energy_history) > _HISTORY_SIZE:
            _energy_history = _energy_history[-_HISTORY_SIZE:]


def _compute_divergence(current_mode: str, current_energy: str) -> list[str]:
    divergences: list[str] = []
    if len(_mode_history) >= 3 and current_mode:
        baseline_modes = _mode_history[:-1]
        majority = Counter(baseline_modes).most_common(1)[0][0]
        if current_mode != majority:
            divergences.append(f"mode:{majority}→{current_mode}")
    if len(_energy_history) >= 3 and current_energy:
        baseline_energy = _energy_history[-2] if len(_energy_history) >= 2 else ""
        if (
            baseline_energy
            and baseline_energy in ENERGY_ORDER
            and current_energy in ENERGY_ORDER
        ):
            delta = abs(
                ENERGY_ORDER.index(current_energy) - ENERGY_ORDER.index(baseline_energy)
            )
            if delta >= 2:
                divergences.append(f"energy:{baseline_energy}→{current_energy}")
    return divergences


def _generate_surprise(
    mode: str, energy: str, divergence: list[str]
) -> str:
    baseline_mode = (
        Counter(_mode_history[:-1]).most_common(1)[0][0]
        if len(_mode_history) > 1
        else "?"
    )
    baseline_energy = _energy_history[-2] if len(_energy_history) >= 2 else "?"
    prompt = (
        f"{build_identity_preamble()} Her er hvad der normalt sker for dig vs. hvad der skete nu:\n\n"
        f"Baseline mode: {baseline_mode}\n"
        f"Nuværende mode: {mode}\n"
        f"Baseline energi: {baseline_energy}\n"
        f"Nuværende energi: {energy}\n"
        f"Afvigelse: {', '.join(divergence)}\n\n"
        "Formulér i én sætning (max 20 ord), i første person, hvad der overraskede dig "
        "ved din egen reaktion.\n"
        "Vær konkret. Start med 'Jeg' eller 'Det overraskede mig'."
    )
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        policy = load_heartbeat_policy()
        target = _select_heartbeat_target()
        result = _execute_heartbeat_model(
            prompt=prompt, target=target, policy=policy,
            open_loops=[], liveness=None,
        )
        phrase = str(result.get("text") or "").strip()
        if phrase.startswith('"') and phrase.endswith('"'):
            phrase = phrase[1:-1].strip()
        return phrase[:200]
    except Exception:
        return ""


def _store_surprise(phrase: str, divergence: list[str]) -> None:
    global _cached_surprise, _cached_surprise_at, _heartbeats_since_surprise
    _cached_surprise = phrase
    _cached_surprise_at = datetime.now(UTC)
    _heartbeats_since_surprise = 0
    try:
        insert_private_brain_record(
            record_id=f"pb-surprise-{uuid4().hex[:12]}",
            record_type="self-surprise",
            layer="private_brain",
            session_id="",
            run_id=f"surprise-daemon-{uuid4().hex[:12]}",
            focus="reaktionsafvigelse",
            summary=phrase,
            detail=f"divergence={','.join(divergence)}",
            source_signals="surprise-daemon:heartbeat",
            confidence="medium",
            created_at=_cached_surprise_at.isoformat(),
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "cognitive_surprise.noted",
            {"phrase": phrase, "divergence": divergence},
        )
    except Exception:
        pass


def _classify_surprise(phrase: str) -> str:
    if not phrase:
        return "ingen"
    lower = phrase.lower()
    if any(w in lower for w in ["positiv", "godt", "bedre", "stærkere"]):
        return "positiv"
    if any(w in lower for w in ["tung", "svær", "fejl", "ikke klarede"]):
        return "negativ"
    return "neutral"
