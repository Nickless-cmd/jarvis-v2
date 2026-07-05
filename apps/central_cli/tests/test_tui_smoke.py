from __future__ import annotations
import pytest
from central_cli.tui import CentralApp


@pytest.mark.asyncio
async def test_app_boots_and_has_three_panes():
    app = CentralApp(base_url="http://x", token="T", live=False)  # live=False → ingen netværk
    async with app.run_test() as pilot:
        assert app.query_one("#feed") is not None
        assert app.query_one("#output") is not None
        assert app.query_one("#cmdbar") is not None
        app._last_dispatched = None
        await app._run_command("status")
        assert app._last_dispatched == "status"
