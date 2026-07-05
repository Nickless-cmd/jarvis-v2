import pytest
from central_cli.hud import CentralHud


class FC:
    """Fake client — soul med aktive + stille signaler."""

    def get_json(self, path, params=None):
        if "/central/soul" in path:
            return {
                "signals": {
                    "longing": {"liveness": True, "count": 3},
                    "identity_drift": {"liveness": False, "count": 0},
                },
                "live_count": 1,
                "total": 2,
            }
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


class FCMarkupSoul:
    """Signal-navne med markup-farlig content → _esc undgår crash."""

    def get_json(self, path, params=None):
        if "/central/soul" in path:
            return {
                "signals": {"[bold]evil[/]": {"liveness": True, "count": 1}},
                "live_count": 1,
                "total": 1,
            }
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


class FCEmptySoul:
    """Tomme signaler → '— stille —', self-safe."""

    def get_json(self, path, params=None):
        if "/central/soul" in path:
            return {"signals": {}, "live_count": 0, "total": 0}
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


@pytest.mark.asyncio
async def test_mind_tab_renders_soul():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"


@pytest.mark.asyncio
async def test_mind_tab_soul_markup_no_crash():
    app = CentralHud(client=FCMarkupSoul(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"


@pytest.mark.asyncio
async def test_mind_tab_soul_empty_is_self_safe():
    app = CentralHud(client=FCEmptySoul(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"
