"""Tests for core/services/central_hypothesis_sampler.py — Lag 3 loop-lukning (test mod virkelighed)."""
from __future__ import annotations

import pytest

from core.services import central_hypothesis_sampler as smp
from core.services import central_hypothesis_generator as gen


def _bind_events(monkeypatch, seq):
    """seq: list of (id, kind, iso_ts) — bindes som event_bus.recent()."""
    import core.eventbus.bus as bus

    class _Bus:
        def recent(self, limit=3000):
            return [{"id": i, "kind": k, "created_at": t} for i, k, t in seq][:limit]
    monkeypatch.setattr(bus, "event_bus", _Bus())


def _ts(sec):
    # simple monotone timestamps
    return f"2026-07-02T00:00:{sec:02d}+00:00"


def test_supports_when_y_follows_x(monkeypatch):
    # X altid tæt fulgt af Y → betinget rate høj vs baseline → supports
    seq = []
    eid = 1
    for base in range(0, 60, 2):
        seq.append((eid, "memory.recall_fail", _ts(base))); eid += 1
        seq.append((eid, "somatic.stress", _ts(base + 1))); eid += 1
    _bind_events(monkeypatch, seq)
    res = smp.test_causal_hypothesis("memory", "somatic")
    assert res is not None and res["supports"] is True and res["falsifies"] is False


def test_falsifies_when_no_lift(monkeypatch):
    # Y forekommer aldrig efter X (spredt/uafhængigt) → ingen lift → falsifies
    seq = []
    eid = 1
    for base in range(0, 60, 2):
        seq.append((eid, "memory.recall_fail", _ts(base))); eid += 1
        seq.append((eid, "tool.completed", _ts(base + 1))); eid += 1
    _bind_events(monkeypatch, seq)
    res = smp.test_causal_hypothesis("memory", "somatic")   # somatic forekommer slet ikke
    assert res is not None and res["supports"] is False and res["falsifies"] is True


def test_too_little_data_returns_none(monkeypatch):
    _bind_events(monkeypatch, [(1, "a.x", _ts(0)), (2, "b.y", _ts(1))])
    assert smp.test_causal_hypothesis("a", "b") is None


def test_sampler_tick_records_grounded_samples(isolated_runtime, monkeypatch):
    # registrér en causal-hypotese memory->somatic
    gen.ensure_schema()
    gen.register_governed_hypothesis(gen.formulate_correlation_hypothesis(
        {"parent_family": "memory", "child_family": "somatic", "count": 4, "cursor": 10}))
    # event-strøm hvor somatic altid følger memory → supports
    seq = []
    eid = 1
    for base in range(0, 60, 2):
        seq.append((eid, "memory.recall_fail", _ts(base))); eid += 1
        seq.append((eid, "somatic.stress", _ts(base + 1))); eid += 1
    _bind_events(monkeypatch, seq)
    res = smp.run_hypothesis_sampler_tick()
    assert res["status"] == "ok" and res["tested"] == 1 and res["supported"] == 1
    # hypotesen har nu 1 grounded sample
    active = gen.list_active_hypotheses()
    assert active and active[0]["grounded_samples"] == 1


def test_sampler_tests_stance_divergence(isolated_runtime, monkeypatch):
    """§8.4: stance-divergens-hypoteser resolver nu (før: skippet permanent)."""
    gen.ensure_schema()
    gen.register_governed_hypothesis(gen.formulate_stance_divergence_hypothesis(
        {"key": "gut:proceed|somatic:stress", "count": 5, "desc": "gut vil frem, kroppen bremser"}))
    import core.services.central_stance as cs
    # tension'en gentager sig stadig → persistens → supports
    monkeypatch.setattr(cs, "recurring_tensions",
                        lambda **k: [{"key": "gut:proceed|somatic:stress", "count": 5}])
    res = smp.run_hypothesis_sampler_tick()
    assert res["tested"] >= 1 and res["supported"] >= 1


def test_sampler_tests_causal_divergence(isolated_runtime, monkeypatch):
    """§8.4: causal-divergens-hypoteser resolver nu (persistens-test)."""
    gen.ensure_schema()
    gen.register_governed_hypothesis(gen.formulate_divergence_hypothesis(
        {"parent_family": "decision", "good": "kept", "bad": "broken",
         "good_count": 3, "bad_count": 2, "cursor": 10}))
    # divergensen er der stadig → supports
    monkeypatch.setattr(gen, "detect_outcome_divergence_candidates",
                        lambda **k: [{"parent_family": "decision", "good": "kept", "bad": "broken",
                                      "good_count": 3, "bad_count": 2, "cursor": 11}])
    res = smp.run_hypothesis_sampler_tick()
    assert res["tested"] >= 1 and res["supported"] >= 1


def test_five_supporting_samples_resolve(isolated_runtime, monkeypatch):
    gen.ensure_schema()
    gen.register_governed_hypothesis(gen.formulate_correlation_hypothesis(
        {"parent_family": "memory", "child_family": "somatic", "count": 4, "cursor": 10}))
    seq = []
    eid = 1
    for base in range(0, 60, 2):
        seq.append((eid, "memory.recall_fail", _ts(base))); eid += 1
        seq.append((eid, "somatic.stress", _ts(base + 1))); eid += 1
    _bind_events(monkeypatch, seq)
    # 5 ticks — men hver tick skal se NY information. `ground_ref` er event-
    # cursoren, og idempotensen (4/11-2026) indsætter kun ét sample pr.
    # (source, ground_ref): en uændret strøm er ÉN observation målt fem gange,
    # ikke fem observationer. Uden dette ville testen måle sin egen antagelse.
    for i in range(5):
        smp.run_hypothesis_sampler_tick()
        seq.append((eid, "memory.recall_fail", _ts(i))); eid += 1
        seq.append((eid, "somatic.stress", _ts(i))); eid += 1
    from core.runtime.db import connect
    with connect() as c:
        row = c.execute("SELECT status, outcome, grounded_samples FROM central_hypotheses").fetchone()
    assert row["grounded_samples"] == 5, f"5 unikke observationer skulle give 5 samples, fik {row['grounded_samples']}"
    assert row["status"] == "resolved" and row["outcome"] == "supported"


