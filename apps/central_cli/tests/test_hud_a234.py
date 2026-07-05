from __future__ import annotations

import pytest

from central_cli.hud import CentralHud, _TABLE_TABS


_REALTIME = {
    "status": "green", "coverage": {}, "incidents": [],
    "open_breakers": [], "clusters": [], "feed": [],
}


class FC:
    """Fake client serving the three live central endpoints (+ realtime boot)."""

    def get_json(self, path, params=None):
        if "realtime" in path:
            return dict(_REALTIME)
        if path == "/central/queues/scheduled":
            return {"tasks": [
                {"title": "x", "next_run": "2026-07-05T10:00Z", "status": "pending"},
            ]}
        if path == "/central/autonomy":
            return {
                "proposals": [{"title": "y", "kind": "z", "status": "pending"}],
                "pending_count": 1,
            }
        if path == "/central/council":
            return {"sessions": [{"id": "c1"}, {"id": "c2"}]}
        return {}

    def post_json(self, path, body):
        return {"ok": True}


class FCEmpty:
    """Fake client with empty scheduled/autonomy/council payloads."""

    def get_json(self, path, params=None):
        if "realtime" in path:
            return dict(_REALTIME)
        if path == "/central/queues/scheduled":
            return {"tasks": []}
        if path == "/central/autonomy":
            return {"proposals": [], "pending_count": 0}
        if path == "/central/council":
            return {"sessions": []}
        return {}

    def post_json(self, path, body):
        return {"ok": True}


class FCInjection:
    """Fake client whose values contain markup brackets — must not crash."""

    def get_json(self, path, params=None):
        if "realtime" in path:
            return dict(_REALTIME)
        if path == "/central/queues/scheduled":
            return {"tasks": [
                {"title": "x[y]", "next_run": "no[w]", "status": "pen[ding]"},
            ]}
        if path == "/central/autonomy":
            return {
                "proposals": [{"title": "a[b]", "kind": "c[d]", "status": "e[f]"}],
                "pending_count": 1,
            }
        if path == "/central/council":
            return {"sessions": [{"id": "c[1]"}]}
        return {}

    def post_json(self, path, body):
        return {"ok": True}


# -- tab-set membership ------------------------------------------------------
def test_runs_and_approvals_and_agents_are_table_tabs():
    assert "runs" in _TABLE_TABS
    assert "approvals" in _TABLE_TABS
    assert "agents" in _TABLE_TABS


# -- HUD render --------------------------------------------------------------
@pytest.mark.asyncio
async def test_runs_tab_renders_scheduled():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("runs")
        assert app.active_tab == "runs"
        from textual.widgets import DataTable
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 1


@pytest.mark.asyncio
async def test_approvals_tab_renders_autonomy():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("approvals")
        assert app.active_tab == "approvals"
        from textual.widgets import DataTable
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 1


@pytest.mark.asyncio
async def test_agents_tab_includes_council():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("agents")
        assert app.active_tab == "agents"
        header = str(app.query_one("#main-paneh").render())
        assert "råds-sessioner" in header


@pytest.mark.asyncio
async def test_empty_scheduled_and_autonomy_render_info_row():
    app = CentralHud(client=FCEmpty(), live=False)
    async with app.run_test(size=(150, 45)):
        from textual.widgets import DataTable
        app.show_tab("runs")
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 1  # single info row
        app.show_tab("approvals")
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 1  # single info row


@pytest.mark.asyncio
async def test_markup_injection_safe_across_tabs():
    app = CentralHud(client=FCInjection(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("runs")
        assert app.query_one("#nerve-table").row_count == 1
        app.show_tab("approvals")
        assert app.query_one("#nerve-table").row_count == 1
        app.show_tab("agents")
        assert app.active_tab == "agents"
