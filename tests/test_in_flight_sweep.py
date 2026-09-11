"""Nedluknings-sweepen stemplede fejlede ture med en grund der var falsk om dem.

Målt 11/9-2026 på fem ture der døde af «chat session not found»:

    død 06:24:08 -> stemplet 06:24:25   (17 s efter)
    død 06:29:38 -> stemplet 06:30:34   (56 s efter)
    død 06:32:10 -> stemplet 06:32:47   (37 s efter)

Alle fem stod `failed` i `visible_runs` FØR nedlukningen begyndte. Sweepens
egen docstring kalder dem «crash-zombies whose finally never ran» — men med
`stale_after_s=0.0` tager den også poster som en helt almindelig fejlet tur
efterlod. Og `interrupted_for_session()` sætter `resume_context`, så en fejlet
tur kunne blive tilbudt som en afbrudt tur.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.services import visible_runs_outcomes as vro


def _db(tmp_path, rows: list[tuple]) -> str:
    sti = str(tmp_path / "v.db")
    con = sqlite3.connect(sti)
    con.execute("CREATE TABLE visible_runs (run_id TEXT PRIMARY KEY, status TEXT, "
                "finished_at TEXT)")
    con.executemany("INSERT INTO visible_runs VALUES (?,?,?)", rows)
    con.commit()
    con.close()
    return sti


@pytest.fixture
def _forbind(monkeypatch):
    def _lav(sti):
        import contextlib

        @contextlib.contextmanager
        def _c():
            con = sqlite3.connect(sti)
            try:
                yield con
            finally:
                con.close()
        monkeypatch.setattr(vro, "connect", _c)
    return _lav


def test_afsluttet_run_er_terminal(tmp_path, _forbind):
    _forbind(_db(tmp_path, [("r1", "failed", "2026-09-11T06:24:08")]))
    assert vro.run_er_terminal("r1") is True


def test_alle_fire_terminale_statusser_taeller(tmp_path, _forbind):
    _forbind(_db(tmp_path, [(s, s, "") for s in
                            ("completed", "failed", "cancelled", "error")]))
    for s in ("completed", "failed", "cancelled", "error"):
        assert vro.run_er_terminal(s) is True, s


def test_ingen_raekke_er_en_AEGTE_zombie(tmp_path, _forbind):
    """Rækken skrives kun ved afslutning (`_persist_visible_run_outcome` kræver
    `finished_at`), så ingen række betyder at runnet aldrig nåede dertil."""
    _forbind(_db(tmp_path, []))
    assert vro.run_er_terminal("findes-ikke") is False


def test_uafgjort_er_ikke_terminal(tmp_path, _forbind):
    """En DB-hikke må ikke læses som «turen var slut» — så ville sweepen rydde
    en post der faktisk hørte til en levende tur."""
    _forbind(str(tmp_path / "findes-ikke.db") + "/umuligt")
    assert vro.run_er_terminal("r1") is None
    assert vro.run_er_terminal("") is None


def test_sweepen_spoerger_foer_den_stempler():
    """Kildetjek på kaldestedet: rækkefølgen er hele pointen."""
    src = open("apps/api/jarvis_api/app.py", encoding="utf-8").read()
    i = src.index("list_running_orphans(0.0)")
    vindue = src[i:i + 1400]
    assert "run_er_terminal" in vindue
    assert vindue.index("run_er_terminal") < vindue.index('reason="api-nedlukning"')