# ── Evaluator-laget (4/11-2026) ────────────────────────────────────────────────
# Foer: ét `skipped`-tal blandt to helt forskellige ting — hypoteser der ALDRIG kan
# testes (ingen evaluator) og hypoteser der ikke kunne maales lige nu (for lidt data).
# Maalt i den levende base: 18 aktive laa i den foerste gruppe og blev hentet hvert
# 30. minut i ugevis. Navnet forsvandt; kun tallet stod tilbage.


def _insert_hyp(hyp_id: str, mechanism: str, family: str = "", *, age_hours: int = 0,
                ekstra: dict | None = None, contract: dict | None = None) -> None:
    import json
    from datetime import datetime, timezone, timedelta
    from core.runtime.db import connect
    gen.ensure_schema()
    created = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    prov = {"mechanism": mechanism, "family": family}
    if ekstra:
        prov.update(ekstra)
    with connect() as c:
        c.execute(
            "INSERT INTO central_hypotheses (hyp_id, source, statement, prediction, "
            "null_hypothesis, success_criterion, sample_size, ttl_seconds, provenance_json, "
            "confidence, status, grounded_samples, created_at, test_contract_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (hyp_id, "test", "s", "p", "n", ">= 5", 5, 604800,
             json.dumps(prov),
             0.5, "active", 0, created,
             json.dumps(contract) if contract is not None else None))


def test_hypotese_uden_evaluator_rapporteres_med_navn(isolated_runtime, monkeypatch):
    """En hypotese uden evaluator maa ikke forsvinde i et samlet tal."""
    _insert_hyp("hyp-doed", "dream_hypothesis_judge", "oneiric")
    res = smp.run_hypothesis_sampler_tick()
    assert res["tested"] == 0
    assert res["no_data"] == [], "hypotesen blev aldrig maalt — den er ikke 'no_data'"
    grunde = res["unevaluable"]
    assert list(grunde) == ["ingen evaluator registreret for oprindelse 'dream_hypothesis_judge'"], grunde
    assert grunde[list(grunde)[0]] == ["hyp-doed"], "hyp_id'et skal staa i rapporten"


def test_forkert_family_er_strukturel_gaeld_ikke_no_data(isolated_runtime, monkeypatch):
    """En REGISTRERET evaluator der ikke KAN teste kontraktformen er strukturel gaeld.

    Testen forventede foer `no_data` — men `family` staar i provenance og aendrer sig ikke,
    saa «proev igen om 30 minutter» var en loekke uden udgang. Kravet laa desuden inde i
    evaluatoren, som returnerede None, og None betoed «for lidt data». Maalt 4/11-2026:
    0 aktive ramt — fejlen var latent, men den bliver aktiv den dag en generator skriver
    en family i en anden form.
    """
    _insert_hyp("hyp-tynd", "causal_edges", family="uden-pil")   # kraever 'X->Y'
    res = smp.run_hypothesis_sampler_tick()
    assert res["tested"] == 0
    assert res["no_data"] == [], "formen kan ikke blive rigtig af at vente paa data"
    assert len(res["unevaluable"]) == 1
    grund = list(res["unevaluable"])[0]
    assert "kraever" in grund and "uden-pil" in grund, grund


def test_ægte_no_data_naar_evaluatoren_mangler_data(isolated_runtime, monkeypatch):
    """Modsat kant: en evaluator der MATCHER formen, men hvor der er for lidt data, er no_data.

    Det er den forbigående tilstand — og den eneste der maa hedde no_data.
    """
    _insert_hyp("hyp-mangler-data", "causal_edges", family="a->b")
    _bind_events(monkeypatch, [(1, "a.x", _ts(0)), (2, "b.y", _ts(1))])  # < _MIN_EVENTS
    res = smp.run_hypothesis_sampler_tick()
    assert res["tested"] == 0
    assert res["unevaluable"] == {}, "evaluatoren kan teste formen — det er ikke strukturelt"
    assert res["no_data"] == ["hyp-mangler-data"]


def test_list_unevaluable_active_navngiver_hypotesen(isolated_runtime):
    _insert_hyp("hyp-a", "dream_hypothesis_judge", "oneiric")
    _insert_hyp("hyp-b", "prediction_error", "a->b")     # har evaluator
    out = smp.list_unevaluable_active()
    ids = {x["hyp_id"] for x in out}
    assert ids == {"hyp-a"}, f"kun hyp-a er utestbar, fik {ids}"
    assert "dream_hypothesis_judge" in out[0]["reason"]
    assert out[0]["origin"] == "dream_hypothesis_judge"


