from __future__ import annotations
import pytest
from central_cli.hud import CentralHud


class FakeClient:
    def get_json(self, path, params=None):
        if path == "/central/realtime":
            return {"status": "yellow", "coverage": {"nerves": 122, "clusters": 21},
                    "open_breakers": [], "incidents": [{"cluster": "network", "nerve": "health", "severity": "error", "message": "x", "ts": 1}],
                    "feed": [{"cluster": "infra", "nerve": "pfsense_security", "decision": "error", "reason": "scan"}]}
        if path == "/central/timeseries":
            return {"series": {"network:health": {"api": {"count": 970, "latest": 1.0, "meta": {"state": "degraded"},
                    "ts": "2026-07-05T14:57:42+00:00", "recent": [1.0, 2.0, 3.0]}}}}
        return {}


@pytest.mark.asyncio
async def test_hud_boots_with_tabs_and_nerves():
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test() as pilot:
        assert app.query_one("#hud-head") is not None
        assert app.query_one("#hud-tabs") is not None
        assert app.query_one("#nerve-table") is not None
        assert app.query_one("#hud-feed") is not None
        # populate from the fake datasource
        app.refresh_data()
        # tab switch works
        app.show_tab("incidents")
        assert app.active_tab == "incidents"
        app.show_tab("nerves")
        assert app.active_tab == "nerves"
