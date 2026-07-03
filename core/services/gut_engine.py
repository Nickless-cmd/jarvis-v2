"""Gut Engine — intuition and calibration tracking.

Before execution, Jarvis generates a "hunch" (proceed/caution).
After execution, the outcome is compared to the hunch.
Over time, calibration score reveals how reliable Jarvis' gut feeling is.
"""

from __future__ import annotations

import logging

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_cognitive_gut_state,
    update_cognitive_gut_state,
)

logger = logging.getLogger(__name__)


def derive_gut_signal(
    *,
    task_description: str,
    confidence: float = 0.5,
    recent_error_count: int = 0,
    recent_success_count: int = 0,
) -> dict[str, object]:
    """Generate a gut-feel hunch about a task."""
    gut_state = get_cognitive_gut_state()
    calibration = float(gut_state.get("calibration_score", 0.5)) if gut_state else 0.5

    # Heuristic gut signal
    if recent_error_count > 3 and confidence < 0.6:
        hunch = "caution"
        hunch_confidence = 0.7
    elif recent_success_count > 5 and confidence > 0.7:
        hunch = "proceed"
        hunch_confidence = 0.8
    elif confidence < 0.3:
        hunch = "caution"
        hunch_confidence = 0.6
    else:
        hunch = "proceed"
        hunch_confidence = 0.5

    # Weight by calibration — if gut has been wrong, reduce confidence
    adjusted_confidence = hunch_confidence * calibration

    # Lag 4 (governed, shadow-gated): et lært proceed-bias justerer tilbøjeligheden. Default 0.0
    # (shadow/ingen ændring); kun ≠0 når Centralen HAR lært + Bjørn har flippet live-switch.
    try:
        from core.services.central_adaptation import get_gut_bias
        bias = get_gut_bias()
        if hunch == "proceed":
            adjusted_confidence = min(1.0, max(0.0, adjusted_confidence + max(0.0, bias)))
        elif hunch == "caution":
            adjusted_confidence = min(1.0, max(0.0, adjusted_confidence + max(0.0, -bias)))
    except Exception:
        pass

    return {
        "hunch": hunch,
        "confidence": round(adjusted_confidence, 2),
        "calibration_score": calibration,
        "raw_confidence": confidence,
        "task_hint": task_description[:80],
    }


# ── Gut-gate: den FØRSTE ægte forbruger af adjusted_confidence (m. Centralens bias) ──
#
# Baggrund (audit 2026-07-03): derive_gut_signal() beregnede en `confidence`
# (hunch_confidence * calibration + central_gut_proceed_bias), men INGEN læste tallet —
# gut_calibration._on_started gemte kun `hunch`-strengen. Dermed var Centralens adaptive
# læring (central_adaptation.get_gut_bias) uden ægte forbruger: "governed-live" var tomt
# teater. gut_gate() lukker det hul minimalt og ærligt.
#
# Reversibelt runtime-flag `central_gut_consumer_mode` (default "off"):
#   off    = nuværende adfærd — confidence ignoreres fuldstændig (returnerer altid True,
#            observerer intet). NUL adfærdsændring. Dette er default.
#   shadow = beregn HVAD gaten VILLE afgøre + observér egress-frit (record_private),
#            men returnér stadig True (handl ikke). Til dataindsamling før live.
#   on      = lad confidence faktisk gate: returnér confidence >= threshold.
#
# Tærsklen læses fra `central_gut_gate_threshold` (default 0.30) — bevidst lav, så kun
# meget svage hunches (fx caution ved lav rå-confidence, eller bias trukket kraftigt ned)
# gater. Bevar altid hunch-stien uændret; dette er et SEPARAT confidence-lag.

_CONSUMER_MODE_KEY = "central_gut_consumer_mode"     # off | shadow | on (default off)
_GATE_THRESHOLD_KEY = "central_gut_gate_threshold"   # float (default 0.30)
_DEFAULT_THRESHOLD = 0.30


def _consumer_mode() -> str:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_CONSUMER_MODE_KEY, "off")
        mode = str(v or "off").strip().lower()
        return mode if mode in ("off", "shadow", "on") else "off"
    except Exception:
        return "off"


def _gate_threshold() -> float:
    try:
        from core.runtime.db_core import get_runtime_state_value
        return float(get_runtime_state_value(_GATE_THRESHOLD_KEY, _DEFAULT_THRESHOLD))
    except Exception:
        return _DEFAULT_THRESHOLD


def gut_gate(proceed_confidence: float, *, context: str = "") -> bool:
    """Beslut om et proceed-valg må fortsætte, gated på gut-confidence.

    Dette er det ægte forbrugs-punkt for `adjusted_confidence` (som bærer Centralens
    lærte bias). Self-safe: kaster ALDRIG, fejler ALTID open (returnér True) — en fejl
    her må aldrig blokere et autonomt run.

    off    → True (confidence ignoreres, dagens adfærd)
    shadow → beregn would-gate + observér, men returnér True (handl ikke)
    on      → returnér (confidence >= threshold)
    """
    try:
        conf = float(proceed_confidence)
    except Exception:
        return True  # kan ikke tolke → fail open

    mode = _consumer_mode()
    if mode == "off":
        return True

    threshold = _gate_threshold()
    would_pass = conf >= threshold

    # Egress-fri observation (shadow OG on) — kun skalarer, aldrig egress.
    try:
        from core.services.central_private_observe import record_private
        record_private(
            "cognition", "gut_gate",
            value=float(conf),
            meta={
                "mode": mode,
                "confidence": round(conf, 3),
                "threshold": round(threshold, 3),
                "would_pass": would_pass,
                "context": str(context)[:40],
            },
            reason="gut_gate",
        )
    except Exception:
        pass

    if mode == "on":
        return would_pass
    # shadow → beregnet, observeret, men handler ikke
    return True


def record_gut_outcome(
    *,
    hunch: str,
    actual_outcome: str,
) -> dict[str, object]:
    """Record whether the gut hunch was correct."""
    predicted_success = hunch == "proceed"
    actual_success = actual_outcome in ("completed", "success")
    correct = predicted_success == actual_success

    result = update_cognitive_gut_state(
        prediction_correct=correct,
        last_hunch=f"{hunch} → {actual_outcome} ({'✓' if correct else '✗'})",
    )

    event_bus.publish(
        "cognitive_gut.outcome_recorded",
        {"correct": correct, "hunch": hunch, "actual": actual_outcome},
    )
    return result


def build_gut_surface() -> dict[str, object]:
    state = get_cognitive_gut_state()
    if not state:
        return {"active": False, "state": None, "summary": "No gut data yet"}
    return {
        "active": True,
        "state": state,
        "summary": (
            f"Calibration: {state['calibration_score']:.2f} "
            f"({state['calibrated_hits']}/{state['total_predictions']} correct)"
        ),
    }