def test_eksplicit_evaluator_felt_slaar_broen(isolated_runtime):
    """Broen fra oprindelse er FALLBACK. Baerer hypotesen et evaluator-felt, vinder det —
    saa kan en hypotese foedt i én mekanisme testes af en anden.

    Men et NAVN er ikke en KONTRAKT. Kilden er `explicit`, ikke `contract`: der findes
    ingen valideret testkontrakt, kun en henvisning. Foerst naar `test_contract_json`
    validerer mod CONTRACT_TYPES maa Centralen kalde koblingen valideret.
    """
    navn, why, kilde = smp.evaluator_for(
        {"mechanism": "ukendt-ophav", "evaluator": "stance_persistence",
         "family": "nogen-tension"})
    assert (navn, why) == ("stance_persistence", None)
    assert kilde == "explicit", "et navn uden kontrakt er ikke en valideret kontrakt"
    # og et ukendt evaluator-navn afvises frem for at falde tilbage paa broen
    navn2, why2, _ = smp.evaluator_for(
        {"mechanism": "causal_edges", "evaluator": "findes-ikke"})
    assert navn2 is None and "ikke registreret" in str(why2)


def test_legacy_bro_rapporteres_som_legacy(isolated_runtime):
    """Uden et eksplicit felt er koblingen en LEGACY-bro — den skal ikke kunne forveksles
    med en valideret kontrakt i Centralens egne tal."""
    navn, why, kilde = smp.evaluator_for(
        {"mechanism": "causal_edges", "family": "a->b"})
    assert (navn, why, kilde) == ("causal_sequence", None, "legacy")


def test_family_der_ikke_matcher_evaluatoren_er_strukturel_gaeld(isolated_runtime):
    """En evaluator der ikke KAN teste kontraktformen er strukturel gæld — ikke «mangler data».

    Maalt 4/11-2026: kravet laa foer inde i evaluatoren, som returnerede None, og None blev
    tolket som «for lidt data lige nu». En permanent utestbar hypotese blev dermed forsoegt
    igen hvert 30. minut for evigt."""
    navn, why, _ = smp.evaluator_for(
        {"mechanism": "causal_edges", "family": "ingen-pil-her"})
    assert navn is None
    assert "kraever" in str(why) and "ingen-pil-her" in str(why)


def test_samme_evidens_forskellig_oprindelse_giver_samme_dom(isolated_runtime, monkeypatch):
    """BEVISET paa at ophav og evaluering er adskilt — ikke bare at navnet slaas rigtigt op.

    Tre hypoteser med IDENTISK family og IDENTISK evidens. Kun oprindelsen varierer:
    to mekanismer der peger paa samme evaluator via broen, og én mekanisme der SLET IKKE
    har en bro — den testes kun fordi den baerer et eksplicit evaluator-felt.

    Giver de ikke samme dom, sidder den gamle kobling stadig et sted i kaeden.
    """
    gen.ensure_schema()
    _insert_hyp("h-causal", "causal_edges", "memory->somatic")
    _insert_hyp("h-prederr", "prediction_error", "memory->somatic")
    _insert_hyp("h-judge", "dream_hypothesis_judge", "memory->somatic",
                ekstra={"evaluator": "causal_sequence"})

    seq = []
    eid = 1
    for base in range(0, 60, 2):
        seq.append((eid, "memory.recall_fail", _ts(base))); eid += 1
        seq.append((eid, "somatic.stress", _ts(base + 1))); eid += 1
    _bind_events(monkeypatch, seq)

    smp.run_hypothesis_sampler_tick()

    from core.runtime.db import connect
    with connect() as c:
        def _dom(hid):
            return [dict(r) for r in c.execute(
                "SELECT supports, falsifies FROM central_hypothesis_samples"
                " WHERE hyp_id=?", (hid,)).fetchall()]
        a, b, c_ = _dom("h-causal"), _dom("h-prederr"), _dom("h-judge")

    assert a and b and c_, f"en af dem fik intet sample: {a} {b} {c_}"
    assert a == b, f"to oprindelser med SAMME evaluator gav forskellig dom: {a} vs {b}"
    assert a == c_, f"eksplicit evaluator blev overruled af oprindelsen: {a} vs {c_}"


# ── Testkontrakten (4/11-2026) ─────────────────────────────────────────────────
# Maalt: 0 af 505 aktive hypoteser bar en valideret kontrakt. Retningen laa hardkodet
# i family-konventionen 'latency:W>L' og i et if/else — saa en hypotese der paastod
# det MODSATTE kunne ikke udtrykkes, og to hypoteser med modsatrettede forventninger
# ville faa samme dom paa samme data.

_CONTRACT_BASE = {
    "schema_version": 1,
    "contract_type": "comparative_latency",
    "evaluator": "model_meta_persistence",
    "evaluator_version": 1,
    "subject": "p/fast",
    "comparator": "p/slow",
    "metric": "latency_ms",
    "min_samples": 5,
    "time_basis": "ingestion_time",
    "evaluation_policy": "latency_margin_v1",
    "policy_version": 1,
    # Evidens-specifikationen (4/11-2026): hvad tælles, hvordan vælges det, hvordan
    # vægtes det. Uden den ved dommen ikke om `min_samples: 5` betyder fem uafhængige
    # observationer eller én målt fem gange.
    "evidence_unit": "per_run",
    "window_semantics": "rolling_run_count",
    "aggregation": "equal_weight",
}


