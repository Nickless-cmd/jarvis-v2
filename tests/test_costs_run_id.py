"""costs.run_id — eksakt run↔cost-kobling, verificeret mod en ægte DB.

FØR havde `costs` kun `created_at`, så enhver kobling var tidsheuristik. Den
gav en direkte forkert konklusion under latens-analysen 20. aug: TTFT-tal blev
matchet til de forkerte runs (15k-prompts forvekslet med 111k-runs), hvilket
fik cache-hit til at fremstå som latensens hovedårsag. Codex fandt fejlen.

Codex' anden note: den første version af disse tests var ren source-inspection
— de beviste at koden SÅ rigtig ud, ikke at værdien faktisk når disken.
`TestPersistence` skriver og læser derfor mod en rigtig SQLite-fil.
"""
from __future__ import annotations

import inspect
import sqlite3
from unittest.mock import patch

from core.costing.ledger import record_cost


class TestPersistence:
    """Den ægte prøve: når run_id disken, og kan den læses tilbage?"""

    def _db(self, tmp_path):
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
                user_id TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL)
        """)
        con.commit()
        return path, con

    def _patched(self, con):
        """record_cost lukker sin connection via context manager — hold den åben."""
        class _Keep:
            def __enter__(_s):
                return con

            def __exit__(_s, *a):
                return False
        return patch("core.costing.ledger.connect", return_value=_Keep())

    def test_run_id_skrives_og_kan_laeses_tilbage(self, tmp_path):
        path, con = self._db(tmp_path)
        with self._patched(con):
            record_cost(lane="visible", provider="deepseek", model="deepseek-v4-flash",
                        input_tokens=108776, cache_hit_tokens=6272,
                        run_id="visible-abc123")
        con.commit()
        row = sqlite3.connect(str(path)).execute(
            "SELECT run_id, input_tokens, cache_hit_tokens FROM costs").fetchone()
        assert row[0] == "visible-abc123", "run_id nåede ikke disken"
        assert row[1] == 108776 and row[2] == 6272, "de øvrige felter må ikke forskubbes"

    def test_uden_run_id_bliver_tom_streng_ikke_NULL(self, tmp_path):
        """Interne kald uden run-kontekst skal give '' — NOT NULL-kolonnen
        ville ellers afvise indsættelsen og tabe hele cost-registreringen."""
        path, con = self._db(tmp_path)
        with self._patched(con):
            record_cost(lane="cheap", provider="groq", model="llama", input_tokens=10)
        con.commit()
        row = sqlite3.connect(str(path)).execute("SELECT run_id FROM costs").fetchone()
        assert row[0] == ""

    def test_kolonne_raekkefoelge_stemmer_med_INSERT(self, tmp_path):
        """Regression mod en forskudt VALUES-liste: user_id og run_id står ved
        siden af hinanden, så en byttet rækkefølge ville være tavs."""
        path, con = self._db(tmp_path)
        with self._patched(con):
            record_cost(lane="visible", provider="deepseek", model="m",
                        user_id="bjorn", run_id="visible-xyz")
        con.commit()
        uid, rid = sqlite3.connect(str(path)).execute(
            "SELECT user_id, run_id FROM costs").fetchone()
        assert (uid, rid) == ("bjorn", "visible-xyz"), "felterne er byttet om"


class TestSignatur:
    def test_run_id_er_valgfri_keyword_only(self):
        p = inspect.signature(record_cost).parameters
        assert "run_id" in p and p["run_id"].default == ""
        assert p["run_id"].kind == inspect.Parameter.KEYWORD_ONLY


class TestSkema:
    def test_migration_er_idempotent_og_index_ikke_unikt(self):
        import core.runtime.db_schema as sch
        src = inspect.getsource(sch)
        assert 'if "run_id" not in _cost_cols' in src, "ALTER skal være betinget"
        assert "CREATE INDEX IF NOT EXISTS idx_costs_run_id" in src
        assert "UNIQUE" not in src.split("idx_costs_run_id")[1][:80], \
            "index må IKKE være unikt — ét run har flere cost-rækker"


class TestKaldesteder:
    def test_begge_visible_runs_kald_sender_run_id(self):
        """To record_cost-kald: den agentiske gren (lane="visible") og den
        generelle (lane=run.lane). Binder kun det ene, er halvdelen af turene
        stadig kun tidsmatchbare."""
        from core.services import visible_runs
        blocks = inspect.getsource(visible_runs).split("record_cost(")[1:]
        assert len(blocks) >= 2
        for i, b in enumerate(blocks[:2]):
            assert "run_id=" in b[:b.index(")")], f"kald #{i + 1} mangler run_id"
