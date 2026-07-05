import pytest
from central_cli.hud import CentralHud


@pytest.mark.asyncio
async def test_overview_renders_cost_breakdown():
    class FC:
        def get_json(self, p, params=None):
            if "realtime" in p:
                return {"status": "green", "coverage": {}, "incidents": [],
                        "open_breakers": [], "clusters": [], "feed": []}
            if "costs-daily" in p:
                return {"today_cost": 3.5, "week_cost": 9.0,
                        "days": [{"day": "2026-07-05", "lane": "primary",
                                  "total_cost": 3.5, "calls": 2, "total_tokens": 100}]}
            return {}
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 40)):
        app.show_tab("overview")
        assert app.active_tab == "overview"