def test_modsatrettede_forventninger_giver_modsatte_domme(isolated_runtime, monkeypatch):
    """KONTRAKTEN STYRER EVALUERINGEN — ikke bare gemmes og valideres.

    To hypoteser med SAMME ophav, SAMME family og PRÆCIS samme observationsdata.
    Kun `expected_relation` er modsat. Hvis begge får samme dom, læser evaluatoren
    stadig family-konventionen i stedet for kontrakten — og så er hele kontrakt-laget
    pynt. Det er den test der afgør om betydningen følger påstanden hele vejen.
    """
    from core.services import central_model_meta as mm
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 20, "lat_n": 20, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 20, "lat_n": 20, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    # Samme family for BEGGE — den ville give samme dom hvis den blev laest.
    _insert_hyp("h-a", "model_meta", "latency:p/fast>p/slow",
                contract={**_CONTRACT_BASE, "expected_relation": "less_than"})
    _insert_hyp("h-b", "model_meta", "latency:p/fast>p/slow",
                contract={**_CONTRACT_BASE, "expected_relation": "greater_than"})

    res = smp.run_hypothesis_sampler_tick()
    assert res["tested"] == 2, res

    from core.runtime.db import connect
    with connect() as c:
        def _dom(hid):
            return [dict(r) for r in c.execute(
                "SELECT supports, falsifies FROM central_hypothesis_samples"
                " WHERE hyp_id=?", (hid,)).fetchall()]
        a, b = _dom("h-a"), _dom("h-b")

    assert a == [{"supports": 1, "falsifies": 0}], f"A (X hurtigere) skal støttes: {a}"
    assert b == [{"supports": 0, "falsifies": 1}], f"B (X langsommere) skal modsiges: {b}"


def test_hurtigere_men_ikke_markant_nok_er_uafgjort_ikke_modbevist(isolated_runtime, monkeypatch):
    """TREDJE UDFALD: «hurtigere, men ikke markant nok» er ikke et modbevis.

    Kontraktens politik kræver 25 % margin for støtte. Er X kun 10 % hurtigere, er
    observationen uafgjort — ikke en modsigelse. Et binært udfald ville stemple al
    utydelig evidens som modsigelse, og det er præcis den fejlform der gav 14.618
    hypoteser stemplet «modbevist» på et tal i stedet for på evidens.
    """
    from core.services import central_model_meta as mm
    # 100 mod 110: X er hurtigere, men kun ~9 % — under 25 %-margin.
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 20, "lat_n": 20, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 20, "lat_n": 20, "latency_ms": 110.0, "latency_median_ms": 110.0},
    })
    _insert_hyp("h-svag", "model_meta", "latency:p/fast>p/slow",
                contract={**_CONTRACT_BASE, "expected_relation": "less_than"})

    res = smp.run_hypothesis_sampler_tick()
    assert res["tested"] == 1, res
    assert res["supported"] == 0 and res["contradicted"] == 0, (
        f"en utydelig observation maa hverken stotte eller modsige: {res}")

    from core.runtime.db import connect
    with connect() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT supports, falsifies FROM central_hypothesis_samples"
            " WHERE hyp_id='h-svag'").fetchall()]
    assert rows == [{"supports": 0, "falsifies": 0}], (
        f"observationen skal vaere jordet UDEN retning: {rows}")


def test_politikken_kommer_fra_kontrakten_ikke_fra_modulet(isolated_runtime, monkeypatch):
    """Beslutningsreglen skal vaere PINNET i kontrakten, ikke laant fra et andet modul.

    Maalt 4/11-2026 laeste kontrakt-stien `_LATENCY_MARGIN` fra `central_model_meta`
    med en hardkodet fallback. AEndrede nogen den konstant, ville hypoteser oprettet
    for maaneder siden faa en anden dom — uden at nogen havde roert deres kontrakt.
    """
    from core.services import central_model_meta as mm
    from core.services import central_test_contract as tc

    # Flyt modul-konstanten til noget absurd: hvis den stadig blev laest, ville
    # 100 mod 1000 ikke laengere taelle som stotte.
    monkeypatch.setattr(mm, "_LATENCY_MARGIN", 100.0, raising=False)
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 20, "lat_n": 20, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 20, "lat_n": 20, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    _insert_hyp("h-pin", "model_meta", "latency:p/fast>p/slow",
                contract={**_CONTRACT_BASE, "expected_relation": "less_than"})

    res = smp.run_hypothesis_sampler_tick()
    assert res["supported"] == 1, (
        f"dommen fulgte modul-konstanten i stedet for kontraktens politik: {res}")

    # Og politikken selv skal vaere laesbar og versioneret.
    pol = tc.policy_of(_CONTRACT_BASE)
    assert pol is not None and pol["version"] == 1, pol


def test_kontrakt_uden_politik_afvises(isolated_runtime):
    """En kontrakt uden beslutningskriterium maa ikke accepteres.

    «En evaluator maa ikke acceptere en kontrakt, hvis dens beslutningskriterier
    mangler» — ellers er kontrakten deklarativ mens dommen er imperativ, og de to
    kan glide fra hinanden uden at nogen roerer hypotesen.
    """
    from core.services import central_test_contract as tc
    uden = {k: v for k, v in _CONTRACT_BASE.items() if k != "evaluation_policy"}
    ok, missing = tc.validate(uden)
    assert not ok, "kontrakt uden evaluation_policy blev accepteret"
    assert any("evaluation_policy" in m for m in missing), missing

    ukendt = {**_CONTRACT_BASE, "evaluation_policy": "opfundet_politik_v9"}
    ok2, missing2 = tc.validate(ukendt)
    assert not ok2 and any("evaluation_policy" in m for m in missing2), missing2


