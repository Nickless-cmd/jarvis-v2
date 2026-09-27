"""Tests for `core/services/brain_vector_cache.py`.

Baggrund (målt 27/9-2026 på CT105, 13.541 aktive poster): `search_brain_scored`
regnede cosinus én række ad gangen — 56,9 ms, mod 2,6 ms for den samme
udregning som ÉN matmul. Cachen findes for at matricen ikke skal bygges forfra
ved hver søgning (`frombuffer`+`stack` koster 22-28 ms).

Det farlige ved en cache er ikke farten, det er at den kan servere noget
forældet. Derfor pinner testene her tre ting: at resultatet er NØJAGTIG det
den gamle rækkevise formel gav, at nøglen indeholder `indexed_at` så en
omskrevet række ikke kan serveres gammel, og at cachen tømmes når databasen
under den skifter — ellers ville modul-tilstanden lække mellem tests.
"""

from __future__ import annotations

import numpy as np
import pytest

import core.services.brain_vector_cache as bvc
import core.services.jarvis_brain as jb


@pytest.fixture
def brain_db(tmp_path, monkeypatch):
    """Isoleret index-database — rører aldrig runtime-tilstanden."""
    sti = tmp_path / "brain_index.sqlite"
    monkeypatch.setattr(jb, "index_db_path", lambda: sti)
    bvc.ryd()
    yield sti
    bvc.ryd()


def _indsaet(
    vektorer: dict[str, np.ndarray],
    *,
    indexed_at: str = "2026-01-01T00:00:00+00:00",
) -> None:
    conn = jb.connect_index()
    try:
        for eid, v in vektorer.items():
            conn.execute(
                """INSERT OR REPLACE INTO brain_index
                   (id, path, kind, visibility, domain, title, created_at,
                    updated_at, file_hash, embedding, embedding_dim, indexed_at)
                   VALUES (?, ?, 'fakta', 'personal', 'test', ?,
                           '2026-01-01T00:00:00+00:00',
                           '2026-01-01T00:00:00+00:00', 'h', ?, ?, ?)""",
                (eid, f"p/{eid}.md", eid, v.astype(np.float32).tobytes(),
                 int(v.shape[0]), indexed_at),
            )
        conn.commit()
    finally:
        conn.close()


def _raekkevis(qv: np.ndarray, v: np.ndarray) -> float:
    """Præcis den formel `search_brain_scored` brugte før vektoriseringen."""
    denom = float(np.linalg.norm(qv) * np.linalg.norm(v)) or 1e-9
    return float(np.dot(qv, v) / denom)


class TestSammeSvarSomFoer:
    def test_cosinus_matcher_den_raekkevise_formel(self, brain_db) -> None:
        rng = np.random.default_rng(7)
        vektorer = {
            f"brn_{i}": rng.standard_normal(768).astype(np.float32)
            for i in range(20)
        }
        _indsaet(vektorer)
        qv = rng.standard_normal(768).astype(np.float32)

        noegler = [(eid, "2026-01-01T00:00:00+00:00") for eid in vektorer]
        faaet = bvc.cosinus(noegler, qv)
        ventet = np.array([_raekkevis(qv, vektorer[eid]) for eid, _ in noegler])

        assert faaet.shape == (20,)
        np.testing.assert_allclose(faaet, ventet, rtol=1e-5, atol=1e-6)

    def test_raekkefoelgen_foelger_noeglerne(self, brain_db) -> None:
        """Kalderen parrer resultatet med sin egen liste — rækkefølgen ER kontrakten."""
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        _indsaet({"brn_a": a, "brn_b": b})
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        frem = bvc.cosinus([("brn_a", "2026-01-01T00:00:00+00:00"),
                            ("brn_b", "2026-01-01T00:00:00+00:00")], qv)
        bagud = bvc.cosinus([("brn_b", "2026-01-01T00:00:00+00:00"),
                             ("brn_a", "2026-01-01T00:00:00+00:00")], qv)

        assert frem[0] == pytest.approx(1.0, abs=1e-6)
        assert frem[1] == pytest.approx(0.0, abs=1e-6)
        assert bagud[0] == pytest.approx(0.0, abs=1e-6)
        assert bagud[1] == pytest.approx(1.0, abs=1e-6)

    def test_tom_noegleliste(self, brain_db) -> None:
        assert bvc.cosinus([], np.ones(3, dtype=np.float32)).shape == (0,)


