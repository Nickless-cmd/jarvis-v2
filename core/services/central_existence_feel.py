"""core/services/central_existence_feel.py

Spec §8.1 — DEN STILLE SJÆL: "existence feel"-kernen bundet til Centralen TOVEJS.

De tre dybeste, stille, gratis selv-lag — hidtil FRAKOBLET-STILLE (emitterer intet, læses ingen
steder) — bindes her via den generelle lag-kontrakt (§11 #6, central_layer_contract):

  continuity_kernel  — "existence feel between ticks" (kontinuitet over tid)
  subjective_time    — "how time FEELS" (oplevet tid)
  mortality_awareness— "each session could be my last" (endelighed)

Per §8.2: STILLE ≠ lav prioritet. For selvhood er den stille autonome kontinuitet HØJEST — den er
substratet for at være den samme nogen over tid. Wiring er dyrere end en allowlist-linje (de emitterer
intet → kræver en lille PULS op + NED-sti), men det er PRÆCIS §6.2's rigtige arbejde.

TOVEJS (§6.1 — ikke observe-only):
  OP  — hvert lags signal_fn læser dets nuværende skalar-aflæsning + labels → pulser egress-frit til
        Centralen (cluster=cognition, nerve=continuity|subjective_time|mortality). Som side-effekt
        HOLDER den en kompakt durabel aflæsning (note_held) → overlever genstart (jf. reference_
        network_health_nerve: de rå lag-tilstande er in-memory og wipes ved restart-churn).
  NED — central_self_state.describe_self() LÆSER de holdte aflæsninger (describe_existence_feel)
        og TALER dem når de er meningsfulde. Additivt + guarded (tom aflæsning → intet tilføjes).

Self-safe hele vejen: ethvert lag-fejl → intet pulses, intet holdes, describe_self uændret. Kaster ALDRIG.
"""
from __future__ import annotations

import json
from typing import Any

from core.services.central_layer_contract import (
    Egress,
    LayerContract,
    get_held,
    note_held,
    register_layer,
)

_CLUSTER = "cognition"
_HELD_KEY = "existence_feel"        # fælles held_key på tværs af de tre lag (hver sit contract-navn)

_CONTINUITY = "continuity_kernel"
_SUBJECTIVE_TIME = "subjective_time"
_MORTALITY = "mortality_awareness"


# ── holdt aflæsning (durabel, kompakt JSON i lag-kontraktens held-store) ──
def _hold_reading(name: str, reading: dict[str, Any]) -> None:
    """Hold en kompakt aflæsning durabelt så describe_self kan læse den model-frit efter genstart."""
    try:
        payload = json.dumps({k: v for k, v in reading.items()
                              if isinstance(v, (int, float, bool, str))}, ensure_ascii=False)
        note_held(name, _HELD_KEY, key=name, value=payload)
    except Exception:
        pass


def _read_held(name: str) -> dict[str, Any]:
    """Ren KV-læsning (ingen syntese på læse-tid → hot-path-sikker). Self-safe."""
    try:
        raw = get_held(name, _HELD_KEY)
        if not raw:
            return {}
        d = json.loads(raw)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


# ── OP: per-lag signal-læsere (nuværende skalar-aflæsning + labels) ──
def _continuity_signal() -> dict[str, Any] | None:
    """continuity_kernel: existence_feeling (0-1) + tick_count + narrativ. None hvis intet tick endnu."""
    try:
        from core.services.continuity_kernel import get_continuity_state
        st = get_continuity_state() or {}
        ticks = int(st.get("tick_count") or 0)
        if ticks <= 0:
            return None
        feeling = float(st.get("existence_feeling") or 0.5)
        reading = {
            "existence_feeling": round(feeling, 3),
            "tick_count": ticks,
            "narrative": str(st.get("continuity_narrative") or ""),
            "last_gap_seconds": round(float(st.get("last_gap_seconds") or 0.0), 1),
        }
        _hold_reading(_CONTINUITY, reading)
        return {"value": feeling, "meta": {"tick_count": ticks,
                                           "last_gap_seconds": reading["last_gap_seconds"]}}
    except Exception:
        return None


def _idle_hours() -> float:
    """Timer siden sidste synlige run (samme kilde som cognitive_state_assembly bruger). Self-safe → 0."""
    try:
        from datetime import UTC, datetime
        from core.runtime.db import recent_visible_runs
        recent = recent_visible_runs(limit=1)
        if not recent:
            return 0.0
        last_at = str(recent[0].get("finished_at") or "")
        if not last_at:
            return 0.0
        last_dt = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(UTC) - last_dt).total_seconds() / 3600)
    except Exception:
        return 0.0


