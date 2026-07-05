import pytest
from central_cli.hud import CentralHud


class FC:
    """Fake client — inner-life + experiment med aktive + stille sektioner."""

    def get_json(self, path, params=None):
        if "inner-life" in path:
            return {"inner_life": {
                "inner_life": {
                    "thought_stream": {"liveness": True, "count": 5},
                    "dream": {"liveness": False, "count": 0},
                },
                "experiment": {
                    "adaptive_learning": {"liveness": True, "count": 3},
                    "loop_runtime": {"liveness": False, "count": 0},
                },
                "live_count": 2,
                "total": 4,
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
    """Sektion-navne med markup-farlig content i BEGGE grupper → _esc undgår crash."""

    def get_json(self, path, params=None):
        if "inner-life" in path:
            return {"inner_life": {
                "inner_life": {"[bold]evil[/]": {"liveness": True, "count": 1}},
                "experiment": {"[red]boom[/]": {"liveness": True, "count": 1}},
                "live_count": 2,
                "total": 2,
            }}
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


class FCEmptyInnerLife:
    """Tomme grupper → '— stille —', self-safe."""

    def get_json(self, path, params=None):
        if "inner-life" in path:
            return {"inner_life": {"inner_life": {}, "experiment": {},
                                   "live_count": 0, "total": 0}}
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


@pytest.mark.asyncio
async def test_mind_tab_renders_inner_life_and_experiment():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"


@pytest.mark.asyncio
async def test_mind_tab_markup_dangerous_no_crash_both_groups():
    app = CentralHud(client=FCMarkupInnerLife(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"


@pytest.mark.asyncio
async def test_mind_tab_empty_is_self_safe():
    app = CentralHud(client=FCEmptyInnerLife(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"
