"""Gut Engine — intuition and calibration tracking.

Before execution, Jarvis generates a "hunch" (proceed/caution).
After execution, the outcome is compared to the hunch.
Over time, calibration score reveals how reliable Jarvis' gut feeling is.
"""

from __future__ import annotations

import logging
import time

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_cognitive_gut_state,
    update_cognitive_gut_state,
)

logger = logging.getLogger(__name__)


def _gut_bias() -> float:
    """Læs Lag-4-bias'en (0.0 = shadow/ingen ændring). Én sætning, så kaldestedets try er
    smalt nok til at fange netop den fejl det skal — ikke alt hvad der kommer bagefter."""
    try:
        from core.services.central_adaptation import get_gut_bias
        return float(get_gut_bias())
    except Exception:  # uden Lag-4-signal er bias 0 — hunch-stien er uændret
        return 0.0


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
    # Bias-FRI baseline (12/10-2026): bevares FØR Lag-4 lægges oveni, så counterfactual-
    # tællingen kan svare på hvad gaten VILLE afgøre uden den lærte bias. Uden dette led
    # findes svaret ikke — gaten ser kun den justerede værdi og kan ikke sammenlignes med sig selv.
    confidence_no_bias = adjusted_confidence

    # Lag 4 (governed, shadow-gated): et lært proceed-bias justerer tilbøjeligheden. Default 0.0
    # (shadow/ingen ændring); kun ≠0 når Centralen HAR lært + Bjørn har flippet live-switch.
    #
    # 12/10-2026 — bias'en kan nu TRÆKKE FRA (Bjørn: «lad bias kunne trække fra»). Før klippede
    # begge grene til `max(0.0, ±bias)`, så justeringen ALTID var ≥ 0: musklen kunne kun HÆVE
    # confidence og var strukturelt ude af stand til at afvise noget. Det — ikke manglende data —
    # er grunden til at gaten aldrig efterlod et withhold-spor. Nu er bias'en et ægte FORTEGN,
    # symmetrisk om 0: positiv = maven har fortjent tillid (proceed løftes, caution sænkes),
    # negativ = maven har taget fejl (proceed sænkes, caution løftes). Først nu kan et proceed
    # ende UNDER tærsklen — og dermed stoppes.
    bias = _gut_bias()
    if bias:
        if hunch == "proceed":
            adjusted_confidence = adjusted_confidence + bias
        elif hunch == "caution":
            adjusted_confidence = adjusted_confidence - bias
        adjusted_confidence = min(1.0, max(0.0, adjusted_confidence))

    return {
        "hunch": hunch,
        "confidence": round(adjusted_confidence, 2),
        "confidence_no_bias": round(confidence_no_bias, 2),
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


# Counterfactual-tælling (12/10-2026). To nerves i den EKSISTERENDE ledger — ingen ny tabel.
_COUNTERFACTUAL_NERVE = "gut_gate"
_COUNTERFACTUAL_NERVE_NO_BIAS = "gut_gate_uden_bias"


def _safe_record(ledger: object, nerve: str, decision: str, reason: str) -> None:
    """Ét ledger-kald, indkapslet. En tæller må ALDRIG kunne blokere gaten."""
    try:
        ledger.record(nerve, "cognition", decision, reason=reason)
    except Exception:  # en tæller må ALDRIG kunne blokere gaten — fejler åbent
        return


def _record_counterfactual(
    conf: float,
    would_pass: bool,
    no_bias_confidence: float | None,
    threshold: float,
    mode: str,
) -> None:
    """Optæl gatens afgørelse MED og UDEN den lærte bias. Ren statistik — kaster ALDRIG.

    Bruger de kanoniske decision-værdier (green = passerede, red = afvist), så
    `gate_verdict_ledger.summary()` rapporterer withhold-raten direkte via non_green_pct.
    Skrivningen er en in-memory tæller (ingen DB i hot-pathen); ledgeren flusher på cadence.
    """
    try:
        from core.services import gate_verdict_ledger as ledger
    except Exception:  # ledgeren er valgfri — uden den tæller vi bare ikke
        return

    _safe_record(ledger, _COUNTERFACTUAL_NERVE,
                 "green" if would_pass else "red",
                 f"mode={mode} conf={conf:.3f} thr={threshold:.2f}")
    if no_bias_confidence is None:
        return
    try:
        nb = float(no_bias_confidence)
    except (TypeError, ValueError):  # utolkbar baseline → kun med-bias tælles
        return
    _safe_record(ledger, _COUNTERFACTUAL_NERVE_NO_BIAS,
                 "green" if nb >= threshold else "red",
                 f"conf={nb:.3f} thr={threshold:.2f}")


def gut_gate(
    proceed_confidence: float,
    *,
    context: str = "",
    no_bias_confidence: float | None = None,
) -> bool:
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

    # Counterfactual-tælling (12/10-2026): registrér BÅDE den faktiske afgørelse (med den
    # lærte bias) og hvad gaten ville have afgjort UDEN den. Forskellen er det eneste der
    # kan svare på om erfaringen faktisk flytter en beslutning — uden den findes svaret ikke,
    # fordi bias'en er positiv-only og derfor aldrig efterlader et withhold-spor.
    _record_counterfactual(conf, would_pass, no_bias_confidence, threshold, mode)

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


# ── Pre-flight gate (12/10-2026, Bjørn: «tag gut gate og lad bias kunne trække fra») ──
#
# Gaten lå FØR på `runtime.autonomous_run_started` — et event der fyrer EFTER runnet er
# begyndt. Koden sagde det selv: «vi ANNULLERER ikke run'et her (run er allerede startet —
# vinduet er observations-gate, ikke en pre-flight veto)». Den kunne derfor aldrig stoppe
# noget, uanset hvor lav confidence var. Her er beslutningspunktet: bliver runnet afvist,
# fødes det ikke — `start_autonomous_run` og `start_autonomous_stream_run` kalder denne FØR
# de bygger run-objektet.
#
# BAGKANT (fordi en negativ bias nu kan blokere): højst _MAX_BLOK_PER_TIME blokeringer pr.
# rullende time. Er budgettet brugt, slipper runnet igennem og overkørslen tælles særskilt
# på sin egen nerve. En fejlkalibreret muskel må kunne gøre arbejdet mere forsigtigt — den
# må ALDRIG kunne standse det.

_MAX_BLOK_PER_TIME = 3
_BLOK_VINDUE_SEKUNDER = 3600
_BACKSTOP_NERVE = "gut_gate_backstop"
_blok_tider: list[float] = []


def _blok_budget_brugt(no: float | None = None) -> bool:
    """True når blokerings-budgettet for den rullende time er brugt. Ren — kaster ikke."""
    naa = no if no is not None else time.time()
    graense = naa - _BLOK_VINDUE_SEKUNDER
    _blok_tider[:] = [t for t in _blok_tider if t > graense]
    return len(_blok_tider) >= _MAX_BLOK_PER_TIME


def _record_backstop(conf: float, hunch: str) -> None:
    """Tæl en overkørsel: gaten ville stoppe, men bagkanten slap runnet igennem."""
    try:
        from core.services import gate_verdict_ledger as ledger
    except Exception:  # ledgeren er valgfri — uden den tæller vi bare ikke
        return
    _safe_record(ledger, _BACKSTOP_NERVE, "yellow",
                 f"backstop conf={conf:.3f} hunch={hunch}")


def preflight_gut_gate(*, task_description: str) -> dict[str, object]:
    """PRE-FLIGHT: dan hunch og afgør om et autonomt run må starte. Kaster ALDRIG.

    Fail-open hele vejen: enhver fejl her betyder at runnet starter som før. `allowed=False`
    er den eneste vej til at stoppe noget, og den kræver at confidence ligger under tærsklen
    OG at blokerings-budgettet ikke er brugt.
    """
    try:
        signal = derive_gut_signal(task_description=task_description)
    except Exception:  # kunne ikke danne hunch → slip igennem, det er den sikre side
        return {"allowed": True, "reason": "derive-fejl"}

    conf = float(signal.get("confidence") or 0.0)
    hunch = str(signal.get("hunch") or "proceed")
    try:
        tillad = gut_gate(conf, context="autonomous_run_preflight",
                          no_bias_confidence=signal.get("confidence_no_bias"))
    except Exception:  # gaten er rådgivende — en fejl her må ALDRIG stoppe et run
        return {"allowed": True, "reason": "gate-fejl", "confidence": conf}

    if tillad:
        return {"allowed": True, "confidence": conf, "hunch": hunch}
    if _blok_budget_brugt():
        _record_backstop(conf, hunch)
        return {"allowed": True, "confidence": conf, "hunch": hunch, "backstop": True}

    _blok_tider.append(time.time())
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "gut_gate_withhold", value=conf,
                       meta={"hunch": hunch, "task": task_description[:40],
                             "where": "preflight"},
                       reason="gut_gate_withhold")
    except Exception:  # observationen er egress-fri pynt — uden den stopper vi stadig
        pass
    return {"allowed": False, "confidence": conf, "hunch": hunch}


