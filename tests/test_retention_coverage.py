"""Tests for `core/services/retention_coverage.py`.

Baggrund (målt på CT105 27/9-2026): oprydningen i `events_retention` virker —
`events` holder præcis sine 14 dage. Men politikken er en håndskreven liste,
og `cheap_lane_route_decisions` blev oprettet 18. september og var ni dage
senere 2.381 MB, 45 % af hele `jarvis.db`, uden at stå på den.

En liste over hvad der skal ryddes op kan ikke selv opdage hvad der mangler på
den. Vagten spørger den anden vej — hvad fylder, som ingen har taget stilling
til — og testene her er vagten om vagten.
"""

from __future__ import annotations

import ast
import sqlite3

import pytest

import core.services.retention_coverage as rc


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


def _tabel(conn, navn: str, raekker: int = 0, bredde: int = 8) -> None:
    conn.execute('CREATE TABLE "%s" (id INTEGER PRIMARY KEY, v TEXT)' % navn)
    if raekker:
        conn.executemany(
            'INSERT INTO "%s" (v) VALUES (?)' % navn,
            [("x" * bredde,) for _ in range(raekker)],
        )
    conn.commit()


class TestDenFinderDetUdaekkede:
    def test_stor_tabel_uden_politik_rapporteres(self, db) -> None:
        _tabel(db, "en_ny_fed_tabel", raekker=200)
        fund = rc.tabeller_uden_politik(conn=db, min_bytes=1, min_raekker=1)
        assert [f["tabel"] for f in fund] == ["en_ny_fed_tabel"]
        assert fund[0]["raekker"] == 200
        assert fund[0]["bytes"] > 0

    def test_lille_tabel_rapporteres_ikke(self, db) -> None:
        """Med de RIGTIGE tærskler — ikke de nedskruede testværdier."""
        _tabel(db, "en_lille_tabel", raekker=50)
        assert rc.tabeller_uden_politik(conn=db) == []

    def test_stoerste_foerst(self, db) -> None:
        _tabel(db, "lille", raekker=10)
        _tabel(db, "stor", raekker=500)
        fund = rc.tabeller_uden_politik(conn=db, min_bytes=1, min_raekker=1)
        assert [f["tabel"] for f in fund] == ["stor", "lille"]

    def test_sqlite_interne_tabeller_taeller_ikke_med(self, db) -> None:
        _tabel(db, "rigtig", raekker=5)
        db.execute("ANALYZE")          # opretter sqlite_stat1
        db.commit()
        assert db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='sqlite_stat1'"
        ).fetchone(), "ANALYZE oprettede ikke den interne tabel testen handler om"
        fund = [f["tabel"] for f in rc.tabeller_uden_politik(conn=db, min_bytes=1, min_raekker=1)]
        assert "rigtig" in fund
        assert not any(n.startswith("sqlite_") for n in fund)


class TestDeTwoSkuffer:
    def test_tabel_med_politik_rapporteres_ikke(self, db) -> None:
        navn = next(iter(rc.har_politik()))
        _tabel(db, navn, raekker=500)
        assert rc.tabeller_uden_politik(conn=db, min_bytes=1, min_raekker=1) == []

    def test_bevidst_uden_alder_rapporteres_ikke(self, db) -> None:
        navn = next(iter(rc._BEVIDST_UDEN_ALDER))
        _tabel(db, navn, raekker=500)
        assert rc.tabeller_uden_politik(conn=db, min_bytes=1, min_raekker=1) == []

    def test_ingen_tabel_staar_i_BEGGE_skuffer(self) -> None:
        """To sandheder om samme tabel er præcis den fejl vagten findes imod."""
        begge = set(rc.har_politik()) & set(rc._BEVIDST_UDEN_ALDER)
        assert not begge, "både politik og «bevidst uden alder»: %s" % sorted(begge)

    def test_hver_undtagelse_har_en_rigtig_grund(self) -> None:
        """En tom grund er en udeladelse forklædt som en beslutning."""
        for tabel, grund in rc._BEVIDST_UDEN_ALDER.items():
            assert isinstance(grund, str) and len(grund.strip()) >= 20, (
                "%s har ingen brugbar grund: %r" % (tabel, grund)
            )


