"""Tests for core/services/central_hypothesis_generator.py — Lag 3 governed generator (observe-only)."""
from __future__ import annotations

import pytest

from core.services import central_hypothesis_generator as gen


def _seed_edges(isolated_runtime, pairs):
    """pairs: list of (parent_kind, child_kind, count, source)."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    eid = 1
    with connect() as c:
        _ensure_causal_edges_table(c)
        gen.ensure_schema()
        for pk, ck, count, source in pairs:
            for _ in range(count):
                p, ch = eid, eid + 1
                eid += 2
                c.execute("INSERT INTO events (id, kind, payload_json, created_at) VALUES (?,?,?,?)",
                          (p, pk, "{}", "2026-07-02T00:00:00Z"))
                c.execute("INSERT INTO events (id, kind, payload_json, created_at) VALUES (?,?,?,?)",
                          (ch, ck, "{}", "2026-07-02T00:00:00Z"))
                c.execute("INSERT INTO causal_edges (child_event_id,parent_event_id,edge_kind,"
                          "confidence,source,created_at) VALUES (?,?,'caused',0.9,?,?)",
                          (ch, p, source, "2026-07-02T00:00:00Z"))
        c.commit()


def test_detect_recurring_meaningful_pairs(isolated_runtime):
    _seed_edges(isolated_runtime, [
        ("memory.recall_fail", "somatic.stress", 4, "inferred-kind"),   # meningsfuld, ≥3
        ("tool.invoked", "tool.completed", 2, "inferred-id"),           # under tærskel
        ("noise.a", "noise.b", 5, "inferred-temporal"),                 # Tier-3 = ignoreres
    ])
    cands = gen.detect_causal_convergence_candidates(min_recurrence=3)
    fams = {(c["parent_family"], c["child_family"]) for c in cands}
    assert ("memory", "somatic") in fams
    assert ("tool", "tool") not in fams        # samme familie filtreres + under tærskel
    assert ("noise", "noise") not in fams      # Tier-3 udelukket


def test_formulate_is_preregistered(isolated_runtime):
    cand = {"parent_family": "memory", "child_family": "somatic", "count": 4, "cursor": 42}
    hyp = gen.formulate_correlation_hypothesis(cand)
    from core.services import central_hypothesis_governance as gov
    ok, missing = gov.validate_preregistration(hyp)
    assert ok and missing == []
    assert hyp["provenance"]["family"] == "memory->somatic"


def test_register_rejects_unpreregistered(isolated_runtime):
    res = gen.register_governed_hypothesis({"statement": "nøgen", "provenance": {}})
    assert res["status"] == "rejected"


def test_full_generation_tick_registers(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    res = gen.run_hypothesis_generation_tick()
    assert res["status"] == "ok" and res["registered"] == 1
    active = gen.list_active_hypotheses()
    assert active and "memory" in active[0]["statement"]
    # idempotent: anden tick registrerer ikke dubletten
    res2 = gen.run_hypothesis_generation_tick()
    assert res2["registered"] == 0 and res2["duplicate"] >= 1


def test_grounded_samples_resolve_hypothesis(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    hyp_id = gen.list_active_hypotheses()[0]["hyp_id"]
    # 5 jordede støttende samples (sample_size=5) → resolve supported
    out = None
    for i in range(5):
        out = gen.record_governed_sample(hyp_id, supports=True, falsifies=False,
                                         source="run_outcome", ground_ref=f"run-{i}",
                                         triggered_by="world")
    assert out["hyp_status"] == "resolved" and out["outcome"] == "supported"


def test_unverified_grounding_does_not_resolve(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    hyp_id = gen.list_active_hypotheses()[0]["hyp_id"]
    # samples uden ground_ref → tæller ikke som jordede → forbliver aktiv (afventer)
    for i in range(6):
        out = gen.record_governed_sample(hyp_id, supports=True, source="run_outcome")
    assert out["hyp_status"] == "active"


def test_detect_outcome_divergence(isolated_runtime):
    """Rådets dybeste: samme årsag → modsatte udfald = divergens (konflikt-trigger)."""
    _seed_edges(isolated_runtime, [
        ("decision.created", "behavioral_decision_review.kept", 3, "inferred-kind"),
        ("decision.created", "behavioral_decision_review.broken", 2, "inferred-kind"),
        ("tool.invoked", "tool.completed", 4, "inferred-id"),   # kun én side → ikke divergens
    ])
    cands = gen.detect_outcome_divergence_candidates(min_each=2)
    fams = {c["parent_family"] for c in cands}
    assert "decision" in fams            # fører til BEGGE kept+broken
    assert "tool" not in fams            # kun completed, ingen error → ingen divergens
    hyp = gen.formulate_divergence_hypothesis(cands[0])
    from core.services import central_hypothesis_governance as gov
    ok, _ = gov.validate_preregistration(hyp)
    assert ok and hyp["source"] == "causal_divergence"
    assert "skjult" in hyp["statement"]


def test_tick_registers_both_convergence_and_divergence(isolated_runtime):
    _seed_edges(isolated_runtime, [
        ("memory.recall_fail", "somatic.stress", 4, "inferred-kind"),                  # konvergens
        ("decision.created", "behavioral_decision_review.kept", 3, "inferred-kind"),   # divergens (kept
        ("decision.created", "behavioral_decision_review.broken", 3, "inferred-kind"), #  + broken)
    ])
    res = gen.run_hypothesis_generation_tick()
    assert res["status"] == "ok"
    assert res["divergence"] >= 1 and res["registered"] >= 2
    statements = " ".join(h["statement"] for h in gen.list_active_hypotheses(limit=10))
    assert "skjult" in statements       # divergens-hypotesen er registreret


def test_stance_divergence_becomes_hypothesis(isolated_runtime, monkeypatch):
    """Lag 3 v3: gentagen tvær-modal uenighed → governed divergens-hypotese."""
    monkeypatch.setattr(gen, "detect_causal_convergence_candidates", lambda **k: [])
    monkeypatch.setattr(gen, "detect_outcome_divergence_candidates", lambda **k: [])
    monkeypatch.setattr(gen, "detect_stance_divergence_candidates",
                        lambda **k: [{"key": "gut:proceed|somatic:stress",
                                      "count": 5, "desc": "gut vil frem, men kroppen bremser"}])
    res = gen.run_hypothesis_generation_tick()
    assert res["divergence"] >= 1 and res["registered"] >= 1
    stmts = " ".join(h["statement"] for h in gen.list_active_hypotheses(limit=10))
    assert "UENIGE" in stmts and "kroppen bremser" in stmts


def test_prediction_error_surprise_becomes_hypothesis(isolated_runtime, monkeypatch):
    """Tråd 4-bro (§6): en overraskelse fra sekvens-modellen → governed prediction_error-hypotese,
    fuldt pre-registreret + notation via lexicon (runtime→cost er bundne familier)."""
    monkeypatch.setattr(gen, "detect_causal_convergence_candidates", lambda **k: [])
    monkeypatch.setattr(gen, "detect_outcome_divergence_candidates", lambda **k: [])
    monkeypatch.setattr(gen, "detect_stance_divergence_candidates", lambda **k: [])
    monkeypatch.setattr(gen, "detect_prediction_error_candidates",
                        lambda: [{"from_family": "memory", "to_family": "somatic",
                                  "prob": 0.01, "from_total": 101, "cursor": 42}])
    res = gen.run_hypothesis_generation_tick()
    assert res["registered"] >= 1
    active = gen.list_active_hypotheses(limit=10)
    perr = [h for h in active if "overrasket" in h["statement"]]
    assert perr, "prediction_error-hypotese blev ikke registreret"
    # provenance-mekanisme + notation sat korrekt → sampleren kan finde test-stien
    import json as _json
    from core.runtime.db import connect
    with connect() as c:
        row = c.execute("SELECT source, provenance_json, notation_il FROM central_hypotheses "
                        "WHERE source='prediction_error'").fetchone()
    prov = _json.loads(row["provenance_json"] or "{}")
    assert prov.get("mechanism") == "prediction_error" and prov.get("family") == "memory->somatic"
    # memory→somatic er bundne (kontinuitet, krop) → rendret via lexicon med stød-operatoren
    assert row["notation_il"] and "!" in row["notation_il"]


def test_awareness_surface_shows_generated_hypotheses(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    txt = gen.format_governed_hypotheses_for_awareness()
    assert txt and "memory" in txt and "jordede samples" in txt
    # tom tilstand → None (ingen støj i prompten)
    from core.runtime.db import connect
    with connect() as c:
        c.execute("DELETE FROM central_hypotheses")
        c.commit()
    assert gen.format_governed_hypotheses_for_awareness() is None


def test_self_triggered_confirmation_quarantined(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    hyp_id = gen.list_active_hypotheses()[0]["hyp_id"]
    # bekræftelse hvor triggered_by == hyp_id (selv-opfyldende) → karantæne
    out = gen.record_governed_sample(hyp_id, supports=True, source="run_outcome",
                                     ground_ref="run-x", triggered_by=hyp_id)
    assert out["hyp_status"] == "quarantined"


def test_samme_evidens_taeller_kun_en_gang_paa_tvaers_af_kald(isolated_runtime):
    """VARIG idempotens (målt 4/11-2026).

    Dedup'en i `gov.evaluate()` virker kun INDEN FOR én evaluering. Generatoren indsatte
    samme observation som en NY række hver gang og brugte den GEMTE confidence som
    indgang — så samme falsifikation leveret ved to kald gav 0,8 → 0,4 → 0,2. Målt i
    drift: 4.815 hypoteser havde samme (source, ground_ref) op til 5 gange.

    Testen kræver at kontrakten holder på tværs af separate kald, ikke kun i ét sæt.
    """
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    hyp_id = gen.list_active_hypotheses()[0]["hyp_id"]

    foerste = gen.record_governed_sample(hyp_id, supports=False, falsifies=True,
                                         source="run_outcome", ground_ref="run-1")
    assert foerste["status"] == "ok"
    conf_efter_foerste = foerste["confidence"]

    # Samme observation igen — to gange. Confidence må IKKE flytte sig.
    for _ in range(2):
        igen = gen.record_governed_sample(hyp_id, supports=False, falsifies=True,
                                          source="run_outcome", ground_ref="run-1")
        assert igen["status"] == "noop", f"duplikat skulle afvises, fik {igen}"
        assert igen["reason"] == "duplikat-evidens"

    from core.runtime.db import connect
    with connect() as c:
        n = c.execute("SELECT COUNT(*) FROM central_hypothesis_samples WHERE hyp_id=?",
                      (hyp_id,)).fetchone()[0]
        conf = c.execute("SELECT confidence FROM central_hypotheses WHERE hyp_id=?",
                         (hyp_id,)).fetchone()[0]
    assert n == 1, f"kun ét sample må være gemt, fik {n}"
    assert conf == conf_efter_foerste, f"confidence flyttede sig: {conf_efter_foerste} → {conf}"


def test_forskellige_ground_ref_taeller_hver_for_sig(isolated_runtime):
    """Modstykket: dedup'en må ikke slå for hårdt. Unik evidens skal stadig virke."""
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    hyp_id = gen.list_active_hypotheses()[0]["hyp_id"]

    a = gen.record_governed_sample(hyp_id, supports=False, falsifies=True,
                                   source="run_outcome", ground_ref="run-a")
    b = gen.record_governed_sample(hyp_id, supports=False, falsifies=True,
                                   source="run_outcome", ground_ref="run-b")
    assert a["status"] == "ok" and b["status"] == "ok"
    assert b["confidence"] < a["confidence"], "to unikke falsifikationer skal trække mere end én"

    from core.runtime.db import connect
    with connect() as c:
        n = c.execute("SELECT COUNT(*) FROM central_hypothesis_samples WHERE hyp_id=?",
                      (hyp_id,)).fetchone()[0]
    assert n == 2


