from __future__ import annotations

import pytest

from central_cli.hud import CentralHud, _TABS, _TABLE_TABS


_REALTIME = {
    "status": "green", "coverage": {}, "incidents": [],
    "open_breakers": [], "clusters": [], "feed": [],
}

# A known balancer snapshot: two slots — one healthy/home, one cooldown/vpn.
_BALANCER = {
    "header": {
        "total_slots": 2, "healthy": 1, "cooldown": 1, "disabled": 0,
        "stale": 0, "breaker": 0,
        "by_profile": {"default": 1, "account2": 1},
        "by_egress": {"home": 1, "vpn": 1},
        "providers": ["deepseek", "kimi"],
    },
    "slots": [
        {"slot_id": "deepseek::default::home", "provider": "deepseek",
         "model": "deepseek-chat", "auth_profile": "default", "egress": "home",
         "status": "healthy", "weight": 1.0, "daily_headroom": 0.8,
         "daily_used": 200, "daily_limit": 1000, "rpm_used": 3, "rpm_limit": 60,
         "last_success_at": "2026-07-16T10:00:00+00:00", "success_rate": 0.98,
         "daily_observed": True, "stale": False},
        {"slot_id": "kimi::account2::vpn", "provider": "kimi",
         "model": "kimi-k2", "auth_profile": "account2", "egress": "vpn",
         "status": "cooldown", "weight": 0.0, "daily_headroom": 0.0,
         "daily_used": 900, "daily_limit": 900, "rpm_used": 0, "rpm_limit": 30,
         "last_success_at": "", "success_rate": 0.5,
         "daily_observed": False, "stale": False,
         "cooldown_until": "2026-07-16T10:30:00+00:00", "breaker": "open"},
    ],
}


class FakeClient:
    def __init__(self, balancer=None):
        self._balancer = balancer if balancer is not None else _BALANCER

    def get_json(self, path, params=None):
        if "realtime" in path:
            return dict(_REALTIME)
        if path == "/mc/cheap-balancer-state":
            return self._balancer
        return {}

    def post_json(self, path, body):
        return {"ok": True}


# -- tab registration --------------------------------------------------------
def test_balancer_tab_registered_right_after_agents():
    keys = [k for k, _, _ in _TABS]
    assert "balancer" in keys
    assert keys.index("balancer") == keys.index("agents") + 1


def test_balancer_is_a_table_tab():
    assert "balancer" in _TABLE_TABS


# -- F-key binding -----------------------------------------------------------
def test_f8_binds_to_balancer():
    actions = {}
    for b in CentralHud.BINDINGS:
        key = getattr(b, "key", None)
        action = getattr(b, "action", None)
        if key is not None:
            actions[key] = action
    assert actions.get("f8") == "show('balancer')"


# -- HUD render --------------------------------------------------------------
@pytest.mark.asyncio
async def test_balancer_tab_populates_rows_and_header():
    from textual.widgets import DataTable

    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test(size=(170, 40)):
        app.show_tab("balancer")
        assert app.active_tab == "balancer"
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 2

        # both provider rows render
        providers = [str(table.get_row_at(i)[0]) for i in range(2)]
        assert any("deepseek" in p for p in providers)
        assert any("kimi" in p for p in providers)

        # header line shows the total slot count
        header = str(app.query_one("#main-paneh").render())
        assert "BALANCER" in header
        assert "2 slots" in header


@pytest.mark.asyncio
async def test_cooldown_row_status_is_not_healthy_style():
    from central_cli.hud_theme import GREEN, AMBER
    from rich.text import Text
    from textual.widgets import DataTable

    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test(size=(170, 40)):
        app.show_tab("balancer")
        table = app.query_one("#nerve-table", DataTable)

        cd = next(i for i in range(2)
                  if "kimi" in str(table.get_row_at(i)[0]))
        status_cell = table.get_row_at(cd)[4]
        assert isinstance(status_cell, Text)
        # cooldown must not be styled as the healthy (green) status
        assert status_cell.style != GREEN
        assert status_cell.style == AMBER

        # the healthy row uses the green status style + ● marker
        hp = next(i for i in range(2)
                  if "deepseek" in str(table.get_row_at(i)[0]))
        assert table.get_row_at(hp)[4].style == GREEN
        assert "●" in str(table.get_row_at(hp)[4])

        # detail panel for the cooldown slot surfaces its raw fields
        app._render_balancer_detail(cd)
        detail = str(app.query_one("#hud-detail").render())
        assert "kimi::account2::vpn" in detail
        assert "cooldown" in detail.lower()


@pytest.mark.asyncio
async def test_balancer_tab_empty_is_self_safe():
    from textual.widgets import DataTable

    empty = {"header": {}, "slots": []}
    app = CentralHud(client=FakeClient(balancer=empty), live=False)
    async with app.run_test(size=(170, 40)):
        app.show_tab("balancer")
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 1  # friendly placeholder row


@pytest.mark.asyncio
async def test_balancer_markup_injection_safe():
    bad = {
        "header": {"total_slots": 1, "healthy": 1, "cooldown": 0,
                   "by_profile": {"def[ault]": 1}, "by_egress": {"ho[me]": 1}},
        "slots": [
            {"slot_id": "s[1]", "provider": "prov[x]", "model": "m[y]",
             "auth_profile": "p[z]", "egress": "e[g]", "status": "heal[thy]",
             "weight": 1.0, "daily_headroom": 0.5, "daily_used": 1,
             "daily_limit": 2, "rpm_used": 0, "rpm_limit": 1,
             "last_success_at": "", "success_rate": 1.0,
             "daily_observed": True, "stale": False},
        ],
    }
    app = CentralHud(client=FakeClient(balancer=bad), live=False)
    async with app.run_test(size=(170, 40)):
        app.show_tab("balancer")
        assert app.query_one("#nerve-table").row_count == 1
        app._render_balancer_detail(0)
        detail = str(app.query_one("#hud-detail").render())
        assert "prov[x]" in detail