def test_kontrakt_hypotese_rapporteres_som_contract(isolated_runtime, monkeypatch):
    """En valideret kontrakt er den ENESTE kilde der maa hedde `contract` i Centralens tal."""
    from core.services import central_model_meta as mm
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 20, "lat_n": 20, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 20, "lat_n": 20, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    _insert_hyp("h-kontrakt", "model_meta", "latency:p/fast>p/slow",
                contract={**_CONTRACT_BASE, "expected_relation": "less_than"})
    _insert_hyp("h-bro", "causal_edges", "a->b")     # legacy, ingen kontrakt
    ud = smp.evaluator_provenance()
    assert ud["contract"] == 1, ud
    assert ud["legacy"] == 1, ud


def test_ugyldig_kontrakt_afvises_ved_oprettelse(isolated_runtime):
    """Et gyldigt JSON-objekt er ikke en gyldig kontrakt.

    Modellen maa FORESLAA en kontrakt; Centralen VALIDERER den mod CONTRACT_TYPES.
    Mangler evaluator_version eller min_samples, maa hypotesen ikke blive oprettet
    som om den var efterprøvbar.
    """
    cand = gen.formulate_correlation_hypothesis(
        {"parent_family": "a", "child_family": "b", "count": 4, "cursor": 1})
    cand["test_contract"] = {
        "schema_version": 1,
        "contract_type": "comparative_latency",
        "evaluator": "model_meta_persistence",
        "subject": "x", "comparator": "y",
        "expected_relation": "less_than",
    }
    res = gen.register_governed_hypothesis(cand)
    assert res["status"] == "rejected", res
    assert res.get("reason") == "ugyldig test_contract"
    assert any("min_samples" in m for m in res["missing"]), res["missing"]
    assert any("evaluator_version" in m for m in res["missing"]), res["missing"]


def test_ukendt_kontrakttype_afvises(isolated_runtime):
    """En kontrakttype Centralen ikke kan efterprøve maa ikke accepteres."""
    from core.services import central_test_contract as tc
    ok, missing = tc.validate({**_CONTRACT_BASE, "contract_type": "opfundet_type",
                               "expected_relation": "less_than"})
    assert ok is False and any("contract_type" in m for m in missing), missing


def test_event_time_afvises_som_tidsbasis(isolated_runtime):
    """Kontrakten maa ikke paastaa at maale en tidsbasis infrastrukturen ikke baerer.

    `central_hypothesis_samples.created_at` saettes ved indsaettelse — event-time
    findes kun indirekte via ground_ref. En kontrakt der siger `event_time` ville
    lyve om praecis det punkt hvor dommen beregnes.
    """
    from core.services import central_test_contract as tc
    ok, missing = tc.validate({**_CONTRACT_BASE, "expected_relation": "less_than",
                               "time_basis": "event_time"})
    assert ok is False and any("event_time" in m for m in missing), missing


def test_ny_hypotese_fra_oprettelse_til_dom_paa_kontrakt(isolated_runtime, monkeypatch):
    """HELE livscyklussen gennem den ÆGTE oprettelsesvej: opret → validér → gem → evaluér → dom.

    Ikke `_insert_hyp` (som skriver direkte i DB), men `register_governed_hypothesis` —
    den vej en generator faktisk bruger. Det er kæden der skal virke, hvis `contract: 0`
    skal kunne blive `contract: 1` af en reel grund og ikke fordi et felt blev tilføjet.
    """
    import json
    from core.services import central_model_meta as mm
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 20, "lat_n": 20, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 20, "lat_n": 20, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    cand = {
        "source": "model_meta",
        "statement": "p/fast er hurtigere end p/slow",
        "prediction": "p/fast bevarer sin latency-fordel over friske runs",
        "null_hypothesis": "p/fast og p/slow er reelt lige hurtige",
        "success_criterion": ">= 5 jordede maalinger hvor fordelen holder",
        "sample_size": 5,
        "provenance": {"mechanism": "model_meta", "family": "latency:p/fast>p/slow",
                       "cursor_id": 20},
        "test_contract": {**_CONTRACT_BASE, "expected_relation": "less_than"},
    }
    reg = gen.register_governed_hypothesis(cand)
    assert reg["status"] == "registered" and reg["contract"] is True, reg

    # Kontrakten ligger PAA hypotesen — ikke som en reference til noget der kan aendre sig.
    from core.runtime.db import connect
    with connect() as c:
        row = c.execute("SELECT test_contract_json FROM central_hypotheses WHERE hyp_id=?",
                        (reg["hyp_id"],)).fetchone()
    assert json.loads(row["test_contract_json"])["expected_relation"] == "less_than"

    res = smp.run_hypothesis_sampler_tick()
    assert res["tested"] == 1 and res["supported"] == 1, res

    with connect() as c:
        dom = c.execute("SELECT supports, falsifies FROM central_hypothesis_samples"
                        " WHERE hyp_id=?", (reg["hyp_id"],)).fetchone()
    assert (dom["supports"], dom["falsifies"]) == (1, 0)

    # Og den tælles som kontrakt — ikke som legacy-bro.
    ud = smp.evaluator_provenance()
    assert ud["contract"] == 1 and ud["legacy"] == 0, ud


