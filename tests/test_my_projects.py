"""Kontakten under mine egne baggrundsprojekter.

De fire projekter (grid-bot, dealwork-worker, superteam-scanner,
toku-poller) startede igen efter hver genstart, fordi boot og vagthunden
begge spawner dem. Bjoern bad om at det stoppede — uden at definitionerne
forsvandt, saa de kan taendes igen.

Det der kan gaa galt uden at nogen ser det:
  1. kontakten sidder kun paa boot, saa vagthunden starter dem 4 timer senere
  2. kontakten sidder kun paa vagthunden, saa naeste genstart starter dem
  3. standarden vender, saa alle andre installationer mister deres projekter
"""
import json

import pytest

from core.services import my_projects


class _Optaeller:
    """Taeller spawn-kald. Et kald her = en proces der starter i virkeligheden."""

    def __init__(self) -> None:
        self.spawn_kald: list[str] = []

    def spawn_process(self, *, name: str, command: str, cwd: str, **kw: object) -> dict:
        self.spawn_kald.append(name)
        return {"status": "ok", "process": {"pid": 4242}}

    def list_processes(self, include_stopped: bool = False) -> dict:
        return {"processes": []}          # ingen koerer — alt vil blive startet


@pytest.fixture()
def optaeller(monkeypatch: pytest.MonkeyPatch) -> _Optaeller:
    t = _Optaeller()
    monkeypatch.setattr(my_projects, "_ps", t)
    return t


def _saet_kontakt(monkeypatch: pytest.MonkeyPatch, vaerdi: bool) -> None:
    monkeypatch.setattr(my_projects, "projekter_slaaet_til", lambda: vaerdi)


def test_boot_starter_intet_naar_kontakten_er_slaaet_fra(monkeypatch, optaeller):
    _saet_kontakt(monkeypatch, False)
    svar = my_projects.ensure_my_projects_running()
    assert optaeller.spawn_kald == []
    assert svar["slaaet_fra"] is True
    assert svar["spawned"] == []


def test_vagthunden_genstarter_intet_naar_kontakten_er_slaaet_fra(monkeypatch, optaeller):
    _saet_kontakt(monkeypatch, False)
    svar = my_projects.tick_my_projects_watchdog()
    assert optaeller.spawn_kald == []
    assert svar["restarted_count"] == 0
    assert svar["slaaet_fra"] is True


def test_kontakten_slaaet_til_starter_stadig_alle_fire(monkeypatch, optaeller):
    """Modstykket: kontakten maa ikke sidde fast i slukket."""
    _saet_kontakt(monkeypatch, True)
    my_projects.ensure_my_projects_running()
    assert optaeller.spawn_kald == [p["name"] for p in my_projects.PROJECTS]
    assert len(optaeller.spawn_kald) == 4


def test_vagthunden_slaaet_til_genstarter_de_doede(monkeypatch, optaeller):
    _saet_kontakt(monkeypatch, True)
    svar = my_projects.tick_my_projects_watchdog()
    assert svar["restarted_count"] == 4
    assert optaeller.spawn_kald == [p["name"] for p in my_projects.PROJECTS]


def test_kontakten_laeses_fra_runtime_json(monkeypatch, tmp_path):
    """Hele vejen: filen paa disken -> load_settings -> kontakten."""
    import core.runtime.settings as settings

    fil = tmp_path / "runtime.json"
    fil.write_text(json.dumps({"my_projects_enabled": False}), encoding="utf-8")
    monkeypatch.setattr(settings, "SETTINGS_FILE", fil)
    assert my_projects.projekter_slaaet_til() is False

    fil.write_text(json.dumps({"my_projects_enabled": True}), encoding="utf-8")
    assert my_projects.projekter_slaaet_til() is True


def test_standarden_er_taendt_saa_ingen_mister_sine_projekter(monkeypatch, tmp_path):
    import core.runtime.settings as settings

    fil = tmp_path / "runtime.json"
    fil.write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setattr(settings, "SETTINGS_FILE", fil)
    assert my_projects.projekter_slaaet_til() is True


def test_definitionerne_bliver_staaende(monkeypatch):
    """Slukket betyder 'starter ikke', ikke 'findes ikke'.

    Bjoern skal kunne taende dem igen uden at nogen skal skrive dem op paa ny.
    """
    _saet_kontakt(monkeypatch, False)
    my_projects.ensure_my_projects_running()
    navne = [p["name"] for p in my_projects.PROJECTS]
    assert navne == ["grid-bot", "dealwork-worker", "superteam-scanner", "toku-poller"]
