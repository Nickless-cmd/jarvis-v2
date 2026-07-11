import pytest
from central_cli.engine.state import HudState
from central_cli.frame.app import CockpitApp


@pytest.mark.asyncio
async def test_cursor_survives_refresh_and_enter_drills(fake_client):
    app = CockpitApp(client=fake_client, state=HudState())
    async with app.run_test() as pilot:
        await app.seed_now()                 # synkron seed så tabellen har rækker
        await app.switch_tab("incidents")
        await pilot.pause()
        table = app.active_table()
        table.move_cursor(row=2)
        key_before = table._selected_key()
        app.rerender_active()                # simulér refresh-tick
        await pilot.pause()
        assert table._selected_key() == key_before   # markør IKKE hoppet
        await pilot.press("enter")           # drill ind
        await pilot.pause()
        assert app.screen_stack[-1].__class__.__name__ == "IncidentDetailScreen"
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen_stack[-1].__class__.__name__ != "IncidentDetailScreen"
