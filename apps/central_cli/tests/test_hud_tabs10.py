from __future__ import annotations

import pytest

from central_cli.hud import CentralHud, _TABS


def test_ten_tabs_in_order():
    """Rækkefølgen er aftalt, ikke tilfældig — den er fanernes plads på tasterne.

    Navnet siger «ten» af historiske grunde (og refereres i
    docs/superpowers/plans/2026-07-05-central-absorbs-everything.md); der er
    seksten nu.

    Var RØD fra 13/9-2026 til 6/10: `f25d3b667` (Actor: opus) indsatte
    «work»-fanen i hud.py og opdaterede ikke denne liste. Arbejds-cockpittet
    var «bygget, korrekt og usynligt», og testen der skulle fange netop en
    usynlig fane blev efterladt rød i tre uger.
    """
    keys = [k for k, _, _ in _TABS]
    # 6. jul: Connections + Users + Excess + Decentral tilføjet (dagens nye nerver, owner-only)
    # 13. jul: Balancer indsat umiddelbart efter agents (cheap-lane pool)
    # 13. sep: Work indsat EFTER incidents og FØR runs — arbejds-cockpittet
    #          hører til ved hændelserne, ikke nede ved de planlagte kørsler.
    assert keys == ["overview", "nerves", "clusters", "incidents", "work",
                    "runs", "approvals", "agents", "balancer", "connections",
                    "users", "excess", "decentral", "mind", "diagnostics",
                    "governance"]
    # Hver tabel-fane skal også STÅ i _TABLE_TABS, ellers får den ingen tabel.
    # «work» manglede ikke dér — men det er den anden halvdel af samme fejl,
    # og en liste der kun tjekkes i én retning fanger ikke en halv tilføjelse.
    from central_cli.hud import _TABLE_TABS
    ukendte = _TABLE_TABS - set(keys) - {"anomalies"}
    assert not ukendte, f"_TABLE_TABS nævner faner der ikke findes: {ukendte}"


@pytest.mark.asyncio
async def test_all_ten_tabs_show_without_crash():
    class FC:
        def get_json(self, p, params=None):
            if "realtime" in p:
                return {"status": "green", "coverage": {}, "incidents": [],
                        "open_breakers": [], "clusters": [], "feed": []}
            return {}

        def post_json(self, p, b):
            return {"ok": True}

    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 40)):
        for k, _, _ in _TABS:
            app.show_tab(k)
            assert app.active_tab == k


@pytest.mark.asyncio
async def test_runs_and_approvals_are_wired_table_tabs():
    """runs (scheduled) and approvals (autonomy) are now wired TABLE tabs.
    With empty payloads they render a single info row without crashing
    (see test_hud_a234.py for the populated cases)."""
    from textual.widgets import DataTable

    class FC:
        def get_json(self, p, params=None):
            if "realtime" in p:
                return {"status": "green", "coverage": {}, "incidents": [],
                        "open_breakers": [], "clusters": [], "feed": []}
            return {}

        def post_json(self, p, b):
            return {"ok": True}

    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 40)):
        for tab in ("runs", "approvals"):
            app.show_tab(tab)
            assert app.active_tab == tab
            table = app.query_one("#nerve-table", DataTable)
            assert table.row_count == 1  # single info row
