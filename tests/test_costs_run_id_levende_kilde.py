"""Kørslens nøgle i `costs` — den levende kilde, ikke kun kalderens parameter.

MÅLT 19/11-2026: `costs.run_id` var tom i 1.144.881 rækker, og for lane='agent'
i ALLE 4.256. Kun 5 af 15 kaldesteder sendte `run_id` selv. Beløbene stod der —
men intet kunne henføres til den kørsel der brugte dem: 0 af 1.880 agent_runs
kunne kobles til en costs-række, så enhver pris pr. kørsel var en tidsheuristik.

Kilden fandtes hele tiden (`run_autonomy_context.set_run_identity`, sat af
rutiner, synlige runs og første-gennemløbet). `record_cost` spurgte den bare
aldrig — samme fejlform som session-resolveren, som blev rettet samme dag.

Disse tests skriver mod en rigtig SQLite-fil: en source-inspection ville kun
bevise at koden SER rigtig ud, ikke at værdien når disken.
"""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

from core.costing.ledger import record_cost
from core.services import run_autonomy_context as rac


def _db(tmp_path):
    path = tmp_path / "costs.db"
    con = sqlite3.connect(str(path))
    con.execute("""
        CREATE TABLE costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lane TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0,
            cache_hit_tokens INTEGER NOT NULL DEFAULT 0,
            cache_miss_tokens INTEGER NOT NULL DEFAULT 0,
            reasoning_tokens INTEGER NOT NULL DEFAULT 0,
            user_id TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL)
    """)
    con.commit()
    return path, con


def _patched(con):
    class _Keep:
        def __enter__(_s):
            return con

        def __exit__(_s, *a):
            return False
    return patch("core.costing.ledger.connect", return_value=_Keep())


@pytest.fixture(autouse=True)
def _ren_kontekst():
    """Hver test starter uden en kørsel — ellers arver den naboens identitet."""
    rac.set_run_identity("", "")
    yield
    rac.set_run_identity("", "")


def test_run_id_hentes_fra_den_levende_koersel(tmp_path):
    """Kaldesteder der ikke sender run_id skal alligevel binde rækken til kørslen.

    Det er de 10 af 15 kaldesteder — bl.a. cheap-lanen og daemon-kaldene.
    """
    path, con = _db(tmp_path)
    rac.set_run_identity("run-74633fe9f43f4bff", origin="agent")
    with _patched(con):
        record_cost(lane="agent", provider="deepseek", model="deepseek-v4-pro",
                    input_tokens=1000, output_tokens=100)
    con.commit()
    rid = sqlite3.connect(str(path)).execute("SELECT run_id FROM costs").fetchone()[0]
    assert rid == "run-74633fe9f43f4bff", "kørslens nøgle nåede ikke disken"


def test_kalderens_egen_run_id_vinder_over_konteksten(tmp_path):
    """En kalder der VED hvilket run den skriver for, må ikke overskrives.

    Ellers ville en agent der bogfører på vegne af et barn få forælderens nøgle.
    """
    path, con = _db(tmp_path)
    rac.set_run_identity("run-FORÆLDER", origin="agent")
    with _patched(con):
        record_cost(lane="agent", provider="deepseek", model="deepseek-v4-pro",
                    input_tokens=10, run_id="run-BARN")
    con.commit()
    rid = sqlite3.connect(str(path)).execute("SELECT run_id FROM costs").fetchone()[0]
    assert rid == "run-BARN"


def test_uden_koersel_bliver_det_tom_streng(tmp_path):
    """NOT NULL-kolonnen ville ellers afvise indsættelsen og tabe beløbet.

    En tom nøgle er ærlig: ingen kørsel at henføre til.
    """
    path, con = _db(tmp_path)
    with _patched(con):
        record_cost(lane="daemon", provider="groq", model="llama", input_tokens=5)
    con.commit()
    rid = sqlite3.connect(str(path)).execute("SELECT run_id FROM costs").fetchone()[0]
    assert rid == ""


def test_manglende_kontekst_modul_vaelter_ikke_bogfoeringen(tmp_path):
    """Bogføringen er vigtigere end koblingen: fejler kilden, skal beløbet stadig skrives."""
    path, con = _db(tmp_path)
    with patch.dict("sys.modules", {"core.services.run_autonomy_context": None}):
        with _patched(con):
            record_cost(lane="daemon", provider="deepseek", model="deepseek-v4-flash",
                        input_tokens=7)
    con.commit()
    row = sqlite3.connect(str(path)).execute("SELECT run_id, input_tokens FROM costs").fetchone()
    assert row == ("", 7), "beløbet må ikke tabe fordi koblingen ikke kunne slås op"
