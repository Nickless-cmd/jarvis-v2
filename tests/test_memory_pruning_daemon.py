"""Pruning arkiverer det gamle og uanvendte — men aldrig en undtaget dagbog (brain_archive).

Målt 4/11-2026: 58 af 147 backfillede dagbøger blev arkiveret af denne daemon og
jarvis_brain_daemon inden for minutter.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.services import daily_journal_entry as je, jarvis_brain
from core.services import memory_pruning_daemon as mp

_NU = datetime(2026, 11, 4, 20, 0, tzinfo=UTC)
_GAMMEL = datetime(2026, 6, 9, 20, 0, tzinfo=UTC)


@pytest.fixture
def hjerne(tmp_path, monkeypatch):
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    return jarvis_brain.brain_dir()


def _gammel_dagbog(hjerne, dag="2026-06-09"):
    p = hjerne / "observation" / f"{dag}-daily.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"# Daily journal — {dag}\n\n_Synthesized {dag}T20:00:00+00:00 — 5 chat-msgs, 0 carries._\n\nDagen gik.\n",
        encoding="utf-8",
    )
    assert je.ensure_frontmatter(p) == "added"
    jarvis_brain.rebuild_index_from_files()
    return p


def _gammel_observation():
    return jarvis_brain.write_entry(
        kind="observation", title="Gammel observation", content="noget",
        visibility="personal", domain="self", now=_GAMMEL,
    )


def _status(entry_id_or_path_like):
    conn = jarvis_brain.connect_index()
    try:
        return conn.execute(
            "SELECT status FROM brain_index WHERE id = ? OR path LIKE ?",
            (entry_id_or_path_like, f"%{entry_id_or_path_like}"),
        ).fetchone()[0]
    finally:
        conn.close()


def test_memory_pruning_arkiverer_den_gamle_observation_men_ikke_dagbogen(hjerne):
    _gammel_dagbog(hjerne)
    obs = _gammel_observation()
    assert mp._prune_brain_entries(_NU) == 1          # præcis den ene: ikke dagbogen
    assert _status(obs) == "archived"
    assert _status("2026-06-09-daily.md") == "active"
    assert (hjerne / "observation" / "2026-06-09-daily.md").exists()


def test_pruning_stoler_ikke_kun_paa_indeksets_tags(hjerne):
    """Indeks og fil kan glide fra hinanden. Filens tag afgør; guarden i Python fanger det SQL-filteret ikke ser."""
    _gammel_dagbog(hjerne)
    conn = jarvis_brain.connect_index()
    try:
        conn.execute("UPDATE brain_index SET tags = '[]' WHERE path LIKE '%-daily.md'")
        conn.commit()
    finally:
        conn.close()
    assert mp._prune_brain_entries(_NU) == 0
    assert _status("2026-06-09-daily.md") == "active"


def test_dagbogen_fylder_ikke_pruning_kandidatpuljen(hjerne, monkeypatch):
    """Mange undtagne dagbøger må ikke fortrænge de poster der FAKTISK skal glemmes."""
    monkeypatch.setattr(mp, "_MAX_PRUNE_PER_CYCLE", 1)
    monkeypatch.setattr(mp, "_BRAIN_CANDIDATE_FACTOR", 2)   # pulje = 2
    for d in ("2026-06-09", "2026-06-10", "2026-06-11", "2026-06-12"):
        _gammel_dagbog(hjerne, d)
    obs = _gammel_observation()
    assert mp._prune_brain_entries(_NU) == 1
    assert _status(obs) == "archived"