def test_ground_ref_daekker_begge_parter_ikke_kun_subject(isolated_runtime, monkeypatch):
    """Ny comparator-data må ikke afvises som «duplikat».

    Målt 4/11-2026: `cursor` var `sa["samples"]` alene. Når kun comparator fik nye
    runs ændrede latency-målet sig, men ground_ref stod stille — og dedup'en i
    `record_governed_sample` (nøgle: source+ground_ref) afviste observationen som
    duplikat. Centralen kunne altså overse ny evidens om præcis den hypotese den
    netop testede. ground_ref skal identificere OBSERVATIONEN, og observationen er
    begge parters tilstand.
    """
    from core.services import central_model_meta as mm

    contract = {**_CONTRACT_BASE, "expected_relation": "less_than"}

    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 10, "lat_n": 10, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 5, "lat_n": 5, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    a = smp._eval_contract_comparative(contract)
    # Noeglen baerer nu ogsaa en hash af de faktiske rækker — et antal alene er
    # ikke en identitet (korrigeret maaling / rullende vindue, maalt 4/11-2026).
    assert a["cursor"].startswith("5u:10:5:"), a

    # Samme subject, men comparator har fået ét run mere: en NY observation.
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 10, "lat_n": 10, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 6, "lat_n": 6, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    b = smp._eval_contract_comparative(contract)
    assert b["cursor"].startswith("6u:10:6:"), b
    assert a["cursor"] != b["cursor"], \
        "ny comparator-data må ikke se ud som den samme observation"


# ── Observations-identitet (4/11-2026, anden runde) ───────────────────────────
# `ground_ref` var `"23:5"` = ANTAL runs. Et antal er ikke en identitet: to
# forskellige datasæt kan have samme antal. ChatGPT pegede på netop dette efter
# foerste rettelse — og maalt bagefter er det ikke teoretisk: subject faar 0,40
# nye runs pr. tick, saa fem samples bygger paa et grundlag der er vokset med
# 2-3 runs ud af 23. Nøglen bærer derfor en hash af de faktiske rækker.

def _run(rid: str, model: str, start: str, slut: str) -> dict:
    return {"provider": "p", "model": model, "run_id": rid,
            "started_at": start, "finished_at": slut}


def test_korrigeret_maaling_giver_ny_observation(isolated_runtime, monkeypatch):
    """Rettes én måling, ændrer ANTALLET runs sig ikke — men grundlaget gør.

    Uden hashen ville den korrigerede måling få samme `ground_ref` som den gamle og
    blive afvist som duplikat: Centralen ville mangle evidens om at grundlaget flyttede sig.
    """
    from core.services import central_model_meta as mm
    from core.runtime import db as rdb
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 10, "lat_n": 10, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 5, "lat_n": 5, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    rows = [_run("r1", "fast", "t1", "t2"), _run("r2", "slow", "t3", "t4")]
    monkeypatch.setattr(rdb, "recent_visible_runs", lambda **k: rows)
    a = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than"})

    rows[1] = {**rows[1], "finished_at": "t4-korrigeret"}
    b = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than"})

    assert a["cursor"] != b["cursor"], (
        f"korrigeret maaling skal give en NY observation, ikke en dublet:"
        f" {a['cursor']} vs {b['cursor']}")


def test_rullende_vindue_giver_ny_observation(isolated_runtime, monkeypatch):
    """300-runs-vinduet glider: samme ANTAL kan dække helt forskellige runs."""
    from core.services import central_model_meta as mm
    from core.runtime import db as rdb
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 10, "lat_n": 10, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 5, "lat_n": 5, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    foerste = [_run("r1", "fast", "t1", "t2"), _run("r2", "slow", "t3", "t4")]
    monkeypatch.setattr(rdb, "recent_visible_runs", lambda **k: foerste)
    a = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than"})

    # samme antal rækker — men de ældste er rullet ud og nye kommet ind
    monkeypatch.setattr(rdb, "recent_visible_runs", lambda **k: [
        _run("r9", "fast", "t9", "t10"), _run("r8", "slow", "t7", "t8")])
    b = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than"})

    assert a["cursor"] != b["cursor"], (
        f"rullende vindue skal give en NY observation: {a['cursor']} vs {b['cursor']}")


def test_identisk_grundlag_giver_samme_observation(isolated_runtime, monkeypatch):
    """Modsat kant: uændret grundlag er STADIG en dublet. Hashen må ikke goere
    dedup virkningsloes — saa ville samme observation taelle fem gange som fem beviser."""
    from core.services import central_model_meta as mm
    from core.runtime import db as rdb
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 10, "lat_n": 10, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 5, "lat_n": 5, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    rows = [_run("r1", "fast", "t1", "t2"), _run("r2", "slow", "t3", "t4")]
    monkeypatch.setattr(rdb, "recent_visible_runs", lambda **k: rows)
    a = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than"})
    b = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than"})
    assert a["cursor"] == b["cursor"], (
        f"identisk grundlag skal give samme noegle — ellers taeller samme observation"
        f" flere gange: {a['cursor']} vs {b['cursor']}")
    assert a["cursor"].count(":") == 3, f"noeglen skal baere enheder + antal + hash: {a['cursor']}"


# ── Enheden i kontrakten (4/11-2026) ──────────────────────────────────────────
# Kontrakten bandt retningen, politikken og evaluatoren — men ikke ENHEDEN. Maalt:
# `min_samples: 5` talte fem kald til `aggregate_model_outcomes()`, ikke fem
# uafhaengige observationer; de fem kald laeste stort set samme rullende vindue
# (97,8 % overlap). «Fem beviser» var én observation maalt fem gange.


