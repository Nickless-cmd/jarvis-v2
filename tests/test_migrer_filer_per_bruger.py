"""Migreringen af de gamle fælles filer (4/10-2026).

Testene måler de tre ting der kan gå galt ved en flytning: at noget forsvinder,
at noget bliver overskrevet, og at den ikke kan køres to gange.
"""
from __future__ import annotations

import pytest

from scripts.migrer_filer_per_bruger import migrer


@pytest.fixture
def hjem(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    f = tmp_path / "files"
    f.mkdir()
    (f / "rapport.pdf").write_bytes(b"%PDF indhold")
    (f / "noter.md").write_text("mine noter")
    for d in ("phase5", "icons"):
        (f / d).mkdir()
        (f / d / "data.jsonl").write_text("eksperiment")
    return tmp_path


def test_toerloeb_flytter_INTET(hjem, capsys):
    assert migrer(udfoer=False, ejer_ws="bjorn") == 0
    assert (hjem / "files" / "rapport.pdf").exists()
    assert not (hjem / "files" / "u").exists()
    assert "TOERLOEB" in capsys.readouterr().out


def test_filerne_flyttes_og_indholdet_overlever(hjem):
    assert migrer(udfoer=True, ejer_ws="bjorn") == 0
    ny = hjem / "files" / "u" / "bjorn"
    assert (ny / "rapport.pdf").read_bytes() == b"%PDF indhold"
    assert (ny / "noter.md").read_text() == "mine noter"
    assert not (hjem / "files" / "rapport.pdf").exists()


def test_undermapperne_roeres_IKKE(hjem):
    """De syv er eksperiment-output som `scripts/phase*` forventer hvor de er.
    Ruten kunne aldrig naa dem."""
    migrer(udfoer=True, ejer_ws="bjorn")
    assert (hjem / "files" / "phase5" / "data.jsonl").read_text() == "eksperiment"
    assert (hjem / "files" / "icons" / "data.jsonl").exists()
    assert not (hjem / "files" / "u" / "bjorn" / "phase5").exists()


def test_den_kan_koeres_to_gange(hjem):
    assert migrer(udfoer=True, ejer_ws="bjorn") == 0
    assert migrer(udfoer=True, ejer_ws="bjorn") == 0
    assert (hjem / "files" / "u" / "bjorn" / "rapport.pdf").read_bytes() == b"%PDF indhold"


def test_en_AFVIGENDE_dublet_overskrives_ALDRIG(hjem, capsys):
    """En overskrivning her er datatab, ikke en migrering."""
    ny = hjem / "files" / "u" / "bjorn"
    ny.mkdir(parents=True)
    (ny / "rapport.pdf").write_bytes(b"%PDF NYERE udgave")
    assert migrer(udfoer=True, ejer_ws="bjorn") == 0
    assert (ny / "rapport.pdf").read_bytes() == b"%PDF NYERE udgave"
    assert (hjem / "files" / "rapport.pdf").exists(), "kilden blev slettet"
    assert "AFVIGER" in capsys.readouterr().out


def test_en_IDENTISK_dublet_rydder_kilden_op(hjem):
    ny = hjem / "files" / "u" / "bjorn"
    ny.mkdir(parents=True)
    (ny / "rapport.pdf").write_bytes(b"%PDF indhold")
    migrer(udfoer=True, ejer_ws="bjorn")
    assert not (hjem / "files" / "rapport.pdf").exists()


def test_uden_ejer_flyttes_INTET(hjem, monkeypatch, capsys):
    import scripts.migrer_filer_per_bruger as m
    monkeypatch.setattr(m, "find_ejer", lambda: "")
    assert migrer(udfoer=True) == 1
    assert (hjem / "files" / "rapport.pdf").exists()
    assert "intet flyttet" in capsys.readouterr().out
