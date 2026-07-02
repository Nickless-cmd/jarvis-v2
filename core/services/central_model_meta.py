"""core/services/central_model_meta.py

Tråd 1 (Intelligent Central-spec §3): CENTRALEN KENDER SIT EGET HARDWARE.

Centralen observerer per-model-udfald (provider/model/latency/success/cost) fra de kilder der
ALLEREDE persisteres — `visible_runs` (provider/model/status/tider → latency+success) og cost-
ledgeren (`costs`: per-model tokens+pris). Den bygger en tidsserie "system"/"model_outcome:<prov>:
<model>" og — når to modeller har nok samples til ægte kontrast — en governed `model_meta`-hypotese
(*"model X er hurtigere/billigere/mere pålidelig end Y"*) der lever/dør gennem §8-dødsmekanismen.

OBSERVE-ONLY. Ændrer ALDRIG hvilken model der svarer Bjørn — det er eksplorations-armen (§3-blokker,
eget flag default OFF, ALDRIG på reasoning/deep-tier), som bygges separat bag én ventil (som Lag 4).

§8-nøgle-mapping (undgår frozen-core-ceremoni): latency_ms→duration_ms, win_rate→rate, cost→ratio —
disse ER i LEARNABLE_AGGREGATE_KEYS; rå navne ville fail-close.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_WINDOW = 300
_MIN_SAMPLES = 15            # hver model skal ses ≥ dette før den kan indgå i en kontrast
_LATENCY_MARGIN = 1.25       # X's latency skal være ≤ Y's / dette (25% hurtigere) for et forslag
_SUCCESS_MARGIN = 0.10       # eller X's success-rate ≥ Y's + dette
_SUCCESS_STATES = ("completed", "done")


def _parse(ts: Any) -> datetime | None:
    try:
        s = str(ts or "").replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _key(provider: str, model: str) -> str:
    return f"{str(provider or '?')}/{str(model or '?')}"


def aggregate_model_outcomes(*, window: int = _WINDOW) -> dict[str, dict[str, Any]]:
    """Aggregér per-model: samples, success-rate, gennemsnits-latency (fra visible_runs) + pris/1k
    tokens (fra costs). Self-safe — returnerer {} ved fejl."""
    out: dict[str, dict[str, Any]] = {}
    # --- latency + success fra visible_runs ---
    try:
        from core.runtime.db import recent_visible_runs
        for r in recent_visible_runs(limit=int(window)):
            k = _key(r.get("provider"), r.get("model"))
            d = out.setdefault(k, {"provider": r.get("provider"), "model": r.get("model"),
                                   "samples": 0, "success": 0, "lat_sum": 0.0, "lat_n": 0,
                                   "cost_usd": 0.0, "tokens": 0, "cost_rows": 0})
            d["samples"] += 1
            if str(r.get("status") or "") in _SUCCESS_STATES:
                d["success"] += 1
            st, fi = _parse(r.get("started_at")), _parse(r.get("finished_at"))
            if st and fi:
                ms = (fi - st).total_seconds() * 1000.0
                if 0 <= ms < 3_600_000:          # sanity: 0..1h
                    d["lat_sum"] += ms
                    d["lat_n"] += 1
    except Exception:
        pass
    # --- pris + tokens fra cost-ledgeren ---
    try:
        from core.costing.ledger import recent_costs
        for c in recent_costs(limit=int(window)):
            k = _key(c.get("provider"), c.get("model"))
            d = out.setdefault(k, {"provider": c.get("provider"), "model": c.get("model"),
                                   "samples": 0, "success": 0, "lat_sum": 0.0, "lat_n": 0,
                                   "cost_usd": 0.0, "tokens": 0, "cost_rows": 0})
            d["cost_usd"] += float(c.get("cost_usd") or 0.0)
            d["tokens"] += int(c.get("input_tokens") or 0) + int(c.get("output_tokens") or 0)
            d["cost_rows"] += 1
    except Exception:
        pass
    # --- afledte skalarer ---
    for d in out.values():
        d["success_rate"] = round(d["success"] / d["samples"], 4) if d["samples"] else 0.0
        d["latency_ms"] = round(d["lat_sum"] / d["lat_n"], 1) if d["lat_n"] else 0.0
        d["cost_per_1k"] = round(d["cost_usd"] / d["tokens"] * 1000.0, 6) if d["tokens"] else 0.0
    return out


def observe_model_outcomes(*, window: int = _WINDOW) -> int:
    """Skriv per-model-udfald til tidsserien "system"/"model_outcome:<prov>:<model>". Metadata-only
    (IKKE via broen). §8-mapping i meta. Self-safe. Returnerer antal observerede modeller."""
    agg = aggregate_model_outcomes(window=window)
    n = 0
    try:
        from core.services import central_timeseries as ts
        for k, d in agg.items():
            if not d.get("samples") and not d.get("cost_rows"):
                continue
            ts.record("system", f"model_outcome:{k}", value=float(d.get("latency_ms") or 0.0),
                      meta={"duration_ms": d.get("latency_ms"), "rate": d.get("success_rate"),
                            "ratio": d.get("cost_per_1k"), "samples": int(d.get("samples") or 0)})
            n += 1
    except Exception:
        pass
    return n


def detect_model_meta_candidates(*, window: int = _WINDOW, min_samples: int = _MIN_SAMPLES) -> list[dict[str, Any]]:
    """Find modeller med ægte kontrast (begge ≥ min_samples) hvor den ene DOMINERER den anden på
    latency eller success. Blokker (§3): visible-lane har typisk ÉN model → ofte tom liste (ærligt).
    Naturlig kontrast opstår fra historiske model-skift + provider-fallback + cheap-lane. Self-safe."""
    agg = aggregate_model_outcomes(window=window)
    ready = [d for d in agg.values() if int(d.get("samples") or 0) >= int(min_samples)]
    out: list[dict[str, Any]] = []
    for a in ready:
        for b in ready:
            if a is b:
                continue
            ka, kb = _key(a["provider"], a["model"]), _key(b["provider"], b["model"])
            if ka >= kb:                          # kun ét ordnet par (undgå dubletter A|B og B|A)
                continue
            # latency-dominans: A markant hurtigere end B
            if a["latency_ms"] > 0 and b["latency_ms"] > 0 and \
                    a["latency_ms"] * _LATENCY_MARGIN <= b["latency_ms"]:
                out.append({"metric": "latency", "winner": ka, "loser": kb,
                            "w_val": a["latency_ms"], "l_val": b["latency_ms"],
                            "w_n": a["samples"], "l_n": b["samples"]})
            elif b["latency_ms"] > 0 and a["latency_ms"] > 0 and \
                    b["latency_ms"] * _LATENCY_MARGIN <= a["latency_ms"]:
                out.append({"metric": "latency", "winner": kb, "loser": ka,
                            "w_val": b["latency_ms"], "l_val": a["latency_ms"],
                            "w_n": b["samples"], "l_n": a["samples"]})
            # success-dominans: A markant mere pålidelig end B
            elif a["success_rate"] >= b["success_rate"] + _SUCCESS_MARGIN:
                out.append({"metric": "success", "winner": ka, "loser": kb,
                            "w_val": a["success_rate"], "l_val": b["success_rate"],
                            "w_n": a["samples"], "l_n": b["samples"]})
            elif b["success_rate"] >= a["success_rate"] + _SUCCESS_MARGIN:
                out.append({"metric": "success", "winner": kb, "loser": ka,
                            "w_val": b["success_rate"], "l_val": a["success_rate"],
                            "w_n": b["samples"], "l_n": a["samples"]})
    return out


def _family(cand: dict[str, Any]) -> str:
    return f"{cand['metric']}:{cand['winner']}>{cand['loser']}"


def formulate_model_meta_hypothesis(cand: dict[str, Any]) -> dict[str, Any]:
    """Kontrast → falsificerbar model_meta-hypotese. Testbar = dominansen PERSISTERER i friske runs."""
    from core.services.central_hypothesis_generator import _DEFAULT_SAMPLE_SIZE, _DEFAULT_TTL_S, _INITIAL_CONFIDENCE
    metric, w, l = cand["metric"], cand["winner"], cand["loser"]
    unit = "ms latency" if metric == "latency" else "success-rate"
    return {
        "source": "model_meta",
        "statement": f"Model '{w}' er bedre end '{l}' på {metric} ({cand['w_val']} vs {cand['l_val']} {unit})",
        "prediction": f"Over friske runs bevarer '{w}' sin fordel på {metric} over '{l}'",
        "null_hypothesis": f"'{w}' og '{l}' er reelt ens på {metric} (fordelen var støj/udvalg)",
        "success_criterion": f">= {_DEFAULT_SAMPLE_SIZE} jordede måle-vinduer hvor dominansen holder",
        "sample_size": _DEFAULT_SAMPLE_SIZE,
        "ttl_seconds": _DEFAULT_TTL_S,
        "provenance": {"mechanism": "model_meta", "family": _family(cand),
                       "cursor_id": int(cand.get("w_n", 0))},
        "confidence": _INITIAL_CONFIDENCE,
    }


def test_model_meta_persistence(family: str) -> dict[str, Any] | None:
    """Sampler-sti (§8.4): holder model-dominansen stadig i friske data? family = "<metric>:<w>><l>".
    Ja → supports; kollapset (loser indhentede / winner væk) → falsifies. None ved for lidt data."""
    try:
        metric, _, rest = str(family).partition(":")
        w, _, l = rest.partition(">")
        if not (metric and w and l):
            return None
        agg = aggregate_model_outcomes()
        wa, la = agg.get(w), agg.get(l)
        if not wa or not la or int(wa.get("samples") or 0) < _MIN_SAMPLES \
                or int(la.get("samples") or 0) < _MIN_SAMPLES:
            return None                            # ingen frisk kontrast → ingen falsk resolution
        if metric == "latency":
            holds = wa["latency_ms"] > 0 and la["latency_ms"] > 0 and \
                wa["latency_ms"] * _LATENCY_MARGIN <= la["latency_ms"]
        else:
            holds = wa["success_rate"] >= la["success_rate"] + _SUCCESS_MARGIN
        return {"supports": bool(holds), "falsifies": not bool(holds),
                "cursor": int(wa.get("samples") or 0)}
    except Exception:
        return None


def run_model_meta_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: observér per-model-udfald + generér model_meta-hypoteser (governance-gated,
    dedup mod aktive). OBSERVE-ONLY — ændrer aldrig routing. Egress-fri observe. Self-safe."""
    observed = observe_model_outcomes()
    registered = 0
    try:
        from core.services import central_hypothesis_generator as gen
        gen.ensure_schema()
        existing = gen._active_provenance_families()
        for cand in detect_model_meta_candidates():
            hyp = formulate_model_meta_hypothesis(cand)
            if hyp["provenance"]["family"] in existing:
                continue
            if gen.register_governed_hypothesis(hyp).get("status") == "registered":
                registered += 1
    except Exception:
        pass
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "model_meta_reflection", value=float(observed),
                       meta={"models_observed": observed, "hypotheses_registered": registered})
    except Exception:
        pass
    return {"status": "ok", "models_observed": observed, "hypotheses_registered": registered}


def register_model_meta_producer() -> None:
    """Registrér Tråd 1 som cadence-producer (~hvert 30 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_model_meta",
        cooldown_minutes=30,
        visible_grace_minutes=0,
        run_fn=run_model_meta_tick,
        priority=6,
    ))


def build_model_meta_surface() -> dict[str, object]:
    """Mission Control surface — read-only: hvad Centralen ved om sine egne modeller."""
    agg = aggregate_model_outcomes()
    models = sorted(
        ({"model": k, "samples": d["samples"], "success_rate": d["success_rate"],
          "latency_ms": d["latency_ms"], "cost_per_1k": d["cost_per_1k"]}
         for k, d in agg.items() if d.get("samples") or d.get("cost_rows")),
        key=lambda z: z["samples"], reverse=True)
    return {"active": True, "models_known": len(models), "models": models[:12],
            "contrasts": detect_model_meta_candidates()[:6]}