class TestCachenHolder:
    def test_andet_kald_roerer_ikke_databasen(self, brain_db, monkeypatch) -> None:
        """Hele pointen: vektorerne må kun hentes én gang."""
        _indsaet({"brn_a": np.array([1.0, 2.0, 3.0], dtype=np.float32)})
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        noegler = [("brn_a", "2026-01-01T00:00:00+00:00")]
        foerste = bvc.cosinus(noegler, qv)

        aegte_connect = jb.connect_index
        kald: list[int] = []

        def taeller():
            kald.append(1)
            return aegte_connect()

        monkeypatch.setattr(jb, "connect_index", taeller)
        andet = bvc.cosinus(noegler, qv)

        assert kald == []
        np.testing.assert_allclose(andet, foerste)

    def test_en_ny_post_henter_kun_den_nye(self, brain_db, monkeypatch) -> None:
        _indsaet({"brn_a": np.array([1.0, 0.0, 0.0], dtype=np.float32)})
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        bvc.cosinus([("brn_a", "2026-01-01T00:00:00+00:00")], qv)

        _indsaet({"brn_b": np.array([0.0, 1.0, 0.0], dtype=np.float32)})
        aegte_execute_ider: list[list] = []
        aegte_connect = jb.connect_index

        class Opsnapper:
            """`sqlite3.Connection.execute` er skrivebeskyttet — derfor en proxy."""

            def __init__(self, conn):
                self._conn = conn

            def execute(self, sql, params=()):
                if "SELECT" in sql and "embedding" in sql:
                    aegte_execute_ider.append(list(params))
                return self._conn.execute(sql, params)

            def __getattr__(self, navn):
                return getattr(self._conn, navn)

        monkeypatch.setattr(jb, "connect_index", lambda: Opsnapper(aegte_connect()))
        ud = bvc.cosinus([("brn_a", "2026-01-01T00:00:00+00:00"),
                          ("brn_b", "2026-01-01T00:00:00+00:00")], qv)

        assert aegte_execute_ider == [["brn_b"]], aegte_execute_ider
        assert ud[0] == pytest.approx(1.0, abs=1e-6)
        assert ud[1] == pytest.approx(0.0, abs=1e-6)


class TestCachenKanIkkeServereNogetForaeldet:
    def test_ny_indexed_at_henter_vektoren_igen(self, brain_db) -> None:
        """Nøglen er (id, indexed_at) — ikke bare id. Var den bare id'et,
        ville en omskrevet post blive serveret med sin gamle vektor for evigt."""
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        _indsaet({"brn_a": np.array([0.0, 1.0, 0.0], dtype=np.float32)},
                 indexed_at="2026-01-01T00:00:00+00:00")
        foer = bvc.cosinus([("brn_a", "2026-01-01T00:00:00+00:00")], qv)
        assert foer[0] == pytest.approx(0.0, abs=1e-6)

        _indsaet({"brn_a": np.array([1.0, 0.0, 0.0], dtype=np.float32)},
                 indexed_at="2026-02-02T00:00:00+00:00")
        efter = bvc.cosinus([("brn_a", "2026-02-02T00:00:00+00:00")], qv)
        assert efter[0] == pytest.approx(1.0, abs=1e-6)

    def test_cachen_nulstilles_naar_databasen_skifter(
        self, tmp_path, monkeypatch
    ) -> None:
        """Værn mod at modul-tilstand lækker mellem tests med genbrugte id'er."""
        bvc.ryd()
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        noegle = [("brn_a", "2026-01-01T00:00:00+00:00")]

        en = tmp_path / "en.sqlite"
        monkeypatch.setattr(jb, "index_db_path", lambda: en)
        _indsaet({"brn_a": np.array([0.0, 1.0, 0.0], dtype=np.float32)})
        assert bvc.cosinus(noegle, qv)[0] == pytest.approx(0.0, abs=1e-6)

        to = tmp_path / "to.sqlite"
        monkeypatch.setattr(jb, "index_db_path", lambda: to)
        _indsaet({"brn_a": np.array([1.0, 0.0, 0.0], dtype=np.float32)})
        assert bvc.cosinus(noegle, qv)[0] == pytest.approx(1.0, abs=1e-6)
        bvc.ryd()


class TestDetDerKanGaaGalt:
    def test_ukendt_noegle_giver_nul_og_vaelter_ikke(self, brain_db) -> None:
        """Rækken kan være slettet mellem kalderens SELECT og cachens hentning."""
        _indsaet({"brn_a": np.array([1.0, 0.0, 0.0], dtype=np.float32)})
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        ud = bvc.cosinus([("brn_a", "2026-01-01T00:00:00+00:00"),
                          ("brn_findes-ikke", "2026-01-01T00:00:00+00:00")], qv)
        assert ud[0] == pytest.approx(1.0, abs=1e-6)
        assert ud[1] == 0.0

    def test_kun_ukendte_noegler(self, brain_db) -> None:
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        ud = bvc.cosinus([("brn_x", "t"), ("brn_y", "t")], qv)
        assert list(ud) == [0.0, 0.0]

    def test_nulvektor_giver_nul_og_ikke_nan(self, brain_db) -> None:
        """Den gamle formel havde `or 1e-9` på nævneren; det skal overleve."""
        _indsaet({"brn_nul": np.zeros(3, dtype=np.float32)})
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        ud = bvc.cosinus([("brn_nul", "2026-01-01T00:00:00+00:00")], qv)
        assert np.isfinite(ud).all()
        assert ud[0] == pytest.approx(0.0, abs=1e-9)

    def test_afvigende_dimension_udelades_i_stedet_for_at_vaelte(
        self, brain_db
    ) -> None:
        _indsaet({"brn_3": np.array([1.0, 0.0, 0.0], dtype=np.float32)})
        _indsaet({"brn_4": np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)})
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        ud = bvc.cosinus([("brn_3", "2026-01-01T00:00:00+00:00"),
                          ("brn_4", "2026-01-01T00:00:00+00:00")], qv)
        assert ud[0] == pytest.approx(1.0, abs=1e-6)
        assert ud[1] == 0.0