class TestBeggeMaal:
    def test_mange_smalle_raekker_taeller_ogsaa(self, db) -> None:
        """`central_hypothesis_samples`: 503.619 rækker, kun 49 MB. En vagt der
        kun målte bytes ville lade den passere."""
        _tabel(db, "mange_smalle", raekker=300, bredde=1)
        fund = rc.tabeller_uden_politik(conn=db, min_bytes=10**9, min_raekker=100)
        assert [f["tabel"] for f in fund] == ["mange_smalle"]

    def test_faa_fede_raekker_taeller_ogsaa(self, db) -> None:
        """`cheap_lane_route_decisions`: 52.786 rækker, 2.381 MB. En vagt der
        kun målte rækker ville lade DEN passere."""
        _tabel(db, "faa_fede", raekker=40, bredde=9000)
        fund = rc.tabeller_uden_politik(conn=db, min_bytes=100_000, min_raekker=10**9)
        assert [f["tabel"] for f in fund] == ["faa_fede"]


class TestUdenDbstat:
    def test_falder_tilbage_til_raekketal(self, db, monkeypatch) -> None:
        """dbstat er ikke bygget ind i alle SQLite-udgaver. Vagten skal blive
        mindre følsom — ikke tavs."""
        monkeypatch.setattr(rc, "_stoerrelser", lambda conn: {})
        _tabel(db, "uden_dbstat", raekker=200)
        fund = rc.tabeller_uden_politik(conn=db, min_bytes=1, min_raekker=100)
        assert [f["tabel"] for f in fund] == ["uden_dbstat"]
        assert fund[0]["bytes"] == 0


class TestRutebeslutningerneErDaekket:
    def test_tabellen_staar_paa_politikken(self) -> None:
        """Selve fejlen: 2.381 MB på ni dage uden en politik."""
        assert "cheap_lane_route_decisions" in rc.har_politik()

    def test_retentionen_er_bredere_end_diagnostik_vinduet(self) -> None:
        """KOBLINGEN. `route_integrity` melder «invocation uden rute» for alt i
        sit vindue. Er retentionen smallere end vinduet, begynder den at melde
        rækker vi selv har slettet. Vinduet læses ud af kilden, så testen ikke
        pinner sit eget opdigtede tal.
        """
        import inspect

        from core.services import cheap_lane_diagnostics as cld
        from core.services import events_retention as er

        timer = 0.0
        for node in ast.walk(ast.parse(inspect.getsource(cld))):
            if not (isinstance(node, ast.Call)
                    and getattr(node.func, "id", "") == "timedelta"):
                continue
            for kw in node.keywords:
                if not isinstance(kw.value, ast.Constant):
                    continue
                v = float(kw.value.value)
                if kw.arg == "hours":
                    timer = max(timer, v)
                elif kw.arg == "days":
                    timer = max(timer, v * 24)
        assert timer > 0, "fandt intet tidsvindue i cheap_lane_diagnostics"

        dage = dict((t, d) for t, _k, d in er._TELEMETRY_RETENTION)[
            "cheap_lane_route_decisions"
        ]
        assert dage * 24 >= timer * 2, (
            "retention %d dage er ikke komfortabelt bredere end "
            "diagnostik-vinduet %.0f timer" % (dage, timer)
        )

    def test_ruter_og_invocations_har_hver_sit_tal_med_vilje(self) -> None:
        """De to er ikke samme slags — udfald mod fejlfindings-spor — så de har
        forskellig alder. Det skal være et VALG: rutebeslutningerne må ikke
        styres af `cheap_lane_metadata_retention_days`."""
        from core.services import events_retention as er
        assert "cheap_lane_route_decisions" not in er._CHEAP_LANE_METADATA_TABLER
        assert "cheap_provider_invocations" in er._CHEAP_LANE_METADATA_TABLER


class TestRapport:
    def test_tom_liste_giver_tom_linje(self) -> None:
        assert rc.rapport([]) == ""

    def test_linjen_naevner_tabel_og_stoerrelse(self) -> None:
        linje = rc.rapport([{"tabel": "en_tabel", "bytes": 2_381_000_000, "raekker": 52786}])
        assert "en_tabel" in linje and "2381 MB" in linje and "52786" in linje

    def test_lang_liste_forkortes_men_siger_hvor_mange(self) -> None:
        fund = [{"tabel": "t%d" % i, "bytes": i, "raekker": i} for i in range(10)]
        linje = rc.rapport(fund)
        assert "+4 mere" in linje
