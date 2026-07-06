from __future__ import annotations

import pytest

from central_cli.hud import CentralHud, _TABS


def test_ten_tabs_in_order():
    keys = [k for k, _, _ in _TABS]
    # 6. jul: Connections + Users + Excess + Decentral tilføjet (dagens nye nerver, owner-only)
    assert keys == ["overview", "nerves", "clusters", "incidents", "runs",
                    "approvals", "agents", "connections", "users", "excess", "decentral",
                    "mind", "diagnostics", "governance"]


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