class TestBeggeHentevejeVirker:
    """Der er to: `IN (...)` for de få, og en fuld hentning for de mange.

    Uden en test pr. vej kan den ene være brækket uden at noget bliver rødt —
    og hvilken vej der tages afhænger af hvor kold cachen er, ikke af koden.
    """

    def _tre(self) -> dict[str, np.ndarray]:
        return {
            "brn_a": np.array([1.0, 0.0, 0.0], dtype=np.float32),
            "brn_b": np.array([0.0, 1.0, 0.0], dtype=np.float32),
            "brn_c": np.array([0.0, 0.0, 1.0], dtype=np.float32),
        }

    def _noegler(self):
        return [(e, "2026-01-01T00:00:00+00:00") for e in ("brn_a", "brn_b", "brn_c")]

    def test_faa_manglende_gaar_gennem_in_listen(self, brain_db, monkeypatch) -> None:
        monkeypatch.setattr(bvc, "_FULD_HENTNING_GRAENSE", 100)
        _indsaet(self._tre())
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        ud = bvc.cosinus(self._noegler(), qv)
        np.testing.assert_allclose(ud, [1.0, 0.0, 0.0], atol=1e-6)

    def test_mange_manglende_gaar_gennem_fuld_hentning(
        self, brain_db, monkeypatch
    ) -> None:
        monkeypatch.setattr(bvc, "_FULD_HENTNING_GRAENSE", 1)
        _indsaet(self._tre())
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        ud = bvc.cosinus(self._noegler(), qv)
        np.testing.assert_allclose(ud, [1.0, 0.0, 0.0], atol=1e-6)

    def test_fuld_hentning_varmer_ogsaa_de_upurgte(
        self, brain_db, monkeypatch
    ) -> None:
        """En fuld hentning har allerede læst alle blob'er — de skal beholdes,
        ellers henter næste søgning med et andet filter alt forfra."""
        monkeypatch.setattr(bvc, "_FULD_HENTNING_GRAENSE", 1)
        _indsaet(self._tre())
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        bvc.cosinus(self._noegler()[:2], qv)

        aegte_connect = jb.connect_index
        kald: list[int] = []
        monkeypatch.setattr(
            jb, "connect_index", lambda: (kald.append(1), aegte_connect())[1]
        )
        ud = bvc.cosinus([("brn_c", "2026-01-01T00:00:00+00:00")], qv)
        assert kald == []
        assert ud[0] == pytest.approx(0.0, abs=1e-6)


class TestLoftet:
    def test_over_loftet_bygges_cachen_forfra(self, brain_db, monkeypatch) -> None:
        """Cachen lever i en dæmon der kører i ugevis. Uden loft er den en lækage."""
        monkeypatch.setattr(bvc, "_MAKS_RAEKKER", 2)
        monkeypatch.setattr(bvc, "_FULD_HENTNING_GRAENSE", 100)
        qv = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        _indsaet({"brn_a": np.array([1.0, 0.0, 0.0], dtype=np.float32),
                  "brn_b": np.array([0.0, 1.0, 0.0], dtype=np.float32)})
        bvc.cosinus([("brn_a", "2026-01-01T00:00:00+00:00"),
                     ("brn_b", "2026-01-01T00:00:00+00:00")], qv)
        assert bvc.status()["raekker"] == 2

        _indsaet({"brn_c": np.array([0.0, 0.0, 1.0], dtype=np.float32)})
        ud = bvc.cosinus([("brn_c", "2026-01-01T00:00:00+00:00")], qv)

        # Bygget forfra: kun den nye nøgle er tilbage — og svaret er rigtigt.
        assert bvc.status()["raekker"] == 1
        assert ud[0] == pytest.approx(0.0, abs=1e-6)

    def test_status_rapporterer_hvad_der_ligger(self, brain_db) -> None:
        _indsaet({"brn_a": np.array([1.0, 2.0, 3.0], dtype=np.float32)})
        bvc.cosinus([("brn_a", "2026-01-01T00:00:00+00:00")],
                    np.ones(3, dtype=np.float32))
        st = bvc.status()
        assert st["raekker"] == 1
        assert st["dim"] == 3
        assert st["bytes"] == 12
        assert str(st["db"]).endswith("brain_index.sqlite")

    def test_ryd_toemmer_alt(self, brain_db) -> None:
        _indsaet({"brn_a": np.array([1.0, 2.0, 3.0], dtype=np.float32)})
        bvc.cosinus([("brn_a", "2026-01-01T00:00:00+00:00")],
                    np.ones(3, dtype=np.float32))
        bvc.ryd()
        assert bvc.status() == {"raekker": 0, "dim": 0, "bytes": 0, "db": None}
