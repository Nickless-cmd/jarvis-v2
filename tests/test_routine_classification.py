"""Klassifikationens REGLER — rene funktioner, ingen DB.

Persisteringen (at valget når frem til `delivery_policy['classification']`)
testes i `tests/routines/test_classification.py`, fordi den kræver en rutine.
Her måles kun reglen: hvad betyder et valg.
"""
from __future__ import annotations

import pytest

from core.services.routine_classification import classify_routine


def test_tomme_vaerdier_giver_bagudkompatibel_standard():
    k = classify_routine()
    assert k.execution_mode.value == "background"
    assert k.importance.value == "normal"
    assert k.requires_handling is False
    assert k.blocks_mutations is False
    assert k.highlights is False
    assert k.cool_down_minutes == 0


def test_none_giver_samme_standard_som_tom_streng():
    assert classify_routine(execution_mode=None, importance=None).as_dict() == (
        classify_routine().as_dict()
    )


def test_session_mode_kraever_cool_down():
    k = classify_routine(execution_mode="session")
    assert k.execution_mode.value == "session"
    # Bjørn: en rutine må ikke forurene en kørende session.
    assert k.cool_down_minutes == 5


def test_background_har_ingen_cool_down():
    assert classify_routine(execution_mode="background").cool_down_minutes == 0


def test_high_fremhaeves_men_blokerer_ikke():
    k = classify_routine(importance="high")
    assert k.requires_handling is True
    assert k.highlights is True
    # En påmindelse der ikke er akut må ikke kunne låse en fil-skrivning.
    assert k.blocks_mutations is False


def test_kun_critical_blokerer():
    k = classify_routine(importance="critical")
    assert k.requires_handling is True
    assert k.blocks_mutations is True


def test_low_og_normal_kraever_ingen_handling():
    for vaerdi in ("low", "normal"):
        k = classify_routine(importance=vaerdi)
        assert k.requires_handling is False, vaerdi
        assert k.highlights is False, vaerdi


def test_ukendt_execution_mode_fejler_hoejt():
    # Fail-closed: en tastefejl må ikke stille blive «background».
    with pytest.raises(ValueError, match="execution_mode"):
        classify_routine(execution_mode="baggrund")


def test_ukendt_importance_fejler_hoejt():
    with pytest.raises(ValueError, match="importance"):
        classify_routine(importance="vigtig")


def test_case_og_whitespace_tolereres():
    k = classify_routine(execution_mode="  SESSION  ", importance=" HIGH ")
    assert k.execution_mode.value == "session"
    assert k.importance.value == "high"


def test_as_dict_er_den_persisterede_form():
    # Læserne (runner, indbakke, API) skal ikke genskabe reglerne.
    assert set(classify_routine().as_dict()) == {
        "execution_mode", "importance", "requires_handling",
        "blocks_mutations", "highlights", "cool_down_minutes",
    }
