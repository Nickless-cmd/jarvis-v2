"""Tests for core/services/central_test_contract.py — den bindende testkontrakt.

Maalt 4/11-2026: 0 af 505 aktive hypoteser bar en valideret kontrakt. Retningen laa
hardkodet i family-konventionen "latency:W>L" og i et if/else, saa en hypotese der
paastod det MODSATTE ikke kunne udtrykkes. Kontrakten flytter retningen ind i
hypotesens egen praeregistrering.

Testene daekker BAADE den strukturelle og den semantiske kompatibilitet: at felterne
findes er ikke nok — evaluatoren skal ogsaa vaere den type kontrakten kraever, og
tidsbasen skal vaere en infrastrukturen faktisk baerer.
"""
from __future__ import annotations

import pytest

from core.services import central_test_contract as tc


def _gyldig(**over):
    c = {
        "schema_version": 1,
        "contract_type": "comparative_latency",
        "evaluator": "model_meta_persistence",
        "evaluator_version": 1,
        "subject": "p/fast",
        "comparator": "p/slow",
        "metric": "latency_ms",
        "expected_relation": "less_than",
        "min_samples": 5,
        "time_basis": "ingestion_time",
        "evaluation_policy": "latency_margin_v1",
        "policy_version": 1,
        # Evidens-specifikationen: hvad tælles, hvordan vælges det, hvordan vægtes det.
        "evidence_unit": "per_run",
        "window_semantics": "rolling_run_count",
        "aggregation": "median",
    }
    c.update(over)
    return c


def test_gyldig_kontrakt_accepteres():
    ok, missing = tc.validate(_gyldig())
    assert ok is True and missing == []


@pytest.mark.parametrize("relation", ["less_than", "greater_than"])
def test_begge_retninger_accepteres(relation):
    """Retningen ER kontrakten. Begge sider skal kunne udtrykkes — det var hele pointen."""
    ok, missing = tc.validate(_gyldig(expected_relation=relation))
    assert ok is True, missing


def test_ukendt_retning_afvises():
    ok, missing = tc.validate(_gyldig(expected_relation="cirka_lige"))
    assert ok is False
    assert any("expected_relation" in m for m in missing), missing


def test_ukendt_contract_type_afvises():
    """En kontrakttype Centralen ikke kan efterproeve maa ikke accepteres."""
    ok, missing = tc.validate(_gyldig(contract_type="opfundet_type"))
    assert ok is False
    assert any("contract_type" in m for m in missing), missing


@pytest.mark.parametrize("felt", ["subject", "comparator", "expected_relation", "min_samples",
                                  "evidence_unit", "window_semantics", "aggregation"])
def test_manglende_paakraevet_felt_afvises(felt):
    c = _gyldig()
    c.pop(felt)
    ok, missing = tc.validate(c)
    assert ok is False
    assert any(felt in m for m in missing), missing


def test_tom_streng_taeller_som_manglende():
    """Et felt der ER til stede men tomt er ikke en kontrakt."""
    ok, missing = tc.validate(_gyldig(subject="   "))
    assert ok is False
    assert any("subject" in m for m in missing), missing


def test_forkert_evaluator_afvises_semantisk():
    """Strukturelt gyldigt, semantisk forkert: typen kraever sin egen evaluator.

    Uden dette kunne en model pege paa en vilkaarlig evaluator blot ved at skrive
    et gyldigt JSON-objekt — og kontrakten ville se valideret ud.
    """
    ok, missing = tc.validate(_gyldig(evaluator="stance_persistence"))
    assert ok is False
    assert any("model_meta_persistence" in m for m in missing), missing


def test_forkert_evaluator_version_afvises():
    """Versionen pinnes: aendrer domsreglen sig, skal det vaere en NY version."""
    ok, missing = tc.validate(_gyldig(evaluator_version=2))
    assert ok is False
    assert any("evaluator_version" in m for m in missing), missing


def test_event_time_afvises_som_tidsbasis():
    """Infrastrukturen baerer ikke event-time.

    `central_hypothesis_samples.created_at` saettes ved indsaettelse, og event-tid
    findes kun indirekte via ground_ref. En kontrakt der paastod `event_time` ville
    lyve om praecis det punkt hvor dommen beregnes.
    """
    ok, missing = tc.validate(_gyldig(time_basis="event_time"))
    assert ok is False
    assert any("event_time" in m for m in missing), missing


