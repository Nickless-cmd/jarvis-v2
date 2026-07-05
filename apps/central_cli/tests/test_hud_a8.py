import pytest
from central_cli.hud import CentralHud


class FC:
    """Fake client — inner-life med én aktiv + én stille sektion."""

    def get_json(self, path, params=None):
        if "inner-life" in path:
            return {"inner_life": {
                "sections": {
                    "thought_stream": {"liveness": True, "count": 5},
                    "dream": {"liveness": False, "count": 0},
                },
                "live_count": 1,
                "total": 2,
            }}
        if "memory-health" in path:
            return {}
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        if path.endswith("/central/self") or "self" in path:
            return {}
        return {}


class FCMarkupInnerLife:
    """Sektion-navn med markup-farlig content → _esc forhindrer crash."""

    def get_json(self, path, params=None):
        if "inner-life" in path:
            return {"inner_life": {
                "sections": {"[bold]evil[/]": {"liveness": True, "count": 1}},
                "live_count": 1,
                "total": 1,
            }}
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


class FCEmptyInnerLife:
    """Tom inner-life → '— stille —', self-safe."""

    def get_json(self, path, params=None):
        if "inner-life" in path:
            return {"inner_life": {"sections": {}, "live_count": 0, "total": 0}}
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


@pytest.mark.asyncio
async def test_mind_tab_renders_inner_life():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"


@pytest.mark.asyncio
async def test_mind_tab_inner_life_markup_dangerous_no_crash():
    app = CentralHud(client=FCMarkupInnerLife(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"


@pytest.mark.asyncio
async def test_mind_tab_empty_inner_life_is_self_safe():
    app = CentralHud(client=FCEmptyInnerLife(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"