def preflight_allows(message: str) -> bool:
    """Bekvemmeligheds-indpakning til run-start-stierne: True = start runnet.

    Hele vejen fail-open, så et kaldested kan bruge den uden selv at væbne sig.
    """
    try:
        udfald = preflight_gut_gate(task_description=(message or "").strip())
    except Exception:  # gaten er rådgivende — fejler den, starter runnet som før
        return True
    return bool(udfald.get("allowed", True))


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


def build_gut_counterfactual_surface() -> dict[str, object]:
    """Counterfactual decision delta: hvor ofte flyttede den lærte bias gatens afgørelse?

    Læser den PERSISTENTE ledger (overlever genstart). Da bias'en i dag er positiv-only, er
    med-bias-pass en overmængde af uden-bias-pass, og deltaet = antallet af hændelser hvor
    erfaringen vendte en afvisning til en tilladelse. Det er dét tal der kan svare på om
    erfaringen ændrer en beslutning — ikke om den bare er blevet gemt.
    """
    try:
        from core.services import gate_verdict_ledger as ledger
        counts = ledger.summary()
    except Exception:  # ledgeren kan ikke læses → fladen melder "ingen data", kaster ikke
        return {"active": False, "events": 0, "summary": "ledger utilgængelig"}

    backstop = counts.get(_BACKSTOP_NERVE) or {}
    med = counts.get(_COUNTERFACTUAL_NERVE) or {}
    uden = counts.get(_COUNTERFACTUAL_NERVE_NO_BIAS) or {}
    total = int(med.get("total") or 0)
    if not total:
        return {"active": False, "events": 0,
                "summary": "ingen gut_gate-afgørelser talt op endnu"}

    pass_med = int(med.get("green") or 0)
    pass_uden = int(uden.get("green") or 0)
    delta = pass_med - pass_uden
    blokeret = total - pass_med
    return {
        "active": True,
        "events": total,
        "pass_med_bias": pass_med,
        "pass_uden_bias": pass_uden,
        "counterfactual_delta": delta,
        "delta_pct": round(100.0 * delta / total, 2),
        "blokeret": blokeret,
        "backstop_overkoersler": int(backstop.get("total") or 0),
        "summary": (
            f"bias flyttede afgørelsen i {delta} af {total} tilfælde "
            f"({round(100.0 * delta / total, 2)} %); {blokeret} stoppet, "
            f"{int(backstop.get('total') or 0)} sluppet igennem af bagkanten"
        ),
    }