def test_ingestion_time_er_standard_naar_feltet_mangler():
    c = _gyldig()
    c.pop("time_basis")
    ok, missing = tc.validate(c)
    assert ok is True, missing


def test_min_samples_skal_vaere_positiv():
    ok, missing = tc.validate(_gyldig(min_samples=0))
    assert ok is False
    assert any("min_samples" in m for m in missing), missing


def test_min_samples_skal_vaere_et_tal():
    ok, missing = tc.validate(_gyldig(min_samples="mange"))
    assert ok is False
    assert any("min_samples" in m for m in missing), missing


def test_schema_version_skal_matchez():
    ok, missing = tc.validate(_gyldig(schema_version=99))
    assert ok is False
    assert any("schema_version" in m for m in missing), missing


@pytest.mark.parametrize("vaerdi", [None, {}, [], "en-streng", 42])
def test_ikke_objekt_afvises(vaerdi):
    ok, missing = tc.validate(vaerdi)
    assert ok is False and missing


def test_relation_of_og_subject_of():
    c = _gyldig(expected_relation="greater_than")
    assert tc.relation_of(c) == "greater_than"
    assert tc.subject_of(c) == ("p/fast", "p/slow")
    assert tc.evaluator_of(c) == "model_meta_persistence"


def test_relation_of_taaler_manglende_felt():
    """Self-safe: en tom kontrakt maa ikke kaste, blot returnere tom retning."""
    assert tc.relation_of({}) == ""


def test_kontrakt_uden_beslutningskriterium_afvises():
    """En evaluator maa ikke acceptere en kontrakt hvis beslutningskriterier mangler.

    Uden en pinnet politik er kontrakten deklarativ mens dommen er imperativ — og de
    to kan glide fra hinanden uden at nogen roerer hypotesen.
    """
    c = _gyldig()
    c.pop("evaluation_policy")
    ok, missing = tc.validate(c)
    assert ok is False
    assert any("evaluation_policy" in m for m in missing), missing


def test_ukendt_politik_afvises():
    ok, missing = tc.validate(_gyldig(evaluation_policy="opfundet_v9"))
    assert ok is False
    assert any("evaluation_policy" in m for m in missing), missing


def test_politik_version_pinnes():
    """AEndrer domsreglen sig, skal det vaere en NY politik — ikke en stiltiende aendring."""
    ok, missing = tc.validate(_gyldig(policy_version=99))
    assert ok is False
    assert any("policy_version" in m for m in missing), missing


def test_policy_of_returnerer_beslutningsreglen():
    """Evaluatoren skal kunne laese reglen UDEN at kende modul-konstanter."""
    pol = tc.policy_of(_gyldig())
    assert pol is not None
    assert pol["version"] == 1
    assert pol["support_ratio"] == 1.25
    assert pol["contradict_ratio"] == 1.0


def test_policy_of_ukendt_giver_none():
    """Self-safe: en ukendt politik maa ikke give en tilfaeldig standardregel."""
    assert tc.policy_of({"evaluation_policy": "findes_ikke"}) is None
    assert tc.policy_of({}) is None


def test_describe_viser_retningen():
    """Retningen skal vaere laesbar uden at aabne JSON — ellers kan den ikke revideres."""
    assert "p/fast < p/slow" in tc.describe(_gyldig(expected_relation="less_than"))
    assert "p/fast > p/slow" in tc.describe(_gyldig(expected_relation="greater_than"))


# ── Evidens-specifikationen: hvad tælles ──────────────────────────────────────
#
# Målt 4/11-2026: kontrakten bandt retningen, politikken og evaluatoren — men ikke
# ENHEDEN. `min_samples: 5` talte derfor fem kald til `aggregate_model_outcomes()`,
# ikke fem uafhængige observationer; de fem kald læste stort set samme rullende
# vindue (97,8 % overlap). Testene her binder enheden til kontrakten.


def test_kontrakt_uden_enhed_afvises():
    """En kontrakt der ikke siger hvad den tæller har ingen dom at afsige.

    Beskeden skal sige at feltet MANGLER — ikke blot at dets vaerdi er ukendt. Ellers
    kan en fremtidig omlaegning af `required`-listen fjerne det ene af to lag uden at
    nogen test opdager det (maalt 4/11-2026: mutationen bed ikke, fordi register-
    loekken dækkede over det).
    """
    c = _gyldig()
    c.pop("evidence_unit")
    ok, missing = tc.validate(c)
    assert ok is False
    assert any("evidence_unit" in m and "mangler" in m for m in missing), missing