# ── Outcome kommer fra EVIDENSEN, ikke fra en confidence-taerskel ─────────────────
def _insert_dom_hyp(hyp_id: str, *, confidence: float, sample_size: int = 5) -> None:
    import json as _json
    from datetime import datetime, timezone
    from core.runtime.db import connect
    gen.ensure_schema()
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute(
            "INSERT INTO central_hypotheses (hyp_id, source, statement, prediction,"
            " null_hypothesis, success_criterion, sample_size, ttl_seconds, provenance_json,"
            " confidence, status, outcome, grounded_samples, created_at, resolved_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (hyp_id, "test", "t", "p", "n", "s", sample_size, 168 * 3600,
             _json.dumps({"mechanism": "causal_edges", "family": "a->b", "cursor_id": "c1"}),
             confidence, "active", None, 0, now, None))
        c.commit()


def _dom_row(hyp_id: str) -> dict:
    from core.runtime.db import connect
    with connect() as c:
        r = c.execute("SELECT * FROM central_hypotheses WHERE hyp_id=?", (hyp_id,)).fetchone()
    return dict(r)


def test_stoette_flertal_men_lav_confidence_giver_supported(isolated_runtime):
    """MAALT 4/11-2026: 16.658 af 32.983 'contradicted' (50,5 %) havde stoette >= modsigelse.

    Den gamle regel var `outcome = 'supported' if verdict.confidence >= 0,5 else 'contradicted'`.
    En Popper-modsigelse halverer confidence — saa en hypotese med 4 stoettende mod 1 modsigende
    ender paa ~0,23 og blev stemplet 'modbevist', selv om evidensen IKKE modsagde den (4 > 1).
    Det er samme fejlform som 0/0 -> 0.0: et tal der ikke maaler det navnet siger.
    Kontrakten siger "uden lige saa mange der modsiger den".

    (Fem RENE stoettende giver 0,583 og rammer ikke fejlen — derfor skal testen bruge blandet
    evidens, praecis som de 16.658 i drift har.)
    """
    _insert_dom_hyp("hyp-lav-conf", confidence=0.30)
    for i in range(4):
        gen.record_governed_sample(
            "hyp-lav-conf", supports=True, source="world_consequence",
            ground_ref=f"stott-{i}", triggered_by="world")
    gen.record_governed_sample(
        "hyp-lav-conf", supports=False, falsifies=True, source="world_consequence",
        ground_ref="mod-0", triggered_by="world")
    row = _dom_row("hyp-lav-conf")
    assert row["status"] == "resolved"
    assert row["confidence"] < 0.5, (
        f"testen rammer ikke fejlen: confidence {row['confidence']} er ikke under taersklen")
    assert row["outcome"] == "supported", (
        f"4 stoettende mod 1 modsigende blev doemt {row['outcome']!r} "
        f"fordi confidence var {row['confidence']} — ikke fordi evidensen modsagde den")


