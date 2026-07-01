"""core/services/central_self_observe.py

Fase 1 — Centralens selv-observation (spec §23.3 #2 / §24.5).

I dag publicerer Centralen ``central.observed``/``central.error`` men INTET abonnerer:
dens egen decide-latency, breaker-trips og trace-tryk er usynlige for den selv. Den
eksisterende ``central_self_health`` prober decide/observe + eskalerer — men måler ikke
DRIFT over tid mod en stabil baseline. Denne producer lukker det hul.

BINDENDE (§24.5 — dette er den farligste selv-reference i hele systemet):
  * STRENGT READ-ONLY og UDLØSER-FRI. Ingen central-meta-måling må trigge learning,
    healing eller threshold-justering. Vi observer + registrerer i tidsserien — punktum.
    (Ellers ændrer målingen det målte, og en støjende latency-spike kan amplificeres til
    en falsk "central degraderer"→heling.)
  * Vi emitterer KUN ``observe``-records (kind=observe) — aldrig ``decide``. Så vores egne
    fyringer indgår ALDRIG i decide-latency-metrikken → ingen selv-forstærkning.
  * Baseline persisteres over genstart MEN med OUTLIER-CLIPPING: én spike kan ikke blive
    baseline (§24.5).

Feed'er per-nerve tidsserien (central_timeseries) under (system, central_meta), så drift
er aflæselig uden at røre den globale 2000-buffer.
"""
from __future__ import annotations

from typing import Any

from core.services import central_timeseries, central_trace, shared_cache
from core.services.central_core import central

# Hvor mange nylige records vi kigger på pr. tick for at beregne decide-latency-fordelingen.
_WINDOW = 500
_BASELINE_KEY = "central:self_observe:latency_p95_baseline"
_BASELINE_TTL = 604800.0  # 7 dage; genskrives hvert tick → persisterer reelt over genstart.
_EWMA_ALPHA = 0.2         # ny vægt; 0.2 = træg baseline, robust mod enkelt-spikes.
_CLIP_FACTOR = 3.0        # et sample klippes til baseline*3 før det opdaterer baseline.


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = k - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def _get_baseline() -> float | None:
    try:
        val = shared_cache.get(_BASELINE_KEY)
        if isinstance(val, dict) and "p95" in val:
            return float(val["p95"])
        if val is not None:
            return float(val)
    except Exception:
        pass
    return None


def _set_baseline(p95: float) -> None:
    try:
        shared_cache.set(_BASELINE_KEY, {"p95": float(p95)}, ttl_seconds=_BASELINE_TTL)
    except Exception:
        pass


def _open_breaker_count() -> int:
    try:
        return len(central()._breaker.open_nerves())  # read-only
    except Exception:
        return 0


def sample_self_metrics() -> dict[str, Any]:
    """Læs Centralens egen trace + breaker-state og beregn helbreds-metrikker.

    Ren funktion (bortset fra baseline-persistering). Kaster aldrig."""
    metrics: dict[str, Any] = {
        "decide_count": 0, "observe_count": 0, "error_count": 0, "red_count": 0,
        "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0,
        "open_breakers": 0, "trace_dropped": 0, "trace_fill": 0,
        "latency_baseline_ms": 0.0, "latency_drift_ms": 0.0,
    }
    try:
        sink = central_trace.sink()
        recent = sink.recent(limit=_WINDOW)
        metrics["trace_fill"] = len(recent)
        try:
            metrics["trace_dropped"] = int(sink.dropped)
        except Exception:
            pass

        latencies: list[float] = []
        for r in recent:
            kind = getattr(r, "kind", "")
            if kind == "decide":
                metrics["decide_count"] += 1
                lm = getattr(r, "latency_ms", 0) or 0
                try:
                    latencies.append(float(lm))
                except Exception:
                    pass
                if getattr(r, "decision", "") == "red":
                    metrics["red_count"] += 1
            elif kind == "observe":
                metrics["observe_count"] += 1
            elif kind == "error":
                metrics["error_count"] += 1

        if latencies:
            latencies.sort()
            metrics["p50_ms"] = round(_percentile(latencies, 0.50), 2)
            metrics["p95_ms"] = round(_percentile(latencies, 0.95), 2)
            metrics["max_ms"] = round(latencies[-1], 2)

        metrics["open_breakers"] = _open_breaker_count()

        # Baseline-drift på p95 med outlier-clipping (§24.5).
        current_p95 = metrics["p95_ms"]
        baseline = _get_baseline()
        if baseline is None:
            # Første gang: sæt baseline = nuværende (ingen drift at rapportere endnu).
            baseline = current_p95
            metrics["latency_drift_ms"] = 0.0
        else:
            metrics["latency_drift_ms"] = round(current_p95 - baseline, 2)
        metrics["latency_baseline_ms"] = round(baseline, 2)

        # Opdatér baseline TRÆGT + clip sample så én spike ikke forgifter den.
        clipped = min(current_p95, baseline * _CLIP_FACTOR + 10.0)
        new_baseline = (1.0 - _EWMA_ALPHA) * baseline + _EWMA_ALPHA * clipped
        _set_baseline(new_baseline)
    except Exception:
        pass
    return metrics


def run_self_observe_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: mål Centralens egne helbreds-metrikker og OBSERVE dem.

    UDLØSER-FRI (§24.5): observer + registrer i tidsserien. Ingen eskalering, ingen
    heling, ingen threshold-justering. Kaster aldrig.
    """
    metrics = sample_self_metrics()
    try:
        central().observe({
            "cluster": "system",
            "nerve": "central_meta",
            "kind": "observe",
            **metrics,
        })
    except Exception:
        pass
    try:
        # Registrér p95 som seriens værdi; drift+breakers som meta (til trend-aflæsning).
        central_timeseries.record(
            "system", "central_meta",
            value=float(metrics.get("p95_ms") or 0.0),
            meta={
                "drift_ms": metrics.get("latency_drift_ms"),
                "open_breakers": metrics.get("open_breakers"),
                "error_count": metrics.get("error_count"),
            },
        )
    except Exception:
        pass
    return {"status": "ok", **metrics}


def register_self_observe_producer() -> None:
    """Registrér selv-observationen som cadence-producer. Observe-only → ingen visible-grace.
    Kører hvert ~5 min: hyppigt nok til at se drift, roligt nok til at være billigt."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_self_observe",
        cooldown_minutes=5,
        visible_grace_minutes=0,
        run_fn=run_self_observe_tick,
        priority=3,
    ))
