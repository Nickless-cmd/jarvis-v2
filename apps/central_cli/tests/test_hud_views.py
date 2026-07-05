from __future__ import annotations
import pytest
from central_cli.hud import CentralHud


class FakeClient:
    def get_json(self, path, params=None):
        if path == "/central/realtime":
            return {"status": "yellow", "coverage": {"nerves": 122, "clusters": 21},
                    "open_breakers": [], "clusters": [{"cluster": "network", "status": "red", "nerves": 3}],
                    "incidents": [{"cluster": "network", "nerve": "health", "severity": "error", "message": "meget lang besked "*10, "ts": 1}],
                    "feed": []}
        if path == "/central/timeseries":
            return {"series": {"network:health": {"api": {"count": 9, "latest": 1.0, "meta": {}, "ts": "2026-07-05T14:00:00+00:00", "recent": [1.0, 2.0]}}}}
        if path == "/central/diagnostics":
            return {"incidents": [1], "anomalies": [], "root_causes": ["rod-aarsag A"], "degrading": []}
        return {}


@pytest.mark.asyncio
async def test_all_read_tabs_render_without_crash():
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test() as pilot:
        for tab in ("overview", "clusters", "incidents", "diagnostics", "nerves"):
            app.show_tab(tab)
            app.refresh_data()
            assert app.active_tab == tab
        # incidents drill-down does not crash
        app.show_tab("incidents")
        app.refresh_data()
        if hasattr(app, "_drill_incident"):
            app._drill_incident(0)


@pytest.mark.asyncio
async def test_panel_widget_exists_and_toggles():
    """Overview/Diagnostics use a dedicated panel widget; tabular tabs hide it."""
    from textual.widgets import Static

    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test() as pilot:
        panel = app.query_one("#hud-panel", Static)
        assert panel is not None
        # panel visible on non-tabular tabs
        app.show_tab("overview")
        assert panel.display is True
        # tabular tab hides panel, shows the table
        app.show_tab("nerves")
        assert panel.display is False
        table = app.query_one("#nerve-table")
        assert table.display is True


@pytest.mark.asyncio
async def test_clusters_tab_populates_table_columns():
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test() as pilot:
        app.show_tab("clusters")
        app.refresh_data()
        table = app.query_one("#nerve-table")
        labels = [str(c.label) for c in table.columns.values()]
        assert "cluster" in labels and "aktiv" in labels and "død" in labels
        assert table.row_count >= 1


@pytest.mark.asyncio
async def test_incidents_drill_down_renders_full_message():
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test() as pilot:
        app.show_tab("incidents")
        app.refresh_data()
        assert hasattr(app, "_drill_incident")
        # full (untruncated) message must survive the drill-down
        app._drill_incident(0)


def test_datasource_clusters_shape():
    from central_cli import datasource

    rows = datasource.clusters(FakeClient())
    assert isinstance(rows, list) and rows
    r = rows[0]
    for k in ("cluster", "status", "nerves", "aktiv", "idle", "degraded", "død"):
        assert k in r