def test_flertal_af_modsigelser_giver_contradicted(isolated_runtime):
    """Modproeven: naar modsigelserne faktisk er flertallet, skal dommen vaere contradicted —
    ogsaa selv om confidence tilfaeldigvis ligger over 0,5."""
    _insert_dom_hyp("hyp-mod", confidence=0.90)
    for i in range(5):
        gen.record_governed_sample(
            "hyp-mod", supports=False, falsifies=True, source="world_consequence",
            ground_ref=f"mod-{i}", triggered_by="world")
    row = _dom_row("hyp-mod")
    assert row["outcome"] == "contradicted", (
        f"fem modsigelser og nul stoettende blev doemt {row['outcome']!r}")


def test_jordet_men_retningsneutral_evidens_giver_ingen_dom(isolated_runtime):
    """MAALT 4/11-2026: 2.896 af 140.775 afgjorte havde 5 jordede observationer hvor INGEN
    stottede og INGEN modsagde — og blev alligevel stemplet 'supported' (confidence 0,676),
    fordi den gamle regel kun saa paa tallet.

    En ren `_stott > _mods`-regel ville goere dem til 'contradicted': 0 > 0 er falsk. Det er
    samme fejlform med modsat fortegn — en dom uden grundlag. Kontrakten kraever at
    overgangen GENTAGER sig, og en neutral observation siger intet om det. Derfor: ingen dom,
    hypotesen forbliver aktiv og TTL-sweep'en afgoer senere.
    """
    _insert_dom_hyp("hyp-neutral", confidence=0.30)
    for i in range(5):
        gen.record_governed_sample(
            "hyp-neutral", supports=False, falsifies=False, source="world_consequence",
            ground_ref=f"obs-{i}", triggered_by="world")
    row = _dom_row("hyp-neutral")
    assert row["status"] == "active", (
        f"retningsneutral evidens udloeste status {row['status']!r} — der er intet grundlag "
        f"for en dom (outcome={row['outcome']!r})")
    assert row["outcome"] is None, f"dom uden retning: outcome={row['outcome']!r}"
    assert row["grounded_samples"] == 5, "observationerne skal stadig taelle som jordede"


