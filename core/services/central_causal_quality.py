"""core/services/central_causal_quality.py

Fase 1d (LivingNeuron v3 §4/§10): mål causal-grafens TIER-FORDELING + PRECISION — ikke bare volumen.

Rådets korrektion: "36 edges/tick" er ikke et intelligens-mål. causal_inference_daemon's Tier 3
(conf=0.4) = ren temporal co-occurrence (samme session ≤30s), IKKE kausalitet. En ukendt andel af
grafen er Tier-3-støj. Broen fra signal→hypotese (Lag 3) går gennem denne graf — hvis den domineres
af Tier-3, arver Lag 3 confounded hypoteser. Derfor MÅLES kvaliteten før Lag 3 bygges.

`source`-kolonnen i causal_edges koder tier entydigt:
  explicit          → instrumenteret (højeste tillid)
  inferred-kind     → Tier 1 (conf 0.9, whitelisted parent→child-regel)
  inferred-id       → Tier 2 (conf 0.8, delt tool_call_id/run_id/decision_id)
  inferred-temporal → Tier 3 (conf 0.4, kun temporal samtidighed = mistænkt støj)

PRECISION-PROXY (reproducerbar, uden manuel audit): en Tier-3-kant er "korroboreret" hvis dens
(parent_kind → child_kind)-par ALSO optræder som en Tier-1-regel eller som en faktisk Tier-1/2/
explicit-kant andetsteds i grafen. Korroborerede Tier-3-kanter er sandsynligvis ægte (bare matchet
temporalt her); ukorroborerede er sandsynligvis co-occurrence-støj. tier3_precision = korr / sample.

Alt read-only, self-safe, kaster ALDRIG.
"""
from __future__ import annotations

from typing import Any

# Tier-mærkning fra source-kolonnen.
_TIER_BY_SOURCE = {
    "explicit": "explicit",
    "inferred-kind": "tier1",
    "inferred-id": "tier2",
    "inferred-temporal": "tier3",
}
# Meningsfuldt kausalt signal (ikke ren co-occurrence).
_MEANINGFUL = ("explicit", "inferred-kind", "inferred-id")


def measure_edge_tiers() -> dict[str, Any]:
    """Tier-fordeling af HELE den akkumulerede graf (group by source). Self-safe."""
    out: dict[str, Any] = {"total": 0, "explicit": 0, "tier1": 0, "tier2": 0, "tier3": 0}
    try:
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute(
                "SELECT source, COUNT(*) AS n FROM causal_edges GROUP BY source"
            ).fetchall()
    except Exception:
        return {**out, "tier3_ratio": None, "meaningful_ratio": None}
    meaningful = 0
    for r in rows:
        src = str(r["source"] or "")
        n = int(r["n"] or 0)
        out["total"] += n
        tier = _TIER_BY_SOURCE.get(src)
        if tier:
            out[tier] = out.get(tier, 0) + n
        if src in _MEANINGFUL:
            meaningful += n
    tot = out["total"]
    out["tier3_ratio"] = round(out["tier3"] / tot, 4) if tot else None
    out["meaningful_ratio"] = round(meaningful / tot, 4) if tot else None
    return out


def _kind_rule_pairs() -> set[tuple[str, str]]:
    """(parent_kind, child_kind)-par som Tier-1-reglerne ville matche."""
    try:
        from core.services.causal_inference_daemon import _KIND_RULES
        return {(p, c) for p, children in _KIND_RULES.items() for c in children}
    except Exception:
        return set()


def estimate_tier3_precision(*, sample_limit: int = 100) -> dict[str, Any]:
    """Reproducerbar precision-proxy for Tier-3-kanter via korroboration. Self-safe."""
    out: dict[str, Any] = {"sampled": 0, "corroborated": 0, "tier3_precision": None}
    try:
        from core.runtime.db import connect
        with connect() as c:
            # Korroborerende par: kind-par der findes som Tier-1/2/explicit-kant.
            corr_rows = c.execute(
                "SELECT DISTINCT pe.kind AS pk, che.kind AS ck "
                "FROM causal_edges ce "
                "JOIN events pe ON pe.id = ce.parent_event_id "
                "JOIN events che ON che.id = ce.child_event_id "
                "WHERE ce.source IN ('inferred-kind','inferred-id','explicit')"
            ).fetchall()
            corroborating = {(str(r["pk"]), str(r["ck"])) for r in corr_rows}
            corroborating |= _kind_rule_pairs()
            # Sampl seneste Tier-3-kanter + deres kinds.
            t3 = c.execute(
                "SELECT pe.kind AS pk, che.kind AS ck "
                "FROM causal_edges ce "
                "JOIN events pe ON pe.id = ce.parent_event_id "
                "JOIN events che ON che.id = ce.child_event_id "
                "WHERE ce.source = 'inferred-temporal' "
                "ORDER BY ce.id DESC LIMIT ?",
                (max(int(sample_limit), 1),),
            ).fetchall()
    except Exception:
        return out
    sampled = len(t3)
    corroborated = sum(1 for r in t3 if (str(r["pk"]), str(r["ck"])) in corroborating)
    out["sampled"] = sampled
    out["corroborated"] = corroborated
    out["tier3_precision"] = round(corroborated / sampled, 4) if sampled else None
    return out


def measure() -> dict[str, Any]:
    """Fuldt kvalitets-billede: tier-fordeling + Tier-3-precision. Self-safe."""
    tiers = measure_edge_tiers()
    prec = estimate_tier3_precision()
    return {**tiers, **prec}


def record_causal_quality() -> dict[str, Any]:
    """Mål + skriv nøgletal til tidsserien (cluster=system) så kvaliteten kan plottes over tid."""
    m = measure()
    try:
        from core.services import central_timeseries as ts
        ts.record("system", "causal_edges_total", value=float(m.get("total") or 0))
        for tier in ("tier1", "tier2", "tier3", "explicit"):
            ts.record("system", f"causal_{tier}", value=float(m.get(tier) or 0))
        if m.get("tier3_ratio") is not None:
            ts.record("system", "causal_tier3_ratio", value=float(m["tier3_ratio"]))
        if m.get("meaningful_ratio") is not None:
            ts.record("system", "causal_meaningful_ratio", value=float(m["meaningful_ratio"]))
        if m.get("tier3_precision") is not None:
            ts.record("system", "causal_tier3_precision", value=float(m["tier3_precision"]),
                      meta={"sampled": m.get("sampled")})
    except Exception:
        pass
    return m


def run_causal_quality_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: mål + registrér causal-kvalitet (~hvert 30 min). Self-safe."""
    m = record_causal_quality()
    return {"status": "ok", "total": m.get("total"), "tier3_ratio": m.get("tier3_ratio"),
            "meaningful_ratio": m.get("meaningful_ratio"), "tier3_precision": m.get("tier3_precision")}


def register_causal_quality_producer() -> None:
    """Registrér causal-kvalitets-målingen som cadence-producer (~hvert 30 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_causal_quality",
        cooldown_minutes=30,
        visible_grace_minutes=0,
        run_fn=run_causal_quality_tick,
        priority=6,
    ))


def build_central_causal_quality_surface() -> dict[str, object]:
    """Mission Control surface — read-only causal-kvalitets-projektion (tier + precision)."""
    return {"active": True, **measure()}
