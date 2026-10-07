"""`db_query`: fejlen skal baere skemaet, for et opslag koster en runde.

Maalt 5/10-2026 over 7 dage: 185 af 777 db_query-kald fejlede (23,8 %), og
formerne var naesten alle gaet: «no such column: status» 17 gange, «no such
column: created_at» 12, «no such table: heartbeat_ticks» 8. Der fandtes
allerede et puf der sagde «slaa skemaet op ÉN gang» — og det puf koster en
runde paa ~7,7 s. Fejlen kender navnet der ikke fandtes; den kan lige saa godt
sige hvad der findes.

Alt maales mod RIGTIG sqlite. En fake forbindelse der svarer det samme uanset
forespoergslen kan ikke se om skema-opslaget rammer noget.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.tools.db_query_tool import _exec_db_query, skema_hint


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE visible_runs (run_id TEXT, status TEXT, started_at TEXT)")
    c.execute("CREATE TABLE costs (id INTEGER, lane TEXT, created_at TEXT)")
    c.execute("CREATE TABLE heartbeat_state (id INTEGER)")
    return c


def test_manglende_tabel_navngiver_det_taettest_paa(conn):
    """Den rigtige fejl 5/10 var «no such table: heartbeat_ticks».

    Listen over alle tabeller daekkes af de to tests nederst: den kommer frem
    naar intet naert traef findes, og udgaar naar et goer.
    """
    hint = skema_hint(conn, "no such table: heartbeat_ticks",
                      "SELECT * FROM heartbeat_ticks")
    assert "heartbeat_ticks" in hint
    assert "heartbeat_state" in hint, "den naermeste skal naevnes"


def test_manglende_kolonne_giver_tabellens_EGNE_kolonner(conn):
    """Min egen fejl, to gange paa én time: visible_runs har started_at, ikke created_at."""
    hint = skema_hint(conn, "no such column: created_at",
                      "SELECT created_at FROM visible_runs WHERE status = 'running'")
    assert "created_at" in hint
    assert "started_at" in hint, "det rigtige navn skal staa der"
    assert "run_id" in hint and "status" in hint


def test_kolonne_hint_laeser_tabellen_fra_SQL_ens_FROM(conn):
    """Hintet skal ramme den tabel der faktisk spoerges i — ikke en vilkaarlig."""
    hint = skema_hint(conn, "no such column: lane",
                      "SELECT lane FROM visible_runs")
    assert "visible_runs has" in hint or "visible_runs har" in hint
    assert "started_at" in hint
    assert "lane" not in hint.split("har:")[-1].split("(")[0], \
        "lane findes IKKE i visible_runs og maa ikke staa i dens kolonneliste"


def test_hintet_tier_ved_en_fejl_der_ikke_handler_om_navne(conn):
    """Et hint der gaetter paa alt er stoej."""
    assert skema_hint(conn, "database is locked", "SELECT 1") == ""
    assert skema_hint(conn, "syntax error near \"SELEC\"", "SELEC 1") == ""


def test_tabelnavnet_fra_sql_interpoleres_ikke_raat(conn):
    """Navnet kommer fra modellens SQL. Det maa aldrig naa en raa streng.

    Uden parameterbinding ville et navn som dette vaere en indsproejtning —
    her skal det blot give et hint uden kolonner, og ingen undtagelse.
    """
    ond = 'SELECT x FROM "vr\\"; DROP TABLE costs; --"'
    hint = skema_hint(conn, "no such column: x", ond)
    assert conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE name='costs'").fetchone()[0] == 1
    assert isinstance(hint, str)


def test_kolonne_uden_genkendelig_tabel_siger_det_aerligt(conn):
    hint = skema_hint(conn, "no such column: foo", "SELECT foo")
    assert "foo" in hint
    assert "kunne ikke se tabellen" in hint


# ── Ende til ende gennem vaerktoejet ────────────────────────────────────────

def test_vaerktoejet_svarer_paa_en_gyldig_forespoergsel():
    res = _exec_db_query({"sql": "SELECT 1 AS x", "params": ""})
    assert res["status"] == "ok"
    assert res["rows"] == [{"x": 1}]


def test_vaerktoejet_afviser_ikke_select_og_siger_hvorfor():
    res = _exec_db_query({"sql": "DELETE FROM costs", "params": ""})
    assert res["status"] == "error"
    assert "read-only by design" in res["error"], \
        "18 af de 185 fejl var netop dette; afvisningen skal forklare sig"


def test_vaerktoejet_lægger_hintet_PAA_den_rigtige_fejl():
    """Hintet maa supplere fejlen, ikke erstatte den."""
    res = _exec_db_query({"sql": "SELECT noexist FROM costs", "params": ""})
    assert res["status"] == "error"
    assert "no such column" in res["error"], "den rigtige fejl skal stadig staa der"
    assert res.get("hint"), "og skemaet skal vaere lagt ved"
    assert "costs" in res["hint"]


def test_naert_traef_erstatter_den_lange_tabelliste(conn):
    """Er svaret i det naere traef, er listen 800 tegn stoej i historikken.

    Maalt mod produktionens 307 tabeller: «heartbeat_ticks» fik
    «heartbeat_runtime_ticks» som naermeste — og listen derudover hjalp intet.
    """
    hint = skema_hint(conn, "no such table: heartbeat_ticks",
                      "SELECT * FROM heartbeat_ticks")
    assert "heartbeat_state" in hint
    assert "costs" not in hint, "listen skal VAEK naar der er et naert traef"
    assert "3 tabeller i alt" in hint, "antallet skal stadig staa der"


def test_uden_naert_traef_kommer_listen_frem(conn):
    """Hjaelper det naere traef ikke, er listen det eneste vi har."""
    hint = skema_hint(conn, "no such table: zzqqxx", "SELECT * FROM zzqqxx")
    assert "costs" in hint and "visible_runs" in hint
