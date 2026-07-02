"""core/services/central_hypothesis_sampler.py

Lag 3 loop-lukning (OBSERVE-siden): TEST aktive hypoteser mod virkeligheden → grounded samples.

Hullet der lukkes: generatoren DANNER hypoteser, men intet TESTEDE dem → de sad på 0/sample_size og
resolvede aldrig. Denne sampler tester hver aktiv causal-hypotese (X→Y) mod event-strømmen med en
ÆGTE baseline-sammenligning (betinget rate vs. baseline-rate) — IKKE ren co-occurrence (undgår at
gen-udlede den graf der fødte hypotesen). Ét grounded sample pr. tick pr. hypotese → resolver via
§8-dødsmekanismen (record_governed_sample → evaluate).

Grounding: events ER virkelighedens optegnelse → source="world_consequence", ground_ref = event-id
(verificerbart anker, ikke en selvrapporteret label). OBSERVE-ONLY: tester + registrerer, HANDLER aldrig.

Divergens-/stance-hypoteser auto-testes IKKE i v1 (kræver udfald-linkning) — de forbliver aktive.
Alt read-only, self-safe, kaster ALDRIG.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

_WINDOW = 3000            # events der scannes
_FOLLOW_S = 60            # Y skal følge X inden for dette vindue for at "tælle"
_MIN_EVENTS = 30          # for lidt data → spring over (ingen falsk resolution)
_MIN_X = 5                # for få X-events → ikke nok til en betinget rate
_LIFT = 1.5               # betinget rate skal overstige baseline × dette for "supports"


def _parse(ts: Any) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return t
    except Exception:
        return None


def test_causal_hypothesis(x_fam: str, y_fam: str, *, window: int = _WINDOW,
                           follow_s: int = _FOLLOW_S) -> dict[str, Any] | None:
    """Betinget rate P(Y følger X inden for follow_s) vs. baseline P(Y overhovedet). Self-safe.
    Returnerer None ved for lidt data (ingen falsk resolution)."""
    try:
        from core.eventbus.bus import event_bus
        rows = event_bus.recent(limit=int(window))
    except Exception:
        return None
    evs = []
    for e in rows:
        fam = str(e.get("kind") or "").split(".", 1)[0]
        evs.append((int(e.get("id") or 0), fam, _parse(e.get("created_at"))))
    evs.sort(key=lambda z: z[0])
    n = len(evs)
    if n < _MIN_EVENTS:
        return None
    y_total = sum(1 for _, f, _ in evs if f == y_fam)
    baseline = y_total / n if n else 0.0
    x_events = [(i, t) for i, f, t in evs if f == x_fam]
    if len(x_events) < _MIN_X:
        return None
    y_ts = [t for _, f, t in evs if f == y_fam and t is not None]
    hits = 0
    for _, xt in x_events:
        if xt and any(0 < (yt - xt).total_seconds() <= follow_s for yt in y_ts):
            hits += 1
    conditional = hits / len(x_events)
    supports = (conditional > baseline * _LIFT) and (conditional > 0.05)
    # falsificerer HVIS betinget rate IKKE overstiger baseline (null-hypotesen holder)
    falsifies = conditional <= baseline
    return {"conditional": round(conditional, 4), "baseline": round(baseline, 4),
            "supports": supports, "falsifies": falsifies, "cursor": evs[-1][0],
            "x_events": len(x_events)}


def test_divergence_persistence(family: str) -> dict[str, Any] | None:
    """causal_divergence (§8.4): 'X → BÅDE godt og dårligt udfald'. Test PERSISTENS mod friske data —
    er divergensen der stadig (X fører stadig til begge sider)? Ja → supports; nej (kollapset til én
    side) → falsifies. family = 'parent:good|bad'. Self-safe."""
    try:
        parent, _, rest = str(family).partition(":")
        good, _, bad = rest.partition("|")
        if not (parent and good and bad):
            return None
        from core.services import central_hypothesis_generator as gen
        cands = gen.detect_outcome_divergence_candidates()
        match = next((c for c in cands if c["parent_family"] == parent
                      and c["good"] == good and c["bad"] == bad), None)
        cursor = match["cursor"] if match else 0
        return {"supports": bool(match), "falsifies": not bool(match), "cursor": cursor}
    except Exception:
        return None


def test_stance_persistence(tension_key: str) -> dict[str, Any] | None:
    """stance_divergence (§8.4): 'to organer er gentagne gange uenige'. Test PERSISTENS — gentager
    tension'en sig stadig? Ja → supports; nej (organerne enige nu) → falsifies. Self-safe."""
    try:
        from core.services.central_stance import recurring_tensions
        rec = recurring_tensions(min_count=1)   # findes den overhovedet stadig i vinduet?
        still = any(r.get("key") == str(tension_key) for r in rec)
        cnt = next((r.get("count", 0) for r in rec if r.get("key") == str(tension_key)), 0)
        return {"supports": bool(still), "falsifies": not bool(still), "cursor": int(cnt)}
    except Exception:
        return None


