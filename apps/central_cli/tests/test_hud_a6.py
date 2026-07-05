from __future__ import annotations

import pytest

from central_cli.hud import CentralHud


_REALTIME = {
    "status": "green", "coverage": {}, "incidents": [],
    "open_breakers": [], "clusters": [], "feed": [],
}


class FC:
    """Fake client: /central/runs returns one completed run; scheduled empty."""

    def get_json(self, path, params=None):
        if "realtime" in path:
            return dict(_REALTIME)
        if path == "/central/runs":
            return {"runs": [{
                "run_id": "r-123", "lane": "primary", "status": "completed",
                "model": "deepseek", "provider": "x", "text_preview": "hej",
            }], "count": 1, "failed_count": 0}
        if path == "/central/queues/scheduled":
            return {"tasks": []}
        return {}

    def post_json(self, path, body):
        return {"ok": True}


class FCEmpty:
    """Fake client with no runs."""

    def get_json(self, path, params=None):
        if "realtime" in path:
            return dict(_REALTIME)
        if path == "/central/runs":
            return {"runs": [], "count": 0, "failed_count": 0}
        if path == "/central/queues/scheduled":
            return {"tasks": []}
        return {}

    def post_json(self, path, body):
        return {"ok": True}


class FCInjection:
    """Fake client whose run_id carries markup brackets — must not crash."""

    def get_json(self, path, params=None):
        if "realtime" in path:
            return dict(_REALTIME)
        if path == "/central/runs":
            return {"runs": [{
                "run_id": "r-[bold]x", "lane": "pri[mary]", "status": "fai[led]",
                "model": "m[odel]", "provider": "p", "text_preview": "t[ext]",
                "error": "e[rr]",
            }]}
        if path == "/central/queues/scheduled":
            return {"tasks": [{"title": "s[1]", "status": "pen[ding]"}]}
        return {}

    def post_json(self, path, body):
        return {"ok": True}


@pytest.mark.asyncio
async def test_runs_tab_renders_recent_runs():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("runs")
        assert app.active_tab == "runs"
        from textual.widgets import DataTable
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 1


@pytest.mark.asyncio
async def test_runs_tab_empty_shows_info_row():
    app = CentralHud(client=FCEmpty(), live=False)
    async with app.run_test(size=(150, 45)):
        from textual.widgets import DataTable
        app.show_tab("runs")
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 1  # single info row


@pytest.mark.asyncio
async def test_runs_tab_header_shows_scheduled_count():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("runs")
        header = str(app.query_one("#main-paneh").render())
        assert "planlagte" in header
        assert "seneste" in header


@pytest.mark.asyncio
async def test_runs_tab_markup_injection_safe():
    app = CentralHud(client=FCInjection(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("runs")
        assert app.active_tab == "runs"
        from textual.widgets import DataTable
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 1
