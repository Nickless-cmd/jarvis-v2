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


@pytest.mark.parametrize("felt", ["subject", "comparator", "expected_relation", "min_samples"])
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