def test_ikke_implementeret_enhed_afvises_med_grund():
    """`per_model_call` er REGISTRERET men IKKE implementeret — og det skal siges.

    `costs` bærer `created_at` pr. ledger-række, men intet per-kald start/slut, så
    ægte per-kald-latency kan ikke måles. En kontrakt der påstod det ville lyve om
    præcis det punkt hvor dommen beregnes — samme fejl som `event_time`-tidsbasen.
    Afvisningen skal naevne HVORFOR, ikke bare at feltet er ugyldigt.
    """
    ok, missing = tc.validate(_gyldig(evidence_unit="per_model_call"))
    assert ok is False
    grund = next((m for m in missing if "per_model_call" in m), "")
    assert "IKKE implementeret" in grund, missing
    assert "costs" in grund, grund


def test_ukendt_enhed_afvises():
    ok, missing = tc.validate(_gyldig(evidence_unit="per_stemning"))
    assert ok is False
    assert any("evidence_unit" in m for m in missing), missing


def test_ikke_implementeret_vindue_afvises():
    """`fixed_duration` er den semantik der MANGLER — den maa ikke kunne påstaas."""
    ok, missing = tc.validate(_gyldig(window_semantics="fixed_duration"))
    assert ok is False
    assert any("window_semantics" in m for m in missing), missing


def test_ikke_implementeret_aggregering_afvises():
    ok, missing = tc.validate(_gyldig(aggregation="per_period"))
    assert ok is False
    assert any("aggregation" in m for m in missing), missing


def test_evidence_version_pinnes():
    ok, missing = tc.validate(_gyldig(evidence_version=99))
    assert ok is False
    assert any("evidence_version" in m for m in missing), missing


def test_evidence_of_returnerer_specifikationen():
    """Evaluatoren skal kunne laese enheden UDEN at kende modul-konstanter."""
    ev = tc.evidence_of(_gyldig())
    assert ev is not None
    assert ev["unit"] == "per_run"
    assert ev["window"] == "rolling_run_count"
    assert ev["aggregation"] == "median"
    assert ev["version"] == tc.EVIDENCE_SPEC_VERSION
    assert ev["source"] == "visible_runs"


def test_evidence_of_ved_ikke_implementeret_giver_none():
    """Self-safe: en enhed Centralen ikke kan maale maa ikke give en tilfaeldig dom."""
    assert tc.evidence_of(_gyldig(evidence_unit="per_model_call")) is None
    assert tc.evidence_of(_gyldig(evidence_unit="findes_ikke")) is None
    assert tc.evidence_of({}) is None


def test_signaturen_foelger_enheden_ikke_en_konstant():
    """To kontrakter med FORSKELLIGE enheder maa ikke dele evidensidentitet.

    Uden dette ville dedup'en i `record_governed_sample` (noegle: source+ground_ref)
    blokere den ene kontrakts observation som «duplikat» af den andens — selv om de
    talte hvert sit grundlag. Signaturen testes ved at goere en anden vindues-semantik
    implementeret: saa SKAL signaturen aendre sig.
    """
    base = tc.evidence_signature(_gyldig())
    assert base == "per_run/rolling_run_count/median/v1", base
    # En kontrakt uden gyldig enhed har ingen signatur — ikke en tom der kollapser alle.
    assert tc.evidence_signature(_gyldig(window_semantics="fixed_duration")) == ""

    import copy
    spec = copy.deepcopy(tc.WINDOW_SEMANTICS)
    try:
        tc.WINDOW_SEMANTICS["fixed_duration"]["implemented"] = True
        aendret = tc.evidence_signature(_gyldig(window_semantics="fixed_duration"))
        assert aendret == "per_run/fixed_duration/median/v1", aendret
        assert aendret != base, "signaturen skal foege vindues-semantikken"
    finally:
        tc.WINDOW_SEMANTICS.clear()
        tc.WINDOW_SEMANTICS.update(spec)


def test_describe_viser_enheden():
    """En dom uden sin enhed kan ikke revideres — enheden skal staa i den laesbare form."""
    tekst = tc.describe(_gyldig())
    assert "per_run/rolling_run_count/median" in tekst, tekst
    # Og en kontrakt UDEN enhed skal sige det hoejt i stedet for at se gyldig ud.
    c = _gyldig()
    c.pop("evidence_unit")
    assert "UDEN enhed" in tc.describe(c)
