"""Flytningen fra `shared/runtime/` til `state_store` må ikke tabe eller
overskrive noget.

Skrevet 25/9-2026. Skriptet køres én gang per maskine, og den eneste chance
for at opdage en fejl er FØR den kører — bagefter er den gamle fil ganske vist
i behold, men tjenesterne læser den ikke længere.
"""
from __future__ import annotations

import json

import pytest

from core.runtime import state_store
import scripts.migrer_shared_runtime_til_state_store as M


@pytest.fixture(autouse=True)
def _tomme_noegler():
    """Hver test starter med tomme state_store-nøgler.

    Skærm-mappen fra conftest er SESSIONS-bred, så `tests/test_body_memory.py`
    og de fem andre når at skrive der i en fuld kørsel. Uden denne fixture
    fandt migreringen «allerede indhold» og sprang over — og testen målte
    rækkefølgen af testfiler frem for skriptet. (Målt i fuld suite 25/9-2026:
    grøn alene, rød sammen med de andre.)
    """
    for navn in M.MODULER:
        state_store.save_json(navn, None)
    yield


@pytest.fixture
def _gammel(tmp_path, monkeypatch):
    """Peg `shared_dir()` mod en tmp-mappe. `state_store` er allerede skærmet
    af conftest' autouse-fixture."""
    (tmp_path / "runtime").mkdir(parents=True)
    monkeypatch.setattr(M, "shared_dir", lambda: tmp_path)

    def skriv(navn, data):
        (tmp_path / "runtime" / f"{navn}.json").write_text(
            json.dumps(data), encoding="utf-8")
    return skriv


def test_indholdet_kommer_ordret_med(_gammel):
    poster = [{"sensation": "varm", "intensity": 0.7}, {"sensation": "tung"}]
    _gammel("body_memory", poster)

    status, _ = M.flyt("body_memory", toerloeb=False)

    assert status == "flyttet"
    assert state_store.load_json("body_memory", None) == poster


def test_en_fil_der_allerede_har_indhold_roeres_ikke(_gammel):
    """Koeres skriptet EFTER genstarten, staar der allerede friske data."""
    _gammel("ghost_networks", [{"node_id": "gammel"}])
    state_store.save_json("ghost_networks", [{"node_id": "ny"}])

    status, hvorfor = M.flyt("ghost_networks", toerloeb=False)

    assert status == "sprunget" and "allerede indhold" in hvorfor
    assert state_store.load_json("ghost_networks", None) == [{"node_id": "ny"}]


def test_en_TOM_state_fil_maa_gerne_overskrives(_gammel):
    """Genstartede tjenesten foer flytningen, skrev den en tom fil. Den maa
    ikke staa i vejen for de rigtige data."""
    _gammel("memory_tattoos", [{"event": "noget der praegede en dag"}])
    state_store.save_json("memory_tattoos", [])

    status, _ = M.flyt("memory_tattoos", toerloeb=False)

    assert status == "flyttet"
    assert len(state_store.load_json("memory_tattoos", [])) == 1


def test_toerloeb_skriver_ingenting(_gammel):
    _gammel("text_resonance", [{"emotional_tone": "warm"}])

    status, _ = M.flyt("text_resonance", toerloeb=True)

    assert status == "ville flytte"
    assert state_store.load_json("text_resonance", None) is None


def test_en_oedelagt_gammel_fil_meldes_som_fejl_ikke_som_succes(tmp_path, monkeypatch):
    """En stille «sprunget» ville se ud som om der intet var at flytte."""
    (tmp_path / "runtime").mkdir(parents=True)
    monkeypatch.setattr(M, "shared_dir", lambda: tmp_path)
    (tmp_path / "runtime" / "decision_ghosts.json").write_text(
        "{ikke gyldig json", encoding="utf-8")

    status, hvorfor = M.flyt("decision_ghosts", toerloeb=False)

    assert status == "fejl" and "læses" in hvorfor


def test_alle_seks_moduler_staar_i_listen():
    """Glemmes ét, flyttes dets data aldrig — og ingen opdager det."""
    assert set(M.MODULER) == {
        "body_memory", "forgetting_curve", "decision_ghosts",
        "memory_tattoos", "ghost_networks", "text_resonance",
    }
