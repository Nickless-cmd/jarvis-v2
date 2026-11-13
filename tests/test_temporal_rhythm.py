"""Rytmen var usynlig for den proces der viser den.

`_tick_history` og `_baseline_samples` lå i modul-globaler. `jarvis-api` og
`jarvis-runtime` kører samme kode i hver sin proces, men kun runtime tikker —
api'ens kopi var derfor tom, og fladen sagde «Endnu ingen tempo-sampling»
uanset hvor længe han havde levet. Genstart slettede desuden både historik og
baseline.

Livstegnet stod samtidig på `active: False` i den tomme gren.
`cognitive_architecture_surface` læser nøglen som «systemet lever», så et
modul der rigtigt meldte «ingen sampling endnu» meldte sig dødt.
"""
from __future__ import annotations

import pytest

import core.services.temporal_rhythm as R


@pytest.fixture(autouse=True)
def _tom_rytme(monkeypatch):
    """Skærm-mappen fra conftest er sessions-bred, så nøglen skal tømmes.

    Mood-oscillatoren kobles fra: rytmen skal måles, ikke dens bivirkning.
    """
    monkeypatch.setattr("core.services.mood_oscillator.apply_bump",
                        lambda *a, **k: None)
    R.reset_temporal_rhythm()
    yield
    R.reset_temporal_rhythm()


def test_et_tomt_men_koerende_modul_er_LEVENDE():
    flade = R.build_temporal_rhythm_surface()
    assert flade["active"] is True
    assert "Endnu ingen" in flade["summary"]


def test_rytmen_overlever_at_modulet_indlaeses_forfra():
    """KERNEN. En `deque` i modulet døde med processen."""
    import importlib

    R.tick(551.0)

    frisk = importlib.reload(R)
    try:
        flade = frisk.build_temporal_rhythm_surface()
        assert flade["samples"] == 1
        assert "Puls=" in flade["summary"]
    finally:
        frisk.reset_temporal_rhythm()
        importlib.reload(R)


def test_en_anden_proces_ser_tikket_uden_at_have_tikket_selv():
    """Det var den målte fejl: api'en læste sin egen tomme kopi."""
    import importlib

    anden = importlib.reload(R)
    assert "Endnu ingen" in anden.build_temporal_rhythm_surface()["summary"]

    R.tick(551.0)

    try:
        # Ingen genindlæsning — kun `_synk()` på mtime.
        assert anden.build_temporal_rhythm_surface()["samples"] == 1
    finally:
        anden.reset_temporal_rhythm()
        importlib.reload(R)


def test_historikken_er_afgraenset():
    for _ in range(R._HISTORY_MAX + 15):
        R.tick(551.0)
    assert R.build_temporal_rhythm_surface()["samples"] == R._HISTORY_MAX


def test_baseline_kraever_fem_proever_foer_den_vises():
    """Et gennemsnit af to målinger er ikke en baseline."""
    for _ in range(4):
        R.tick(551.0)
    assert R.build_temporal_rhythm_surface()["baseline_pulse"] is None

    R.tick(551.0)
    assert R.build_temporal_rhythm_surface()["baseline_pulse"] is not None


def test_nyeste_foerst():
    R.tick(551.0)
    foerste = R.get_current_rhythm()["at"]
    R.tick(551.0)
    assert R.get_current_rhythm()["at"] >= foerste
    assert R.build_temporal_rhythm_surface()["samples"] == 2


def test_et_lager_der_ikke_kan_skrives_vaelter_ikke_tikket(monkeypatch):
    """Tikket ligger i hjerteslaget. En fejlet skrivning må ikke standse det.

    Patchen sidder på `save_json_strict`, ikke på `save_json`: det er DÉR en
    rigtig diskfejl opstår, og `save_json` er selv-sikker om den. Patchede man
    `save_json` ville man måle sit eget opspil — og fixturens oprydning ville
    vælte med.
    """
    monkeypatch.setattr(
        R.state_store, "save_json_strict",
        lambda *a, **k: (_ for _ in ()).throw(OSError("disken er fuld")))
    snap = R.tick(551.0)
    assert snap["pulse_rate"] > 0
    assert snap["subjective_time_pressure"]


def test_aktiviteten_kan_faktisk_naa_ind_i_pulsen(monkeypatch):
    """VAGTEN: `_recent_tool_calls_per_min` kaldte en funktion der ikke fandtes.

    (13/11-2026) Kaldet lå i `try/except → 0.0`, så `tool_rate` var
    STRUKTURELT nul. Pulsen kunne derfor ikke se at der blev arbejdet: målt i
    produktionen stod den på 0.3 (»breathing«) midt i en aften med tusindvis
    af handlinger, og DIASTOLE fordoblede hver cooldown i hele ensemblet.

    Testen beviser at tallet KAN komme igennem — ikke at det gør det lige nu.
    """
    from core.runtime import db

    monkeypatch.setattr(
        db, "recent_heartbeat_outcome_counts",
        lambda *, minutes=30: {"ok": 20, "error": 1},
    )
    assert R._recent_tool_calls_per_min() == pytest.approx(4.2)


def test_manglende_udfaldstaelling_giver_nul_ikke_gaet(monkeypatch):
    """Falder kilden væk, er svaret nul — men det er et FRAVÆR af data,
    ikke en påstand om at der ikke skete noget. Derfor må pulsen ikke
    rejse, og funktionen må ikke kaste."""
    from core.runtime import db

    def _braender(*, minutes=30):
        raise RuntimeError("tabellen er væk")

    monkeypatch.setattr(db, "recent_heartbeat_outcome_counts", _braender)
    assert R._recent_tool_calls_per_min() == 0.0
