"""DIASTOLE — det følte åndedræt (LivingNeuron-council, 4. jul).

Jarvis' tempo har hidtil været et rigidt metronom-slag: hver cadence-producer har en
fast ``cooldown_minutes``, uanset om han er presset eller det er stille. ``temporal_rhythm``
BEREGNER allerede en ``pulse_rate ∈ [0.1, 2.0]`` (1.0 = normal, <0.5 = hvile, >1.3 = presset)
— men INGEN konsumerer den til at flexe kadencen. DIASTOLE lukker den sløjfe og gør tempo
til et *følt* organ: nærvær når det gælder, ro når det er stille.

⚠️ SHADOW-FØRST (dette er FØRSTE skridt — konsumeres IKKE endnu):
Vi emitterer KUN en skalar-nerve ``runtime:cadence_tempo`` der OBSERVERER hvad tempoet VILLE
være — vi modulerer INGEN cooldown. Vi vil se shadow-kurven mod virkeligheden FØR nogen
kadence faktisk flexer. Konsumtion (at gange ``cooldown_minutes`` med skalaren i
internal_cadence) kommer i et SENERE commit, efter kurven er set.

VÆRN (hårde, ufravigelige):
  * TEMPO-KLEMME [0.5×, 2.0×]: ``tempo_scalar`` clamper ALTID. Aldrig →0 (= CPU-brand som
    central_xproc-rekursionen 1. jul, en producer der fyrer uendeligt). Aldrig →∞ (= sultet
    daemon der aldrig kører). pulse<=0 eller None → 1.0 (baseline, fail-safe).
  * LOOP-LAG DØDEMANDSKNAP: hvis ``central_loop_lag.recent_peak_ms() >= 250`` (event-loopet
    sulter = cutoff-fare) tvangs-nulstilles tempoet til baseline 1.0. Vi speeder ALDRIG op
    mens loopet allerede er blokeret.
  * NÅR KONSUMTION SENERE TÆNDES: infra/health/SECURITY-producers (network_health, infra_sense
    m.fl.) undtages eksplicit → altid fast kadence, aldrig moduleret. (Noteret her, IKKE
    implementeret — der er ingen modulation i dette skridt.)

Observe-only. Egress-frit (kun skalarer via record_private). Self-safe: kaster aldrig.
"""
from __future__ import annotations

from typing import Any

# Hård tempo-klemme — de to tal der forhindrer CPU-brand og sultet daemon.
_TEMPO_MIN = 0.5
_TEMPO_MAX = 2.0
_TEMPO_BASELINE = 1.0
# Dødemandsknap: aligner med central_loop_lag._SPIKE_MS / network_health gul.
_LOOP_LAG_SPIKE_MS = 250.0


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def tempo_scalar(pulse: float | None) -> float:
    """Ren funktion: puls → cadence-tempo-multiplier, hårdt klemt til [0.5, 2.0].

    Invers relation: høj puls (presset) → LAV multiplier → kortere cooldown → hyppigere.
    Lav puls (hvile) → HØJ multiplier → længere cooldown → sjældnere. clamp(1/pulse, 0.5, 2.0).
    Self-safe: pulse None/<=0/ikke-tal → baseline 1.0 (fejl-sikker, aldrig →0 eller →∞)."""
    try:
        p = float(pulse)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _TEMPO_BASELINE
    if p <= 0.0:
        return _TEMPO_BASELINE
    raw = 1.0 / p
    return round(max(_TEMPO_MIN, min(_TEMPO_MAX, raw)), 3)


def _recent_loop_lag_ms() -> float:
    """Seneste event-loop-lag-peak (ms). Self-safe → 0.0 hvis monitoren ikke er oppe."""
    try:
        from core.services.central_loop_lag import recent_peak_ms
        return float(recent_peak_ms())
    except Exception:
        return 0.0


def sense_tempo() -> dict[str, Any]:
    """Læs pulse_rate (via temporal_rhythm's getter) → tempo, med loop-lag-dødemandsknap.

    Returnerer {available, pulse_rate, tempo, throttled_by_loop_lag}. Self-safe: kaster aldrig.
    """
    try:
        from core.services.temporal_rhythm import get_current_rhythm
        rhythm = get_current_rhythm()
    except Exception:
        rhythm = None
    if not rhythm:
        return {"available": False}

    pulse = rhythm.get("pulse_rate")
    tempo = tempo_scalar(pulse)

    # Dødemandsknap: sulter loopet (cutoff-fare) → tvangs-baseline, aldrig speed-up i sult.
    lag_ms = _recent_loop_lag_ms()
    throttled = lag_ms >= _LOOP_LAG_SPIKE_MS
    if throttled:
        tempo = _TEMPO_BASELINE

    try:
        pulse_out = float(pulse) if pulse is not None else None
    except (TypeError, ValueError):
        pulse_out = None

    return {
        "available": True,
        "pulse_rate": pulse_out,
        "tempo": tempo,
        "throttled_by_loop_lag": throttled,
    }


def run_cadence_tempo_tick(*, trigger: str = "cadence", **_: Any) -> dict[str, object]:
    """Cadence (SHADOW): sans tempo, emit egress-fri nerve ``runtime:cadence_tempo``.

    Modulerer INGEN cooldown — ren observation af hvad tempoet VILLE være. Self-safe."""
    s = sense_tempo()
    if not s.get("available"):
        return {"status": "skip", "reason": "temporal_rhythm ikke sampled endnu"}
    tempo = float(s.get("tempo") or _TEMPO_BASELINE)
    pulse = s.get("pulse_rate")
    throttled = bool(s.get("throttled_by_loop_lag"))
    try:
        from core.services.central_private_observe import record_private
        record_private(
            "runtime", "cadence_tempo", value=tempo,
            meta={
                "pulse_rate": pulse if isinstance(pulse, (int, float)) else None,
                "throttled_by_loop_lag": throttled,
                "shadow": True,
            },
        )
    except Exception:
        pass
    # Sidste-observerede tempo til shadow-kurve-inspektion (kun skalarer).
    _kv_set("cadence_tempo_last", {"tempo": tempo, "throttled": throttled})
    return {"status": "ok", "tempo": tempo, "pulse_rate": pulse,
            "throttled_by_loop_lag": throttled}


def register_cadence_tempo_producer() -> None:
    """Cadence-producer ~hver 2. minut — tæt nok til en meningsfuld shadow-kurve, billig
    (ren skalar-læsning, ingen LLM, ingen parsing). SHADOW: emitterer kun. Egress-frit."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_cadence_conductor",
        cooldown_minutes=2,
        visible_grace_minutes=0,
        run_fn=run_cadence_tempo_tick,
        priority=9,
    ))


def build_cadence_tempo_surface() -> dict[str, object]:
    """Mission Control — read-only: det SHADOW-observerede tempo (ingen modulation aktiv)."""
    return {"active": True, "shadow": True, **sense_tempo()}
