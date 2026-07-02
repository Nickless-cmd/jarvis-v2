"""core/services/central_adaptation.py

Lag 4 v1 (LivingNeuron v3 §11 Fase 3): c→d-LUKNINGEN — første gang Centralen justerer en tilbøjelighed.

Loop: sanse (Lag 1-2) → hypotese (Lag 3) → test mod virkelighed (sampler) → RESOLVE → **JUSTÉR**.
Konkret adaptation v1 (bevidst smal + reversibel): et gut-proceed-BIAS drevet af Centralens EGEN
track-record — jo mere præcist den har forudsagt sig selv (resolved supported vs. contradicted),
jo mere tiltro tjener Jarvis' mavefornemmelse. Selv-model-tillid som tilbøjelighed.

SIKKERHED (§8 + §12.3 + shadow-spec 2026-07-02):
  * SHADOW-FIRST: som standard beregnes + logges kun en diff — INTET ændres. Live kræver runtime-flag
    `central_lag4_live_enabled=True` (Bjørns ene switch, default OFF) OG ikke-paused.
  * DRIFT-BUDGET: hvert forslag gates gennem gate_self_mutation mod ANKRET baseline (bias=0 = identitet);
    overskredet → rollback + PAUSE (kill-switch) + varsl Bjørn.
  * REVERSIBELT: rollback-EKSEKVERING gendanner forrige bias (det manglende primitiv fra shadow-spec).
  * BOUNDET: bias clampet til ±0.25; drift-budget 0.3.
  * FROSSEN KERNE urørt: rører KUN gut-bias — aldrig SOUL/identitet/sikkerhedsgates/værn-konstanter.
Alt self-safe, kaster ALDRIG.
"""
from __future__ import annotations

from typing import Any

from core.services import central_hypothesis_governance as gov

_BIAS_KEY = "central_gut_proceed_bias"        # den justerede tilbøjelighed (persist)
_PREV_KEY = "central_gut_proceed_bias_prev"   # snapshot til rollback
_LIVE_FLAG = "central_lag4_live_enabled"      # Bjørns ene switch (default False)
_PAUSE_KEY = "central_lag4_paused"            # kill-switch (sat af drift-rollback)

_BIAS_CLAMP = 0.25
_BIAS_BUDGET = 0.30
_MIN_RESOLVED = 5
_ANCHOR_VERSION = "gut-bias-v1"


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


def get_gut_bias() -> float:
    try:
        return max(-_BIAS_CLAMP, min(_BIAS_CLAMP, float(_kv_get(_BIAS_KEY, 0.0))))
    except Exception:
        return 0.0


def is_live_enabled() -> bool:
    return bool(_kv_get(_LIVE_FLAG, False)) and not bool(_kv_get(_PAUSE_KEY, False))


def is_paused() -> bool:
    return bool(_kv_get(_PAUSE_KEY, False))


def _ensure_anchor() -> None:
    """Ankr identitets-baseline: bias=0 ER identiteten (ingen tilbøjeligheds-forvrængning). In-memory
    pr. proces (0.0 er altid det korrekte nulpunkt → drift måles altid fra 'ingen bias')."""
    try:
        if gov.get_anchored_baseline() is None:
            gov.anchor_identity_baseline({_BIAS_KEY: 0.0}, version=_ANCHOR_VERSION,
                                         approved_by="lag4-shadow")
    except Exception:
        pass


def resolved_track_record() -> dict[str, int]:
    """Centralens egen præcision: hvor mange hypoteser om sig selv har holdt vs. fejlet."""
    out = {"supported": 0, "contradicted": 0}
    try:
        from core.runtime.db import connect
        with connect() as c:
            for r in c.execute("SELECT outcome, COUNT(*) n FROM central_hypotheses "
                               "WHERE status='resolved' GROUP BY outcome"):
                o = str(r["outcome"] or "")
                if o in out:
                    out[o] = int(r["n"])
    except Exception:
        pass
    return out


def compute_proposed_bias() -> dict[str, Any]:
    """Foreslå gut-bias fra track-record. accuracy=supported/(supported+contradicted). Højere præcision
    → mere proceed-tiltro; lavere → caution. Kræver ≥ _MIN_RESOLVED resolved (ellers ingen ændring)."""
    tr = resolved_track_record()
    resolved = tr["supported"] + tr["contradicted"]
    if resolved < _MIN_RESOLVED:
        return {"proposed": 0.0, "accuracy": None, "resolved": resolved, "enough": False}
    accuracy = tr["supported"] / resolved
    proposed = max(-_BIAS_CLAMP, min(_BIAS_CLAMP, round((accuracy - 0.5) * 0.5, 4)))
    return {"proposed": proposed, "accuracy": round(accuracy, 3), "resolved": resolved, "enough": True}


def rollback(reason: str = "") -> None:
    """Rollback-EKSEKVERING (shadow-specens manglende primitiv): gendan forrige bias + PAUSE Lag 4
    (kill-switch) + varsl Bjørn. Identitet beskyttet."""
    prev = float(_kv_get(_PREV_KEY, 0.0) or 0.0)
    _kv_set(_BIAS_KEY, prev)
    _kv_set(_PAUSE_KEY, True)
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "lag4_rollback", "kind": "flag",
                           "restored_bias": prev, "reason": str(reason)[:120], "paused": True})
    except Exception:
        pass


def run_adaptation_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: beregn foreslået bias → gate gennem drift-budget → SHADOW-log diff; anvend
    KUN hvis live-flag ON + ikke-paused + gate ok. Rollback+pause hvis drift overskrides. Self-safe."""
    _ensure_anchor()
    cur = get_gut_bias()
    prop = compute_proposed_bias()
    proposed = float(prop["proposed"])
    # Drift-budget-gate: hvad ville bias BLIVE, målt mod ankret baseline (bias=0)?
    verdict = gov.gate_self_mutation({_BIAS_KEY: proposed}, budgets={_BIAS_KEY: _BIAS_BUDGET})
    live = is_live_enabled()
    applied = False
    if verdict.action == "rollback":
        rollback(reason=f"drift {verdict.drift} > budget {_BIAS_BUDGET}")
    elif prop["enough"] and live and abs(proposed - cur) > 1e-6:
        _kv_set(_PREV_KEY, cur)          # snapshot FØR ændring (muliggør rollback)
        _kv_set(_BIAS_KEY, proposed)
        applied = True
    # SHADOW-diff (altid) — egress-frit, kun skalarer.
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "lag4_adaptation", value=float(proposed),
                       meta={"current": cur, "proposed": proposed, "accuracy": prop.get("accuracy"),
                             "resolved": prop["resolved"], "live": live, "applied": applied,
                             "gate": verdict.action})
    except Exception:
        pass
    return {"status": "ok", "mode": "live" if live else "shadow", "current_bias": cur,
            "proposed_bias": proposed, "applied": applied, "gate": verdict.action,
            "accuracy": prop.get("accuracy"), "resolved": prop["resolved"]}


def register_adaptation_producer() -> None:
    """Registrér Lag 4-adaptationen som cadence-producer (~hvert 60 min). SHADOW medmindre live-flag ON."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_adaptation",
        cooldown_minutes=60,
        visible_grace_minutes=0,
        run_fn=run_adaptation_tick,
        priority=8,
    ))


def build_central_adaptation_surface() -> dict[str, object]:
    """Mission Control surface — read-only: nuværende bias, foreslået, live/shadow/paused."""
    return {"active": True, "gut_proceed_bias": get_gut_bias(), "live_enabled": is_live_enabled(),
            "paused": is_paused(), **compute_proposed_bias()}
