import pytest
from central_cli.hud import CentralHud


class FC:
    """Fake client — dark-products med aktive + stille signaler."""

    def get_json(self, path, params=None):
        if "/central/dark-products" in path:
            return {
                "signals": {
                    "apophenia": {"liveness": True, "count": 3},
                    "deep_reflection": {"liveness": False, "count": 0},
                },
                "live_count": 1,
                "total": 2,
            }
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


class FCMarkupDark:
    """Signal-navne med markup-farlig content → _esc undgår crash."""

    def get_json(self, path, params=None):
        if "/central/dark-products" in path:
            return {
                "signals": {"[bold]evil[/]": {"liveness": True, "count": 1}},
                "live_count": 1,
                "total": 1,
            }
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


class FCEmptyDark:
    """Tomme signaler → '— stille —', self-safe."""

    def get_json(self, path, params=None):
        if "/central/dark-products" in path:
            return {"signals": {}, "live_count": 0, "total": 0}
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


@pytest.mark.asyncio
async def test_mind_tab_renders_dark_products():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"


@pytest.mark.asyncio
async def test_mind_tab_dark_products_markup_no_crash():
    app = CentralHud(client=FCMarkupDark(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"


@pytest.mark.asyncio
async def test_mind_tab_dark_products_empty_is_self_safe():
    app = CentralHud(client=FCEmptyDark(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"
