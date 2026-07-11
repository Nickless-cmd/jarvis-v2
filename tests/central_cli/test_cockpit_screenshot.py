import pytest
from central_cli.engine.state import HudState
from central_cli.frame.app import CockpitApp


@pytest.mark.asyncio
async def test_screenshot_incidents_tab(fake_client, tmp_path):
    app = CockpitApp(client=fake_client, state=HudState())
    async with app.run_test(size=(120, 40)) as pilot:
        await app.seed_now()
        await app.switch_tab("incidents")
        # lad display-toggle + row-render settle før capture (ellers tom body)
        await pilot.pause()
        app.rerender_active()
        await pilot.pause()
        svg = tmp_path / "cockpit-incidents.svg"
        app.save_screenshot(str(svg))
        assert svg.exists() and svg.stat().st_size > 1000
        # kopiér til en stabil sti så den kan inspiceres udenfor tmp
        import shutil
        dest = "/tmp/cockpit-incidents.svg"
        shutil.copy(str(svg), dest)
        print(f"SCREENSHOT_SVG: {dest}")
