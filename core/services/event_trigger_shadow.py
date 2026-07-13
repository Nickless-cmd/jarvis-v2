"""core/services/event_trigger_shadow.py

C5 — EVENT-TRIGGER SHADOW-METER (observe-only, ZERO adfærdsændring).

Dette er den event-drevne dispatch-trigger (C2 `signal_delta_trigger`) sat på
hjerteslaget i SHADOW: hvert tick samler den de FLYDENDE signaler (genbrugt fra
de eksisterende signal-surfaces — ikke ny instrumentering), spørger den rene,
IKKE-LLM delta-trigger "ville en REEL ændring udløse et dispatch NU?", og
KONSULTERER dispatch-værnene (budget/breaker/visible-lease) — men den FYRER
ALDRIG en LLM og INDKALDER ALDRIG et råd. Den skriver kun telemetri.

Formålet er en 24t kalibrerings-vindue: vi opsamler hvad den event-drevne
trigger VILLE dispatche (og hvad værnene VILLE gøre) FØR vi nogensinde flipper
den til at handle — og UDEN at røre den gamle `autonomous_council_daemon`
(den pensioneres senere).

GOVERNANCE: samme flag som grund-dommeren, `central_convene_judge_mode`
(off|shadow|on). Så længe mode != "on" er dette rent observerende: NUL LLM,
NUL råd. Modulet importerer overhovedet ikke nogen LLM- eller council-sti.

Self-safe: en fejl i signal-kilden → sikker skip (registrerer intet, kaster
aldrig ind i hjerteslaget). Al telemetri er best-effort.

Telemetri-nerve: central_timeseries.record("agents", "event_trigger", ...).
"""
from __future__ import annotations

from typing import Any

# Lane hvis budget/breaker-værn beskytter den autonome dispatch. Vi observerer
# hvad de VILLE sige for netop denne lane (rører ikke deres tilstand — kun læse).
_LANE = "autonomous_council"

# Nominelt cost-estimat pr. dispatch (kun til budget_allows-forespørgslen; intet
# forbruges — record_spend kaldes ALDRIG i shadow).
_EST_COST_USD = 0.02

# Registrér dette shadow-vindue i det durable review-register ved import (idempotent,
# self-safe) — så en modent 24t-vindue surfacer sig selv og hverken Bjørn eller
# Claude glemmer at kalibrere θ. Rører intet hvis allerede registreret.
try:
    from core.services import shadow_experiment_registry as _shadow_reg
    _shadow_reg.register_experiment(
        "event_trigger",
        review_after_hours=24,
        note="C5 delta-trigger shadow — kalibrér θ fra 24t spor",
    )
except Exception:
    pass


def _mode() -> str:
    """Governance-mode (off|shadow|on) fra grund-dommerens flag. Self-safe."""
    try:
        from core.services.central_convene_judge import current_mode
        return current_mode()
    except Exception:
        return "off"


def _gather_signals() -> dict[str, float]:
    """Saml de flydende signaler som en dict[str,float] (0..1) — GENBRUG af de
    eksisterende signal-surfaces via grund-dommerens `_read_flowing_values`
    (ingen ny instrumentering). Kan kaste (signal-kilde-fejl); kalderen fanger
    og laver en sikker skip."""
    from core.services.central_convene_judge import _read_flowing_values

    flowing = _read_flowing_values(None)
    movement = flowing.get("movement") if isinstance(flowing, dict) else None
    if not isinstance(movement, dict):
        return {}
    out: dict[str, float] = {}
    for name, val in movement.items():
        try:
            out[str(name)] = float(val)
        except (TypeError, ValueError):
            continue
    return out


def _consult_guards() -> dict[str, Any]:
    """Læs (read-only) hvad dispatch-værnene VILLE sige lige nu. Self-safe."""
    budget_ok = False
    breaker_tripped = False
    vis = False
    try:
        from core.services import dispatch_guards
        budget_ok = bool(dispatch_guards.budget_allows(_LANE, _EST_COST_USD))
        breaker_tripped = bool(dispatch_guards.is_tripped(_LANE))
    except Exception:
        pass
    try:
        from core.services import autonomous_lease
        vis = bool(autonomous_lease.visible_active())
    except Exception:
        pass
    return {"budget_ok": budget_ok, "breaker_tripped": breaker_tripped, "visible_active": vis}


def _record(value: float, meta: dict[str, Any]) -> None:
    try:
        from core.services import central_timeseries as ts
        ts.record("agents", "event_trigger", value=float(value), meta=meta)
    except Exception:
        pass


def tick_event_trigger_shadow(signals: dict[str, float] | None = None) -> dict[str, Any]:
    """Ét shadow-tick: saml signaler → evaluér den rene delta-trigger → konsultér
    værnene → registrér telemetri. FYRER ALDRIG en LLM, INDKALDER ALDRIG et råd
    (mode != "on" ⇒ ren observation; dette modul kalder aldrig en LLM/council-sti
    overhovedet).

    signals: injicér signaler direkte (test-sti); ellers læses de flydende
    surfaces. En fejl i signal-kilden → sikker skip (registrerer intet).

    Returnerer en lille status-dict (til daemon-record), aldrig en exception."""
    mode = _mode()

    # --- Saml signaler. En signal-kilde-fejl → sikker skip, registrér INTET. ---
    if signals is not None:
        sig: dict[str, float] = {}
        try:
            for k, v in dict(signals).items():
                sig[str(k)] = float(v)
        except Exception:
            return {"recorded": False, "skipped": "signal_source_error", "would_dispatch": False}
    else:
        try:
            sig = _gather_signals()
        except Exception:
            return {"recorded": False, "skipped": "signal_source_error", "would_dispatch": False}

    # --- Evaluér den rene, IKKE-LLM delta-trigger. -----------------------------
    try:
        from core.services import signal_delta_trigger
        decision = signal_delta_trigger.evaluate(sig)
    except Exception:
        decision = None

    would_dispatch = decision is not None
    crossed = list((decision or {}).get("crossed") or [])
    movements = dict((decision or {}).get("movements") or {})
    reason = str((decision or {}).get("reason") or ("no_real_movement" if not would_dispatch else ""))

    # Værn-verdikter (read-only) — så 24t-data viser hvad de VILLE have gjort.
    guards = _consult_guards()

    # value = største bevægelse (abs) i denne beslutning, ellers 0.
    try:
        max_movement = max((abs(float(v)) for v in movements.values()), default=0.0)
    except Exception:
        max_movement = 0.0

    meta: dict[str, Any] = {
        "mode": "shadow" if mode != "on" else "on",
        "would_dispatch": bool(would_dispatch),
        "crossed": crossed,
        "movements": {str(k): round(float(v), 3) for k, v in movements.items()},
        "signals": {str(k): round(float(v), 3) for k, v in sig.items()},
        "reason": reason[:120],
        "lane": _LANE,
        "budget_ok": guards["budget_ok"],
        "breaker_tripped": guards["breaker_tripped"],
        "visible_active": guards["visible_active"],
    }
    _record(max_movement, meta)

    return {
        "recorded": True,
        "would_dispatch": bool(would_dispatch),
        "crossed": crossed,
        "mode": meta["mode"],
    }
