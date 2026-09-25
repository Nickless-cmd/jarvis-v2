"""Ændringerne var usynlige for den proces der viser dem.

`_recent` lå i en `deque` i modulet. `jarvis-api` og `jarvis-runtime` kører
samme kode i hver sin proces, men kun runtime tikker — api'ens kopi var derfor
tom, og fladen sagde «ingen ændringer endnu» uanset hvad der var sket.
Livstegnet stod på `_first_scan_done`, som af samme grund altid var falsk dér.

Fingeraftrykket deles IKKE. Det besvarer et andet spørgsmål — «har JEG en
grundlinje?» — er 16.485 poster, og at skrive ~1,3 MB ved hvert tik ville være
dyrt uden at hjælpe nogen. Værre: deltes `_first_scan_done` med, ville første
sweep efter en genstart se alle 16.485 filer som nye og melde dem «created».
"""
from __future__ import annotations

import pytest

import core.services.file_watch_daemon as F


@pytest.fixture(autouse=True)
def _tom_log():
    F.reset_file_watch_state()
    yield
    F.reset_file_watch_state()


def test_et_tomt_men_koerende_modul_er_LEVENDE():
    flade = F.build_file_watch_surface()
    assert flade["active"] is True


def test_aendringerne_overlever_at_modulet_indlaeses_forfra(tmp_path, monkeypatch):
    import importlib

    fil = tmp_path / "noget.md"
    fil.write_text("hej", encoding="utf-8")
    monkeypatch.setattr(F, "_watched_roots", lambda: [tmp_path])

    F.tick(30.0)              # første sweep er tavs — den bygger grundlinjen
    assert F.recent_changes() == []

    fil.write_text("hej igen", encoding="utf-8")
    F.tick(30.0)
    assert len(F.recent_changes()) == 1

    frisk = importlib.reload(F)
    try:
        assert len(frisk.recent_changes()) == 1
    finally:
        frisk.reset_file_watch_state()
        importlib.reload(F)


def test_fingeraftrykket_deles_IKKE(tmp_path, monkeypatch):
    """Grundlinjen er per proces og skal blive det.

    Deltes den, ville et modul indlæst forfra tro at den allerede HAVDE en
    grundlinje — og melde hver eneste fil som ny.
    """
    import importlib

    (tmp_path / "en.md").write_text("a", encoding="utf-8")
    (tmp_path / "to.md").write_text("b", encoding="utf-8")
    monkeypatch.setattr(F, "_watched_roots", lambda: [tmp_path])

    F.tick(30.0)
    assert F.build_file_watch_surface()["tracked_files"] == 2

    frisk = importlib.reload(F)
    try:
        monkeypatch.setattr(frisk, "_watched_roots", lambda: [tmp_path])
        assert frisk._first_scan_done is False, "grundlinjen blev delt"
        # Første sweep i den nye proces er tavs FREM FOR at melde to «created».
        ud = frisk.tick(30.0)
        assert ud["changes"] == 0
        assert len(frisk.recent_changes()) == 0
    finally:
        frisk.reset_file_watch_state()
        importlib.reload(F)


def test_et_sweep_uden_aendringer_skriver_ikke(tmp_path, monkeypatch):
    """16.485 filer scannes hvert tik; en skrivning uden nyt er ren støj."""
    (tmp_path / "en.md").write_text("a", encoding="utf-8")
    monkeypatch.setattr(F, "_watched_roots", lambda: [tmp_path])
    F.tick(30.0)

    skrivninger: list[int] = []
    monkeypatch.setattr(F, "_gem", lambda: skrivninger.append(1))

    F.tick(30.0)
    assert skrivninger == []
