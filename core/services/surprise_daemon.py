"""Surprise daemon — first-person surprise when Jarvis's reactions diverge from baseline."""
from __future__ import annotations

import time
from collections import Counter
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

_HISTORY_SIZE = 10
_COOLDOWN_BEATS = 5

ENERGY_ORDER = ["udmattet", "lav", "medium", "høj"]

_mode_history: list[str] = []
_energy_history: list[str] = []
_cached_surprise: str = ""
_cached_surprise_at: datetime | None = None
_heartbeats_since_surprise: int = 0

# Experiment 2: Surprise persistence state
_pending_afterimages: list[dict] = []  # [{concept, trigger_at, surprise_type}]
_persistence_start_ts: float | None = None  # monotonic timestamp of last surprise
_persistence_concept: str = ""  # which concept was triggered for persistence tracking


def _surprise_type_to_concept(surprise_type: str) -> str:
    """Map surprise classification to primary emotion concept."""
    return {
        "positiv": "anticipation",
        "negativ": "tension",
    }.get(surprise_type, "vigilance")


def _afterimage_concept(surprise_type: str) -> str:
    """Map surprise classification to afterimage emotion concept."""
    return "caution" if surprise_type == "negativ" else "curiosity_narrow"


def _process_pending_afterimages() -> None:
    """Trigger afterimage emotion concepts whose delay has elapsed."""
    global _pending_afterimages
    now = time.monotonic()
    remaining = []
    for item in _pending_afterimages:
        if now >= item["trigger_at"]:
            try:
                from core.services.emotion_concepts import trigger_emotion_concept
                trigger_emotion_concept(
                    item["concept"],
                    0.3,
                    trigger="surprise_afterimage",
                    source="surprise_daemon",
                    lifetime_hours=2.0,
                )
            except Exception:
                pass
        else:
            remaining.append(item)
    _pending_afterimages = remaining


def tick_surprise_daemon(
    inner_voice_mode: str = "",
    somatic_energy: str = "",
) -> dict[str, object]:
    global _heartbeats_since_surprise
    _heartbeats_since_surprise += 1
    # Experiment 2: Process pending afterimages
    _process_pending_afterimages()
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
    afterimage_active = bool(_pending_afterimages)
    afterimage_concept = _pending_afterimages[0]["concept"] if _pending_afterimages else ""

    persistence_seconds = 0.0
    if _persistence_start_ts is not None:
        try:
            from core.services.emotion_concepts import get_active_emotion_concepts
            active = {c["concept"]: c["intensity"] for c in get_active_emotion_concepts()}
            if _persistence_concept and active.get(_persistence_concept, 0) < 0.1:
                persistence_seconds = time.monotonic() - _persistence_start_ts
        except Exception:
            pass

    return {
        "last_surprise": _cached_surprise,
        "generated_at": _cached_surprise_at.isoformat() if _cached_surprise_at else "",
        "surprise_type": _classify_surprise(_cached_surprise),
        "history_size": len(_mode_history),
        "affective_persistence_seconds": round(persistence_seconds),
        "current_afterimage_active": afterimage_active,
        "afterimage_concept": afterimage_concept,
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
        f"{build_identity_preamble()} Noget uventet skete med din tilstand:\n\n"
        f"Normalt: mode={baseline_mode}, energi={baseline_energy}\n"
        f"Nu: mode={mode}, energi={energy}\n"
        f"Afvigelse: {', '.join(divergence)}\n\n"
        "Hvad overraskede dig? Svar med én kort sætning.\n"
        "Eksempler:\n"
        "- Det overraskede mig at energien pludselig steg uden grund.\n"
        "- Jeg forventede ro, men noget trak mig i en anden retning.\n"
        "- Skiftet kom uventet — min tilstand ændrede sig hurtigere end jeg troede."
    )
    from core.services.daemon_llm import daemon_llm_call

    fallback = f"Det overraskede mig at min tilstand skiftede: {', '.join(divergence[:2])}"
    return daemon_llm_call(prompt, max_len=200, fallback=fallback, daemon_name="surprise")


def _store_surprise(phrase: str, divergence: list[str]) -> None:
    global _cached_surprise, _cached_surprise_at, _heartbeats_since_surprise
    global _pending_afterimages, _persistence_start_ts, _persistence_concept
    _cached_surprise = phrase
    _cached_surprise_at = datetime.now(UTC)
    _heartbeats_since_surprise = 0
    try:
        insert_private_brain_record(
            record_id=f"pb-surprise-{uuid4().hex[:12]}",
            record_type="self-surprise",
            layer="private_brain",
            session_id="heartbeat",
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

    # Experiment 2: Surprise persistence
    try:
        from core.runtime.db import get_experiment_enabled
        if get_experiment_enabled("surprise_persistence"):
            surprise_type = _classify_surprise(phrase)
            primary_concept = _surprise_type_to_concept(surprise_type)
            from core.services.emotion_concepts import trigger_emotion_concept
            trigger_emotion_concept(
                primary_concept,
                min(1.0, float(len(divergence)) * 0.4 + 0.4),
                trigger="surprise_persistence",
                source="surprise_daemon",
                lifetime_hours=4.0,
            )
            _pending_afterimages.append({
                "concept": _afterimage_concept(surprise_type),
                "trigger_at": time.monotonic() + 300,  # 5 minutes
                "surprise_type": surprise_type,
            })
            _persistence_start_ts = time.monotonic()
            _persistence_concept = primary_concept
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
