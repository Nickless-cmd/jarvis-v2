"""Tests for oprydningen i ``brain_temporal_edges``.

Baggrund (målt 2026-08-30): tabellen var vokset til 2.812.752 rækker / 1,2 GB
og voksede ~10.000/dag. ``prune_stale_edges`` blev kaldt fire steder og kørte
fint — men slettede kun rækker med ``confidence < 0.2``, og den LAVESTE værdi i
hele tabellen var 0,4. Filteret matchede nul rækker og ville aldrig matche
nogen. Oprydningen var strukturelt død.

Rettelsen binder oprydningens tærskel til LÆSERENS tærskel via én fælles
konstant, så de to ikke kan glide fra hinanden igen, og indfører et loft pr.
node fordi grafen ellers vokser kvadratisk med antallet af entries.
"""

from __future__ import annotations

import sqlite3

import pytest

import core.services.jarvis_brain as jb


@pytest.fixture
def brain_db(tmp_path, monkeypatch):
    """Isoleret index-database — rører aldrig runtime-tilstanden."""
    path = tmp_path / "brain_index.sqlite"
    monkeypatch.setattr(jb, "index_db_path", lambda: path)
    yield path


def _edges(path, rows: list[tuple[str, str, float]]) -> None:
    conn = jb.connect_index()
    try:
        conn.executemany(
            "INSERT OR REPLACE INTO brain_temporal_edges "
            "(from_id, to_id, relation_type, confidence, inferred_at) "
            "VALUES (?, ?, 'combined', ?, '2026-01-01T00:00:00+00:00')",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _count(path) -> int:
    conn = sqlite3.connect(str(path))
    try:
        return conn.execute("SELECT COUNT(*) FROM brain_temporal_edges").fetchone()[0]
    finally:
        conn.close()


class TestThresholdsCannotDrift:
    def test_reader_and_pruner_share_one_constant(self) -> None:
        """Selve fejlen: to tærskler der gled fra hinanden i tre måneder."""
        import inspect
        reader = inspect.signature(jb._compute_search_temporal_boost)
        pruner = inspect.signature(jb.prune_stale_edges)
        assert (reader.parameters["min_confidence"].default
                == pruner.parameters["min_confidence"].default
                == jb.TEMPORAL_EDGE_READ_MIN_CONFIDENCE)

    def test_constant_is_above_what_the_writer_stores(self) -> None:
        """En tærskel under skriverens gulv kan aldrig ramme noget."""
        assert jb.TEMPORAL_EDGE_READ_MIN_CONFIDENCE > 0.2


class TestPruneUnreadableEdges:
    def test_removes_only_below_the_read_threshold(self, brain_db) -> None:
        thr = jb.TEMPORAL_EDGE_READ_MIN_CONFIDENCE
        _edges(brain_db, [
            ("a", "b", thr - 0.1),      # under → aldrig læst
            ("c", "d", thr),            # præcis på → læses
            ("e", "f", thr + 0.2),      # over → læses
        ])
        removed = jb.prune_unreadable_edges()
        assert removed == 1
        assert _count(brain_db) == 2

    def test_ignores_age_entirely(self, brain_db) -> None:
        """Alderen er irrelevant: en ulæselig kant er dødvægt fra dag ét."""
        conn = jb.connect_index()
        conn.execute(
            "INSERT INTO brain_temporal_edges VALUES ('x','y','combined',0.1,?)",
            ("2099-01-01T00:00:00+00:00",),
        )
        conn.commit(); conn.close()
        assert jb.prune_unreadable_edges() == 1

    def test_empty_table_is_safe(self, brain_db) -> None:
        assert jb.prune_unreadable_edges() == 0

    def test_keeps_everything_when_all_are_readable(self, brain_db) -> None:
        _edges(brain_db, [("a", "b", 0.9), ("c", "d", 0.8)])
        assert jb.prune_unreadable_edges() == 0
        assert _count(brain_db) == 2


class TestPruneDenseEdges:
    def test_caps_edges_per_node(self, brain_db) -> None:
        """Én node med mange naboer trimmes til loftet."""
        rows = [("hub", f"n{i}", 0.5 + i / 1000.0) for i in range(20)]
        _edges(brain_db, rows)
        jb.prune_dense_edges(max_per_node=5)
        # Hver n{i} har kun én kant, så de er alle top-1 for deres eget
        # endepunkt — konservativt beholdes de. Loftet må aldrig slette en
        # kant der er den eneste et sted.
        assert _count(brain_db) == 20

    def test_en_taet_klike_trimmes_til_loftet(self, brain_db) -> None:
        """En tæt klike: kanter uden for top-N i ÉN ende ryger.

        Reglen var «svag i BEGGE ender» indtil 17/9-2026, og det gjorde loftet
        til en tom formulering: en kant overlevede bare fordi den var stærk nok
        for det andet endepunkt. Målt i produktionen lå 4.415 noder over
        loftet, den tætteste med 737 kanter, og reglen ville have fjernet 2.824
        af 684.193 rækker.
        """
        nodes = [f"k{i}" for i in range(10)]
        rows = []
        for i, a in enumerate(nodes):
            for j, b in enumerate(nodes):
                if i < j:
                    rows.append((a, b, 0.5 + (i + j) / 100.0))
        _edges(brain_db, rows)
        before = _count(brain_db)
        assert before == 45
        removed = jb.prune_dense_edges(max_per_node=3)
        after = _count(brain_db)
        assert removed > 0, "tætte hubs skal trimmes"
        assert after == before - removed
        assert after > 0, "må aldrig tømme tabellen"

    def test_strongest_edge_always_survives(self, brain_db) -> None:
        """Læseren bruger MAX(confidence) — den stærkeste må ALDRIG ryge."""
        rows = [("hub", f"n{i}", 0.5) for i in range(30)]
        rows.append(("hub", "vigtig", 0.99))
        _edges(brain_db, rows)
        jb.prune_dense_edges(max_per_node=4)
        conn = sqlite3.connect(str(brain_db))
        best = conn.execute(
            "SELECT MAX(confidence) FROM brain_temporal_edges WHERE from_id='hub'"
        ).fetchone()[0]
        conn.close()
        assert best == pytest.approx(0.99)

    def test_empty_table_is_safe(self, brain_db) -> None:
        assert jb.prune_dense_edges(max_per_node=10) == 0

    def test_below_cap_changes_nothing(self, brain_db) -> None:
        _edges(brain_db, [("a", "b", 0.9), ("a", "c", 0.8)])
        assert jb.prune_dense_edges(max_per_node=64) == 0
        assert _count(brain_db) == 2

    def test_en_nodes_SIDSTE_kant_beholdes_altid(self, brain_db) -> None:
        """Ellers bygger loftet en rundgang der aldrig stopper.

        En node uden kanter findes af `b4_catchup_infer_once` hver time og får
        sine kanter udledt igen — tolv sekunders arbejde pr. post — hvorefter
        næste oprydning fjerner dem igen. Målt 17/9-2026: 3.946 af de 387.180
        kanter loftet ville fjerne, var en nodes eneste. Værnet koster dem og
        fjerner løkken.
        """
        # En hub med 20 eger; hver ege har KUN sin ene kant.
        _edges(brain_db, [("hub", f"n{i}", 0.5 + i / 1000.0) for i in range(20)])
        jb.prune_dense_edges(max_per_node=5)
        assert _count(brain_db) == 20, "en eges eneste kant blev slettet"

    def test_loftet_holder_naar_ingen_bliver_foraeldreloes(self, brain_db) -> None:
        """To hubs der deler alle deres naboer: her HAR hver nabo to kanter, så
        loftet kan trimme uden at efterlade nogen uden kanter."""
        rows = []
        for i in range(30):
            rows.append(("hub-a", f"m{i}", 0.5 + i / 1000.0))
            rows.append(("hub-b", f"m{i}", 0.5 + i / 1000.0))
        _edges(brain_db, rows)
        jb.prune_dense_edges(max_per_node=5)
        # Hver m{i} beholder sin stærkeste; hubberne er trimmet.
        assert _count(brain_db) < 60, "loftet trimmede ingenting"
        assert _count(brain_db) >= 30, "en nabo mistede sin sidste kant"
