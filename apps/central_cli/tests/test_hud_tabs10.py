from __future__ import annotations

import pytest

from central_cli.hud import CentralHud, _TABS


def test_ten_tabs_in_order():
    keys = [k for k, _, _ in _TABS]
    assert keys == ["overview", "nerves", "clusters", "incidents", "runs",
                    "approvals", "agents", "mind", "diagnostics", "governance"]


@pytest.mark.asyncio
async def test_all_ten_tabs_show_without_crash():
    class FC:
        def get_json(self, p, params=None):
            if "realtime" in p:
                return {"status": "green", "coverage": {}, "incidents": [],
                        "open_breakers": [], "clusters": [], "feed": []}
            return {}

        def post_json(self, p, b):
            return {"ok": True}

    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 40)):
        for k, _, _ in _TABS:
            app.show_tab(k)
            assert app.active_tab == k


@pytest.mark.asyncio
async def test_new_tabs_render_placeholder_without_crash():
    """The not-yet-wired tabs (runs/approvals/agents/mind) are PANEL tabs that
    render a 'venter på wiring' placeholder without crashing."""
    class FC:
        def get_json(self, p, params=None):
            if "realtime" in p:
                return {"status": "green", "coverage": {}, "incidents": [],
                        "open_breakers": [], "clusters": [], "feed": []}
            return {}

        def post_json(self, p, b):
            return {"ok": True}

    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150, 40)):
        for tab in ("runs", "approvals", "agents", "mind"):
            app.show_tab(tab)
            assert app.active_tab == tab
            # placeholder tabs are panel tabs (not table tabs)
            assert app.query_one("#hud-panel").display is True
            rendered = str(app.query_one("#hud-panel").render())
            assert "venter" in rendered
