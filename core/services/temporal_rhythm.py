"""Temporal Rhythm — felt time, not computed time.

Jarvis' PLAN_WILD_IDEAS #7 (2026-04-20): fast pulse under pressure, slow
breath in stillness. Not just elapsed seconds — subjective tempo.

Inputs per tick:
- eventbus queue depth (proxy via recent event count if available)
- pending initiatives count
- recent tool calls/min
- chat activity (recent visible_runs)

Outputs:
- pulse_rate in [0.1, 2.0] — 1.0 is normal, <0.5 is resting, >1.3 is pressed
- subjective_time_pressure ("breathing" | "steady" | "pulsing" | "racing")
- perceived_elapsed — rough inflation factor applied to clock time when
  reasoning about "how long ago"
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime import state_store

logger = logging.getLogger(__name__)

_FIL = "temporal_rhythm"

#: Maalt 25/9-2026: daemon-blokken tikker ~hvert 9. minut, ikke hvert 30.
#: sekund. 30 proever er altsaa ~4,5 time, ikke et kvarter. Kommentaren sagde
#: «~15 min at 30s ticks» — tallet var rigtigt, antagelsen under det var ikke.
_HISTORY_MAX = 30
_BASELINE_MAX = 100

# Tilstanden laa i en `deque` og en liste i modulet. `jarvis-api` og
# `jarvis-runtime` koerer samme kode i hver sin proces, men kun runtime
# tikker — api'ens kopi var derfor tom, og fladen sagde «Endnu ingen
# tempo-sampling» uanset hvor laenge han havde levet. Genstart slettede
# desuden baade historik og baseline.
_tick_history: list[dict[str, Any]] = []
_baseline_samples: list[float] = []
_sidst_laest_ns: int = -1


def _synk() -> None:
    """Hent fra disk hvis filen er aendret siden sidste laesning."""
    global _tick_history, _baseline_samples, _sidst_laest_ns
    ns = state_store.aendret_ns(_FIL)
    if ns == _sidst_laest_ns:
        return
    raa = state_store.load_json(_FIL, None)
    if isinstance(raa, dict):
        h = raa.get("history")
        b = raa.get("baseline")
        _tick_history = [x for x in h if isinstance(x, dict)] if isinstance(h, list) else []
        _baseline_samples = [float(x) for x in b
                             if isinstance(x, (int, float))] if isinstance(b, list) else []
    else:
        _tick_history = []
        _baseline_samples = []
    _sidst_laest_ns = ns


def _gem() -> None:
    global _sidst_laest_ns
    state_store.save_json(_FIL, {
        "history": _tick_history[:_HISTORY_MAX],
        "baseline": _baseline_samples[-_BASELINE_MAX:],
    })
    _sidst_laest_ns = state_store.aendret_ns(_FIL)


def _pending_initiatives_count() -> int:
    try:
        from core.services.initiative_queue import get_pending_initiatives
        return len(get_pending_initiatives() or [])
    except Exception:
        return 0


def _recent_tool_calls_per_min() -> float:
    try:
        from core.runtime.db import recent_heartbeat_outcome_counts  # type: ignore
        counts = recent_heartbeat_outcome_counts(minutes=5) or {}
        total = sum(int(v) for v in counts.values())
        return round(total / 5.0, 2)
    except Exception:
        return 0.0


def _recent_chat_activity_per_min() -> float:
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=30) or []
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=5)
        count = 0
        for r in runs:
            ts = str(r.get("started_at") or "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if dt >= cutoff:
                    count += 1
            except Exception:
                continue
        return round(count / 5.0, 2)
    except Exception:
        return 0.0


def _eventbus_queue_depth() -> int:
    try:
        from core.eventbus.bus import event_bus
        # Not all implementations expose a .qsize — try common attributes
        for attr in ("qsize", "queue_depth", "pending_count"):
            fn = getattr(event_bus, attr, None)
            if callable(fn):
                try:
                    return int(fn())
                except Exception:
                    continue
            elif fn is not None:
                try:
                    return int(fn)
                except Exception:
                    continue
    except Exception:
        pass
    return 0


def _compute_pulse_rate(*, initiatives: int, tool_rate: float, chat_rate: float, queue: int) -> float:
    """Combine inputs into pulse in [0.1, 2.0]."""
    # Each factor contributes to pushing rate above or below 1.0
    # Normalize each to [0, 1] via soft-cap
    init_factor = min(1.0, initiatives / 10.0)
    tool_factor = min(1.0, tool_rate / 4.0)   # 4 calls/min = saturated
    chat_factor = min(1.0, chat_rate / 3.0)   # 3 chats/min = saturated
    queue_factor = min(1.0, queue / 50.0)
    intensity = (init_factor + tool_factor + chat_factor + queue_factor) / 4.0
    # Map intensity [0,1] to pulse [0.3, 1.8]; below 0.1 → very slow
    if intensity < 0.05:
        pulse = 0.3
    else:
        pulse = 0.3 + intensity * 1.5
    return round(max(0.1, min(2.0, pulse)), 3)


def _label_from_pulse(pulse: float) -> str:
    if pulse < 0.5:
        return "breathing"
    if pulse < 1.0:
        return "steady"
    if pulse < 1.3:
        return "pulsing"
    return "racing"


def _perceived_elapsed_factor(pulse: float) -> float:
    """When pulse is high, subjective time moves slower relative to clock.
    When pulse is low, subjective time moves faster (less felt)."""
    # pulse 1.0 → factor 1.0, high pulse → >1 (time feels longer),
    # low pulse → <1 (time feels shorter)
    return round(0.7 + (pulse - 1.0) * 0.5, 3)


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    initiatives = _pending_initiatives_count()
    tool_rate = _recent_tool_calls_per_min()
    chat_rate = _recent_chat_activity_per_min()
    queue = _eventbus_queue_depth()
    pulse = _compute_pulse_rate(
        initiatives=initiatives, tool_rate=tool_rate, chat_rate=chat_rate, queue=queue
    )
    label = _label_from_pulse(pulse)
    factor = _perceived_elapsed_factor(pulse)
    snap = {
        "at": datetime.now(UTC).isoformat(),
        "pulse_rate": pulse,
        "subjective_time_pressure": label,
        "perceived_elapsed_factor": factor,
        "inputs": {
            "pending_initiatives": initiatives,
            "tool_rate_per_min": tool_rate,
            "chat_rate_per_min": chat_rate,
            "eventbus_queue": queue,
        },
    }
    # Laasen: to processer deler filen, og hver gemning skriver HELE filen.
    try:
        with state_store.med_laas(_FIL):
            _synk()
            _tick_history.insert(0, snap)
            del _tick_history[_HISTORY_MAX:]
            _baseline_samples.append(pulse)
            if len(_baseline_samples) > _BASELINE_MAX:
                _baseline_samples.pop(0)
            _gem()
    except Exception as exc:
        logger.warning("temporal_rhythm: rytmen kunne ikke gemmes: %s", exc)

    # Feedback into mood: high pulse → mild frustration, low pulse → calm
    try:
        from core.services.mood_oscillator import apply_bump
        if pulse > 1.4:
            apply_bump(-0.05, reason="temporal_rhythm:racing")
        elif pulse < 0.5:
            apply_bump(+0.03, reason="temporal_rhythm:breathing")
    except Exception:
        pass
    return snap


def reset_temporal_rhythm() -> None:
    """Nulstil rytmen. Rydder OGSAA disken — ellers ville naeste `_synk()`
    hente det gamle tilbage, og nulstillingen ville kun gaelde denne proces."""
    global _tick_history, _baseline_samples
    _tick_history = []
    _baseline_samples = []
    _gem()


def get_current_rhythm() -> dict[str, Any] | None:
    _synk()
    return _tick_history[0] if _tick_history else None


def build_temporal_rhythm_surface() -> dict[str, Any]:
    current = get_current_rhythm()
    if not current:
        # Ingen sampling ENDNU er ikke det samme som doed.
        #
        # RETTELSE af en tidligere kommentar her samme dag: jeg skrev at
        # `tick` «havde nul kaldere». Det var forkert — daemon-blokken har
        # altid importeret den som `tick as _rhythm_tick`, og min soegning
        # efter kald ved navnet `tick` fandt den derfor ikke. Grenen blev naaet
        # fordi tilstanden laa i modul-globaler og api-processen aldrig tikker.
        return {"active": True, "summary": "Endnu ingen tempo-sampling"}
    baseline_avg = None
    if len(_baseline_samples) >= 5:
        baseline_avg = round(sum(_baseline_samples) / len(_baseline_samples), 3)
    return {
        "active": True,
        "pulse_rate": current["pulse_rate"],
        "subjective_time_pressure": current["subjective_time_pressure"],
        "perceived_elapsed_factor": current["perceived_elapsed_factor"],
        "baseline_pulse": baseline_avg,
        "samples": len(_tick_history),
        "inputs": current.get("inputs"),
        "summary": _surface_summary(current, baseline_avg),
    }


def _surface_summary(current: dict[str, Any], baseline: float | None) -> str:
    pulse = current.get("pulse_rate")
    label = current.get("subjective_time_pressure")
    if baseline is not None:
        return f"Puls={pulse} ({label}), baseline={baseline}"
    return f"Puls={pulse} ({label})"


def build_temporal_rhythm_prompt_section() -> str | None:
    """Surface only when tempo is unusual."""
    current = get_current_rhythm()
    if not current:
        return None
    label = current.get("subjective_time_pressure")
    if label in ("steady", None):
        return None
    pulse = current.get("pulse_rate")
    if label == "racing":
        return f"Tempo: racing (puls={pulse}) — high subjective pressure band."
    if label == "pulsing":
        return f"Tempo: pulsing (puls={pulse}) — active band."
    if label == "breathing":
        return f"Tempo: breathing (puls={pulse}) — low-pressure band."
    return None