def test_kontrakt_uden_enhed_er_strukturel_gaeld_ikke_no_data(isolated_runtime, monkeypatch):
    """En kontrakt der ikke deklarerer sin enhed kan ALDRIG evalueres.

    Derfor skal den rapporteres som `unevaluable` — ikke som `no_data`. Forskellen er
    ikke kosmetisk: `no_data` betyder «proev igen om 30 minutter», og en kontrakt uden
    enhed bliver aldrig testbar af at vente paa data. Det er samme fejlform som
    family-mismatchet, som blev forsoegt hvert 30. minut i ugevis.
    """
    fra = {k: v for k, v in _CONTRACT_BASE.items() if k != "evidence_unit"}
    _insert_hyp("h-uden-enhed", "model_meta", "latency:p/fast>p/slow",
                contract={**fra, "expected_relation": "less_than"})

    res = smp.run_hypothesis_sampler_tick()
    assert res["tested"] == 0, res
    assert res["no_data"] == [], "en manglende enhed bliver ikke rigtig af at vente paa data"
    assert len(res["unevaluable"]) == 1, res["unevaluable"]
    grund = list(res["unevaluable"])[0]
    assert "evidence_unit" in grund, grund


def test_ikke_implementeret_enhed_er_strukturel_gaeld(isolated_runtime, monkeypatch):
    """`per_model_call` er registreret men IKKE implementeret — den maa ikke kunne testes.

    `costs` baerer intet per-kald start/slut, saa aegte per-kald-latency kan ikke maales.
    En kontrakt der paastod det ville lyve om praecis det punkt hvor dommen beregnes.
    """
    _insert_hyp("h-per-kald", "model_meta", "latency:p/fast>p/slow",
                contract={**_CONTRACT_BASE, "expected_relation": "less_than",
                          "evidence_unit": "per_model_call"})
    res = smp.run_hypothesis_sampler_tick()
    assert res["tested"] == 0, res
    assert res["no_data"] == [], res["no_data"]
    grund = list(res["unevaluable"])[0]
    assert "IKKE implementeret" in grund, grund


def test_enheden_baeres_i_ground_ref(isolated_runtime, monkeypatch):
    """ground_ref skal sige HVILKEN enhed observationen blev talt i.

    Uden det kan to kontrakter med forskellige enheder dele evidensidentitet, og
    dedup'en (noegle: source+ground_ref) ville blokere den ene som «duplikat» af den
    anden — selv om de talte hvert sit grundlag.
    """
    from core.services import central_model_meta as mm
    from core.runtime import db as rdb
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 20, "lat_n": 20, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 20, "lat_n": 20, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    monkeypatch.setattr(rdb, "recent_visible_runs", lambda **k: [
        _run("r1", "fast", "t1", "t2"), _run("r2", "slow", "t3", "t4")])
    res = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than"})
    assert "@per_run/rolling_run_count/equal_weight/v1" in res["cursor"], res["cursor"]


def test_forskellige_enheder_giver_forskellig_ground_ref(isolated_runtime, monkeypatch):
    """To kontrakter paa SAMME data men med FORSKELLIGE enheder maa ikke dele noegle.

    Enheden goeres midlertidigt implementeret her, fordi pointen er mekanismen: i det
    oejeblik en anden enhed kan maales, skal dens observation vaere sin EGEN — ikke en
    dublet af den andens. Maalt 4/11-2026 vender enheden dommen (16/16 per koersel mod
    0/16 per kald), saa de to observationer maa aldrig kollapse til én.
    """
    import copy
    from core.services import central_model_meta as mm
    from core.services import central_test_contract as tc
    from core.runtime import db as rdb
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": {"samples": 20, "lat_n": 20, "latency_ms": 100.0, "latency_median_ms": 100.0},
        "p/slow": {"samples": 20, "lat_n": 20, "latency_ms": 1000.0, "latency_median_ms": 1000.0},
    })
    monkeypatch.setattr(rdb, "recent_visible_runs", lambda **k: [
        _run("r1", "fast", "t1", "t2"), _run("r2", "slow", "t3", "t4")])

    a = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than"})

    spec = copy.deepcopy(tc.EVIDENCE_UNITS)
    try:
        tc.EVIDENCE_UNITS["per_model_call"]["implemented"] = True
        b = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than",
                                            "evidence_unit": "per_model_call",
                                            "min_samples": 1})
    finally:
        tc.EVIDENCE_UNITS.clear()
        tc.EVIDENCE_UNITS.update(spec)

    assert a["cursor"] != b["cursor"], (
        f"to enheder paa samme data delte evidensidentitet: {a['cursor']} vs {b['cursor']}")
    assert "@per_run/" in a["cursor"] and "@per_model_call/" in b["cursor"], (a, b)


# ── ENHEDEN SKAL VÆRE IMPLEMENTERET, IKKE BARE DEKLARERET (4/11-2026) ─────────────
#
# Målt samme dag: kontrakten deklarerede `per_run` + `pooled`, mens evaluatoren læste
# `latency_ms` — et pooled gennemsnit over hele vinduet — og gemte det som ÉT sample.
# Grundlaget rummede 288 run-enheder; dommen udnyttede 1. Testene herunder binder de to
# til hinanden: `min_samples` skal tælles i den deklarerede enhed, og estimanden skal
# følge vægtningen.


def _mock_agg(monkeypatch, fast, slow):
    """Mock med aggregatets FAKTISKE returform (lat_n + latency_median_ms)."""
    from core.services import central_model_meta as mm
    from core.runtime import db as rdb
    monkeypatch.setattr(mm, "aggregate_model_outcomes", lambda **k: {
        "p/fast": fast, "p/slow": slow})
    monkeypatch.setattr(rdb, "recent_visible_runs", lambda **k: [
        _run("r1", "fast", "t1", "t2"), _run("r2", "slow", "t3", "t4")])


