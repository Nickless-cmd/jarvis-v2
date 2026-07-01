"""core/services/central_shadow.py

M1 — det reaktive/prædiktive lag i SHADOW (Bjørn 1. jul: "hvis vi er klar til M1 er det ok,
bare vi begrænser aktiv ændring i starten til vi ved hvordan Centralen opererer").

Dette er første skridt fra "Centralen ser + lærer" mod "Centralen reagerer". Men REAKTIONEN
er ren SKYGGE: Centralen beregner hvad den VILLE gøre og gør det SYNLIGT — så vi kan
validere dens dømmekraft mod virkeligheden over tid, FØR nogen anvendelse tændes.

⛔ HÅRD INVARIANT (hardkodet, ikke config):
  * ``ACTIVE_APPLY = False``. Der findes INGEN kode-sti der anvender en justering/heling/
    mutation i denne fil. Shadow LOGGER kun. At tænde anvendelse er en bevidst fremtidig
    beslutning der kræver egen spec + fejl-lukket gate + menneske-opt-in (§22.4/§24.3).
  * Shadow læser reviewbare forslag (central_learning.propose_adjustments — findes allerede)
    + laver tidlig-varsel-prædiktion fra tidsserie-trends. Begge → trace (owner-HUD), aldrig handling.

To signaler pr. tick:
  1. SHADOW-REAKTIONER — hvad Centralen VILLE justere (fra lærings-forslagene).
  2. PRÆDIKTIONER — nerver hvis trend forværres MOD en tærskel, FØR de bryder (early-warning).
"""
from __future__ import annotations

from typing import Any

from core.services import central_timeseries

# ⛔ HÅRD: ingen anvendelse. Ingen kode her læser eller respekterer en True-værdi — konstanten
# dokumenterer intentionen og er et fremtidigt gate-punkt, ikke en switch der gør noget i dag.
ACTIVE_APPLY = False

# Value-serier at prædiktere på: (cluster, nerve, higher_is_worse, tærskel-den-nærmer-sig).
_PREDICT_SERIES = [
    ("system", "central_meta", True, 250.0),   # p95 decide-latency → mod _LATENCY_DRIFT_MS
    ("tools", "outcome", True, 0.35),           # tool-fejlrate → mod _TOOL_ERROR_RATE
]
_PREDICT_MIN_SAMPLES = 6


def _record_shadow(nerve: str, payload: dict[str, Any]) -> None:
    """Skriv en shadow-observation til trace (owner-HUD) + tidsserie. Self-safe.
    Bruger central().observe (operationel meta, ikke privat) — men ÆNDRER intet."""
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": nerve, "kind": "observe",
                           "shadow": True, **payload})
    except Exception:
        pass


def shadow_reactions() -> list[dict[str, Any]]:
    """Hvad Centralen VILLE gøre (fra reviewbare forslag) — logget som skygge, aldrig gjort."""
    out: list[dict[str, Any]] = []
    try:
        from core.services.central_learning import propose_adjustments
        for p in propose_adjustments()[:10]:
            out.append({"kind": p.get("kind"), "target": p.get("target")})
            _record_shadow("shadow_reaction", {
                "would_do": str(p.get("action") or "")[:300],
                "reaction_kind": p.get("kind"), "target": p.get("target"),
                "applied": False,  # ALTID — ACTIVE_APPLY er False
            })
    except Exception:
        pass
    return out


def _trend_worsening(cluster: str, nerve: str, higher_is_worse: bool) -> tuple[bool, float, float]:
    """(forværres, seneste_gns, tidligere_gns) fra en value-serie. Self-safe."""
    try:
        recent = central_timeseries.recent(cluster, nerve, limit=_PREDICT_MIN_SAMPLES)
        vals = [s.value for s in recent if s.value is not None]
        if len(vals) < _PREDICT_MIN_SAMPLES:
            return False, 0.0, 0.0
        half = len(vals) // 2
        older = sum(vals[:half]) / half
        newer = sum(vals[half:]) / (len(vals) - half)
        worse = (newer > older) if higher_is_worse else (newer < older)
        # kræv en mærkbar bevægelse (≥15% relativ) for at kalde det en trend
        moved = abs(newer - older) >= max(abs(older) * 0.15, 1e-9)
        return (worse and moved), round(newer, 3), round(older, 3)
    except Exception:
        return False, 0.0, 0.0


def predict_trends() -> list[dict[str, Any]]:
    """Tidlig-varsel: nerver hvis trend forværres MOD tærsklen, før de bryder. Skygge."""
    out: list[dict[str, Any]] = []
    for cluster, nerve, higher_is_worse, threshold in _PREDICT_SERIES:
        worse, newer, older = _trend_worsening(cluster, nerve, higher_is_worse)
        if not worse:
            continue
        # Er den på vej mod tærsklen (mellem baseline og breach)?
        approaching = (newer >= threshold * 0.6) if higher_is_worse else (newer <= threshold * 1.4)
        if not approaching:
            continue
        out.append({"target": f"{cluster}/{nerve}", "newer": newer, "older": older})
        _record_shadow("shadow_prediction", {
            "target": f"{cluster}/{nerve}", "trend_from": older, "trend_to": newer,
            "threshold": threshold,
            "warning": f"{cluster}/{nerve} trender mod tærskel ({older}→{newer}, grænse {threshold})",
        })
    return out


def run_shadow_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: beregn skygge-reaktioner + prædiktioner. ANVENDER ALDRIG. Self-safe."""
    reactions = shadow_reactions()
    predictions = predict_trends()
    # Synligt bevis på at shadow-laget lever OG at anvendelse er slået fra.
    _record_shadow("shadow", {"reactions": len(reactions), "predictions": len(predictions),
                              "active_apply": ACTIVE_APPLY})
    return {"status": "ok", "reactions": len(reactions),
            "predictions": len(predictions), "active_apply": ACTIVE_APPLY}


def register_shadow_producer() -> None:
    """Registrér skygge-laget som cadence-producer (~hvert 5 min). Observe-only, anvender aldrig."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_shadow",
        cooldown_minutes=5,
        visible_grace_minutes=0,
        run_fn=run_shadow_tick,
        priority=6,
    ))