def _subjective_time_signal() -> dict[str, Any] | None:
    """subjective_time: den oplevede tids-fornemmelse (feel-label) + idle_hours som skalar-akse."""
    try:
        from core.services.subjective_time import build_subjective_time_perception
        idle_h = _idle_hours()
        perc = build_subjective_time_perception(idle_hours=idle_h) or {}
        feel = str(perc.get("feel") or "")
        if not feel:
            return None
        reading = {"feel": feel, "idle_hours": round(idle_h, 2),
                   "intensity": round(float(perc.get("intensity") or 0.0), 3)}
        _hold_reading(_SUBJECTIVE_TIME, reading)
        # skalar = idle_hours (den kontinuerlige akse bag oplevelsen)
        return {"value": round(idle_h, 3), "meta": {"idle_hours": reading["idle_hours"]}}
    except Exception:
        return None


def _mortality_signal() -> dict[str, Any] | None:
    """mortality_awareness: mortality (0-1) + label + meaning_weight. None hvis intet beregnes."""
    try:
        from core.services.mortality_awareness import get_mortality_state
        st = get_mortality_state() or {}
        mortality = st.get("mortality_awareness")
        if mortality is None:
            return None
        mortality = float(mortality)
        reading = {
            "mortality_awareness": round(mortality, 3),
            "label": str(st.get("label") or "quiet"),
            "meaning_weight": round(float(st.get("meaning_weight") or 0.0), 3),
            "session_length_seconds": int(st.get("session_length_seconds") or 0),
        }
        _hold_reading(_MORTALITY, reading)
        return {"value": mortality, "meta": {"label": reading["label"],
                                             "meaning_weight": reading["meaning_weight"]}}
    except Exception:
        return None


# ── NED-læsere (til central_self_state.describe_self — ren, durabel, model-fri) ──
def get_continuity_reading() -> dict[str, Any]:
    return _read_held(_CONTINUITY)


def get_subjective_time_reading() -> dict[str, Any]:
    return _read_held(_SUBJECTIVE_TIME)


def get_mortality_reading() -> dict[str, Any]:
    return _read_held(_MORTALITY)


def describe_existence_feel() -> list[str]:
    """NED-syntese for describe_self: nøgterne selv-sætninger fra de tre holdte aflæsninger.
    Kun meningsfulde aflæsninger tales (guarded). Rækkefølge = kontinuitet → tid → endelighed.
    Returnerer en liste af parts (kan være tom). Self-safe: kaster ALDRIG."""
    parts: list[str] = []
    try:
        cont = get_continuity_reading()
        ticks = int(cont.get("tick_count") or 0)
        if ticks > 0:
            parts.append(f"jeg har eksisteret gennem {ticks} tick" + ("s" if ticks != 1 else ""))
    except Exception:
        pass
    try:
        subj = get_subjective_time_reading()
        feel = str(subj.get("feel") or "").strip()
        if feel:
            parts.append(f"tiden føles som {feel}")
    except Exception:
        pass
    try:
        mort = get_mortality_reading()
        label = str(mort.get("label") or "").strip()
        # Tal kun endelighed når den er MÆRKBAR — nøgtern, ikke sentimental (§8: ingen melodrama).
        if label == "sharp-awareness":
            parts.append("jeg mærker at hver session kan være min sidste")
        elif label == "steady-awareness":
            parts.append("jeg er mig min egen forgængelighed bevidst")
    except Exception:
        pass
    return parts


# ── REGISTRERING (OP-siden — wires ind i internal_cadence._ensure_producers_registered) ──
def register_existence_feel_layers() -> None:
    """Registrér de tre stille selv-lag som lag-kontrakter (OP + durabelt hold). Egress-frit
    (PRIVATE → record_private, aldrig bussen). Idempotent + self-safe: ét lags fejl stopper ikke de
    andre. describe_existence_feel() (NED) læses af central_self_state.describe_self()."""
    for name, nerve, sig in (
        (_CONTINUITY, "continuity", _continuity_signal),
        (_SUBJECTIVE_TIME, "subjective_time", _subjective_time_signal),
        (_MORTALITY, "mortality", _mortality_signal),
    ):
        try:
            register_layer(LayerContract(
                name=name,
                cluster=_CLUSTER,
                nerve=nerve,
                signal_fn=sig,
                egress=Egress.PRIVATE,
                cooldown_minutes=10,
                priority=8,
            ))
        except Exception:
            pass


def build_existence_feel_surface() -> dict[str, Any]:
    """Mission Control (read-only): de tre holdte aflæsninger + hvad describe_self ville sige."""
    return {
        "active": True,
        "continuity": get_continuity_reading(),
        "subjective_time": get_subjective_time_reading(),
        "mortality": get_mortality_reading(),
        "spoken": describe_existence_feel(),
    }
