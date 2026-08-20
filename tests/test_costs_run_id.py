"""costs.run_id — eksakt kobling mellem et run og dets omkostning.

FØR havde `costs` kun `created_at`, så enhver kobling var tidsheuristik. Den
heuristik gav en direkte forkert konklusion under latens-analysen 20. aug:
TTFT-tal blev matchet til de forkerte runs (15k-prompts forvekslet med
111k-runs), hvilket fik cache-hit til at fremstå som latensens hovedårsag.
Codex fandt fejlen. run_id fjerner gættet.

Bagudkompatibelt: historiske rækker og interne kald uden run-kontekst
beholder tom streng.
"""
from __future__ import annotations

import inspect

from core.costing.ledger import record_cost


class TestSignatur:
    def test_run_id_er_valgfri_med_tom_default(self):
        """Interne kald uden run-kontekst må ikke knække."""
        p = inspect.signature(record_cost).parameters
        assert "run_id" in p, "run_id mangler i record_cost"
        assert p["run_id"].default == "", "skal defaulte til tom streng"

    def test_run_id_er_keyword_only(self):
        """Hele signaturen er keyword-only — positionelle kald ville ellers
        kunne ramme det forkerte felt ved en senere omrokering."""
        p = inspect.signature(record_cost).parameters
        assert p["run_id"].kind == inspect.Parameter.KEYWORD_ONLY


class TestSkema:
    def test_kolonne_og_index_oprettes(self):
        """Migrationen skal være idempotent (ALTER kun hvis kolonnen mangler)
        og lægge et ikke-unikt index — flere cost-rækker pr. run er normalt."""
        import core.runtime.db_schema as sch
        src = inspect.getsource(sch)
        assert 'ADD COLUMN run_id TEXT NOT NULL DEFAULT \'\'' in src
        assert 'if "run_id" not in _cost_cols' in src, "migration skal være idempotent"
        assert "CREATE INDEX IF NOT EXISTS idx_costs_run_id" in src
        assert "UNIQUE" not in src.split("idx_costs_run_id")[1][:80], \
            "index må IKKE være unikt — et run har flere cost-rækker"

    def test_insert_medtager_run_id(self):
        import core.costing.ledger as ledger
        src = inspect.getsource(ledger)
        insert = src.split("INSERT INTO costs")[1][:400]
        assert "run_id" in insert, "INSERT skal skrive run_id"
        assert insert.count("?") == 11, "kolonner og pladsholdere skal stemme"


class TestKaldesteder:
    def test_begge_visible_runs_kald_sender_run_id(self):
        """Der er TO record_cost-kald i visible_runs: den agentiske gren
        (lane="visible") og den generelle (lane=run.lane). Begge skal binde,
        ellers er halvdelen af turene stadig kun tidsmatchbare."""
        from core.services import visible_runs
        src = inspect.getsource(visible_runs)
        blocks = src.split("record_cost(")[1:]
        assert len(blocks) >= 2, "forventede mindst to record_cost-kald"
        for i, b in enumerate(blocks[:2]):
            body = b[:b.index(")")]
            assert "run_id=" in body, f"record_cost-kald #{i + 1} mangler run_id"