def run_hypothesis_sampler_tick(*, trigger: str = "cadence",
                                last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: test hver aktiv CAUSAL-hypotese mod event-strømmen, registrér ét grounded
    sample. OBSERVE-ONLY. Self-safe."""
    from core.services import central_hypothesis_generator as gen
    gen.ensure_schema()
    tested, supported, contradicted, skipped = 0, 0, 0, 0
    try:
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute(
                "SELECT hyp_id, provenance_json FROM central_hypotheses "
                "WHERE status='active'").fetchall()
        active = [(str(r["hyp_id"]), json.loads(r["provenance_json"] or "{}")) for r in rows]
    except Exception:
        active = []
    for hyp_id, prov in active:
        mech = prov.get("mechanism")
        fam = str(prov.get("family") or "")
        # §8.4: test causal-KORRELATION, causal-DIVERGENS OG stance-DIVERGENS (før: kun causal_edges).
        if mech == "causal_edges" and "->" in fam:
            x_fam, y_fam = fam.split("->", 1)
            res = test_causal_hypothesis(x_fam, y_fam)
        elif mech == "prediction_error" and "->" in fam:
            # Tråd 4: overraskelsen holder KUN hvis overgangen faktisk er prædiktiv over baseline —
            # samme conditional-rate-test. Ellers falsificeres den (det var støj). §8.4.
            x_fam, y_fam = fam.split("->", 1)
            res = test_causal_hypothesis(x_fam, y_fam)
        elif mech == "causal_divergence" and ":" in fam:
            res = test_divergence_persistence(fam)
        elif mech == "stance_divergence":
            res = test_stance_persistence(fam)
        else:
            res = None
        if res is None:
            skipped += 1
            continue
        tested += 1
        # triggered_by='world': frisk verdens-observation, IKKE selv-udløst (circular-korrekt, §8.5).
        gen.record_governed_sample(
            hyp_id, supports=bool(res["supports"]), falsifies=bool(res["falsifies"]),
            source="world_consequence", ground_ref=str(res["cursor"]),
            triggered_by="world")
        if res["supports"]:
            supported += 1
        elif res["falsifies"]:
            contradicted += 1
    # egress-fri observe (kun tællere)
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "hypothesis_sampling", value=float(tested),
                       meta={"tested": tested, "supported": supported,
                             "contradicted": contradicted, "skipped": skipped})
    except Exception:
        pass
    return {"status": "ok", "tested": tested, "supported": supported,
            "contradicted": contradicted, "skipped": skipped}


def register_hypothesis_sampler_producer() -> None:
    """Registrér samleren som cadence-producer (~hvert 30 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_hypothesis_sampler",
        cooldown_minutes=30,
        visible_grace_minutes=0,
        run_fn=run_hypothesis_sampler_tick,
        priority=7,
    ))
