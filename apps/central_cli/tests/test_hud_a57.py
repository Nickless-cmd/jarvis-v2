import pytest
from central_cli.hud import CentralHud


class FC:
    """Fake client — returns shaped dicts per path."""

    def get_json(self, path, params=None):
        if "memory-health" in path:
            return {"added_today": 112, "journal_today": False, "memory": {}}
        if "events" in path:
            return {"items": [
                {"family": "tool", "kind": "tool.called"},
                {"family": "cognitive_state", "kind": "x"},
            ]}
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        if path.endswith("/central/self") or "self" in path:
            return {}
        return {}


class FCEmptyMemory:
    """Memory-health empty → self-safe, no crash."""

    def get_json(self, path, params=None):
        if "memory-health" in path:
            return {}
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


class FCMarkupEvents:
    """Events with markup-dangerous content → _esc prevents crash."""

    def get_json(self, path, params=None):
        if "events" in path:
            return {"items": [{"family": "[bold]x", "kind": "[/]boom"}]}
        if "realtime" in path:
            return {"status": "green", "coverage": {}, "incidents": [],
                    "open_breakers": [], "clusters": [], "feed": []}
        return {}


@pytest.mark.asyncio
async def test_mind_tab_renders_memory():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"


@pytest.mark.asyncio
async def test_diagnostics_tab_renders_events():
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("diagnostics")
        assert app.active_tab == "diagnostics"


@pytest.mark.asyncio
async def test_mind_tab_empty_memory_is_self_safe():
    app = CentralHud(client=FCEmptyMemory(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("mind")
        assert app.active_tab == "mind"


@pytest.mark.asyncio
async def test_diagnostics_events_markup_dangerous_no_crash():
    app = CentralHud(client=FCMarkupEvents(), live=False)
    async with app.run_test(size=(150, 45)):
        app.show_tab("diagnostics")
        assert app.active_tab == "diagnostics"