def test_per_run_taeller_runs_ikke_vinduer(isolated_runtime, monkeypatch):
    """`per_run` skal give ÉN enhed pr. kørsel — ikke ét pr. vindue.

    Det er hele forskellen: 23 runs er 23 beviser, et pooled vindue er 1. Målt
    4/11-2026 gav samme grundlag `units=23` for per_run og `units=1` for
    aggregate_window.
    """
    _mock_agg(monkeypatch,
              {"samples": 40, "lat_n": 40, "latency_ms": 100.0, "latency_median_ms": 100.0},
              {"samples": 90, "lat_n": 90, "latency_ms": 1000.0, "latency_median_ms": 1000.0})
    a = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than", "evidence_unit": "per_run",
                                        "aggregation": "equal_weight", "min_samples": 5})
    b = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than", "evidence_unit": "aggregate_window",
                                        "aggregation": "pooled", "min_samples": 1})
    assert a["cursor"].startswith("40u:"), a
    assert b["cursor"].startswith("1u:"), b
    assert a["cursor"] != b["cursor"]


def test_per_run_taeller_kun_runs_med_latency(isolated_runtime, monkeypatch):
    """`samples` er antallet af RÆKKER; `lat_n` er dem der faktisk bar et latency-mål.

    En række uden `finished_at` er en kørsel, men ikke en observation af latency. Blev
    `samples` brugt som enhedstal, ville fem uafsluttede kørsler tælle som fem beviser
    om noget de ikke målte.
    """
    _mock_agg(monkeypatch,
              {"samples": 50, "lat_n": 3, "latency_ms": 100.0, "latency_median_ms": 100.0},
              {"samples": 80, "lat_n": 60, "latency_ms": 1000.0, "latency_median_ms": 1000.0})
    # 3 runs med latency < 5 krævede → ingen dom, selv om der er 50 rækker
    assert smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than", "evidence_unit": "per_run",
                                           "aggregation": "equal_weight",
                                           "min_samples": 5}) is None
    # sænkes kravet til 3, er der netop nok — og dommen falder
    res = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than", "evidence_unit": "per_run",
                                          "aggregation": "equal_weight", "min_samples": 3})
    assert res and res["cursor"].startswith("3u:"), res


def test_equal_weight_bruger_medianen_ikke_gennemsnittet(isolated_runtime, monkeypatch):
    """Enheden bestemmer ESTIMANDEN — ikke kun antallet.

    `pooled` er varighedsvægtning: et run på 30 minutter vejer 100x mere end et på 18
    sekunder, så ét hængt run kan flytte dommen for alle. Er `per_run` ægte, skal
    dommen følge medianen — hvor hvert run har præcis én stemme.
    """
    # mean siger «fast er 10x langsommere», median siger «fast er 10x hurtigere»
    _mock_agg(monkeypatch,
              {"samples": 20, "lat_n": 20, "latency_ms": 10_000.0, "latency_median_ms": 100.0},
              {"samples": 20, "lat_n": 20, "latency_ms": 1_000.0, "latency_median_ms": 1_000.0})
    res = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than", "evidence_unit": "per_run",
                                          "aggregation": "equal_weight", "min_samples": 5})
    assert res["supports"] is True, ("medianen siger fast er hurtigst — brugtes "
                                     f"gennemsnittet ville dommen vende: {res}")
    # modsat retning paa SAMME data: pooled gennemsnit skal give den modsatte dom
    pooled = smp._eval_contract_comparative({**_CONTRACT_BASE, "expected_relation": "less_than", "evidence_unit": "aggregate_window",
                                             "aggregation": "pooled", "min_samples": 1})
    assert pooled["falsifies"] is True, ("det pooled gennemsnit er domineret af det "
                                         f"haengte run: {pooled}")


def test_kontrakt_kan_ikke_blande_enhed_og_aggregering():
    """`per_run` + `pooled` er ikke to uafhaengige valg — de modsiger hinanden.

    `pooled` kollapser netop de runs `per_run` paastaar at taelle enkeltvis. Maalt
    4/11-2026 stod den levende kontrakt med praecis den kombination: den deklarerede
    288 enheder og udfoerte 1.
    """
    from core.services import central_test_contract as tc
    c = {**_CONTRACT_BASE, "expected_relation": "less_than", "evidence_unit": "per_run", "aggregation": "pooled"}
    ok, mangler = tc.validate(c)
    assert ok is False, "per_run + pooled skal afvises"
    assert any("kan ikke bære" in m for m in mangler), mangler


def test_aggregate_window_kan_ikke_kraeve_fem_samples():
    """Et pooled vindue er ÉT bevis — uanset hvor mange runs det summerer.

    Uden loftet ville en saadan kontrakt staa som «mangler data» for evigt i stedet for
    at blive afvist ved oprettelsen.
    """
    from core.services import central_test_contract as tc
    ok, mangler = tc.validate({**_CONTRACT_BASE, "expected_relation": "less_than", "evidence_unit": "aggregate_window",
                               "aggregation": "pooled", "min_samples": 5})
    assert ok is False
    assert any("overstiger" in m for m in mangler), mangler
    ok1, _ = tc.validate({**_CONTRACT_BASE, "expected_relation": "less_than", "evidence_unit": "aggregate_window",
                          "aggregation": "pooled", "min_samples": 1})
    assert ok1 is True