def test_like_mange_paa_begge_sider_giver_ingen_dom(isolated_runtime):
    """MAALT 4/11-2026: 2.040 af 140.775 havde lige mange stottende og modsigende (fx 2-2)
    og blev alle stemplet 'contradicted'. Kontrakten siger "uden lige saa mange der modsiger
    den" — et 3-3-resultat opfylder den ikke, men det MODBEVISER den heller ikke.

    2+2 mod sample_size=4: gaten ER passeret, det er selve retningen der er uafgjort.
    (Med krav 5 ville det femte sample afgoere sagen foer det sjette kunne indsaettes —
    hypotesen var allerede resolved, saa det sidste blev afvist som noop.)
    """
    _insert_dom_hyp("hyp-lige", confidence=0.50, sample_size=4)
    for i in range(2):
        gen.record_governed_sample(
            "hyp-lige", supports=True, source="world_consequence",
            ground_ref=f"st-{i}", triggered_by="world")
    for i in range(2):
        gen.record_governed_sample(
            "hyp-lige", supports=False, falsifies=True, source="world_consequence",
            ground_ref=f"mo-{i}", triggered_by="world")
    row = _dom_row("hyp-lige")
    assert row["grounded_samples"] == 4, (
        f"testen rammer ikke gaten: {row['grounded_samples']} jordede mod krav 4")
    assert row["status"] == "active", (
        f"3-3 udloeste status {row['status']!r} (outcome={row['outcome']!r}) — "
        f"ingen side har flertal")
    assert row["outcome"] is None
