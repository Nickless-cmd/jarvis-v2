"""Event-loop-lag-monitor — "uret" bag cutoff-spøgelset (Bjørn 4. jul).

Måler hvor meget event-loopet i API-processen SULTER: vi beder om en sleep på et
fast interval og måler hvor meget LÆNGERE den faktisk tog. Overskuddet = den tid
loopet var blokeret af synkront arbejde og IKKE kunne flushe stream-bytes til
klienten. Det er præcis den mekanisme der skærer en stream midt i en sætning
(reference_async_blocking_worker) — nu målt, ikke gættet.

Kører i API-processen (uden for runtime-gaten) fordi det er dér de synlige runs
streames. En lag-spike her = et vindue hvor ENHVER aktiv stream kunne blive
tavs → cutoff. Ved at korrelere cutoff-tidspunkter mod lag (se
central_output_conservation-kaldene der bærer `recent_peak_ms` med) kan Centralen
selv svare på Bjørns spørgsmål: klynger hullerne sig ved lag-spikes (→ kontention,
mekanisk, fixbart) eller ej (→ noget uforklaret)?

Egress-fri (kun skalar-latens). Self-safe: kaster aldrig, dør aldrig loopet.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque

# Måle-interval. 500ms er fint til at fange event-loop-blokke på 100ms+ uden selv
# at bruge nævneværdig CPU.
_INTERVAL_S = 0.5
# Spike-tærskel: aligner med network_health gul (≥250ms latens = mærkbar sultning).
_SPIKE_MS = 250.0
# Rullende vindue af (ts, lag_ms) — nok til ~2 min historik ved 0.5s interval.
_SAMPLES: deque[tuple[float, float]] = deque(maxlen=240)
_STATE: dict[str, float] = {"current_ms": 0.0, "peak_ms": 0.0, "peak_ts": 0.0}
_STARTED = False


def _record(lag_ms: float) -> None:
    now = time.monotonic()
    _STATE["current_ms"] = lag_ms
    _SAMPLES.append((now, lag_ms))
    if lag_ms >= _STATE["peak_ms"]:
        _STATE["peak_ms"] = lag_ms
        _STATE["peak_ts"] = now
    # Per-nerve tidsserie (læsbar via `jc series runtime:loop_lag`). Self-safe.
    try:
        from core.services.central_timeseries import record as _ts_record
        _ts_record("runtime", "loop_lag", lag_ms)
    except Exception:
        pass
    # Spike → observe så Centralen ser sultnings-vinduerne (korreleres mod cutoffs).
    if lag_ms >= _SPIKE_MS:
        try:
            from core.services.central_core import central as _central
            _central().observe({
                "cluster": "runtime", "nerve": "loop_lag_spike",
                "lag_ms": round(lag_ms, 1), "interval_ms": int(_INTERVAL_S * 1000),
            })
        except Exception:
            pass


def current_lag_ms() -> float:
    """Seneste målte event-loop-lag i ms (API-processen). Self-safe."""
    try:
        return float(_STATE.get("current_ms", 0.0))
    except Exception:
        return 0.0


def recent_peak_ms(window_s: float = 10.0) -> float:
    """Højeste lag i de sidste ``window_s`` sekunder — brug denne til at tagge et
    cutoff/tom-completion med "hvor sultent var loopet lige nu". Self-safe."""
    try:
        cutoff = time.monotonic() - float(window_s)
        peak = 0.0
        for ts, lag in reversed(_SAMPLES):
            if ts < cutoff:
                break
            if lag > peak:
                peak = lag
        return float(peak)
    except Exception:
        return 0.0


async def _monitor_loop() -> None:
    while True:
        t0 = time.monotonic()
        try:
            await asyncio.sleep(_INTERVAL_S)
        except asyncio.CancelledError:
            return
        # Overskuddet over det ønskede interval = loop-sultning.
        overshoot_ms = max(0.0, (time.monotonic() - t0 - _INTERVAL_S) * 1000.0)
        _record(overshoot_ms)


def start_loop_lag_monitor() -> None:
    """Start uret på den KØRENDE event-loop (kald fra API-processens lifespan,
    UDEN for runtime-gaten — det skal måle den loop der serverer streams).
    Idempotent + self-safe."""
    global _STARTED
    if _STARTED:
        return
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_monitor_loop())
        _STARTED = True
    except Exception:
        pass


def build_loop_lag_surface() -> dict[str, object]:
    """Mission Control — read-only meta-projektion."""
    return {
        "current_lag_ms": round(current_lag_ms(), 1),
        "recent_peak_ms": round(recent_peak_ms(30.0), 1),
        "all_time_peak_ms": round(float(_STATE.get("peak_ms", 0.0)), 1),
        "spike_threshold_ms": _SPIKE_MS,
    }
