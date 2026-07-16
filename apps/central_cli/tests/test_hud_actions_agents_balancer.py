from __future__ import annotations

import pytest

from central_cli.hud import CentralHud


_REALTIME = {
    "status": "green", "coverage": {}, "incidents": [],
    "open_breakers": [], "clusters": [], "feed": [],
}


class FakeClient:
    """Records every POST as (path, body); GETs return self-safe empties."""

    def __init__(self):
        self.posts: list = []

    def get_json(self, path, params=None):
        if "realtime" in path:
            return dict(_REALTIME)
        return {}

    def post_json(self, path, body):
        self.posts.append((path, body))
        return {"ok": True}


def _paths(client):
    return [p for p, _ in client.posts]


# -- bindings ----------------------------------------------------------------
def test_action_bindings_registered_without_collision():
    actions = {}
    for b in CentralHud.BINDINGS:
        key = getattr(b, "key", None)
        action = getattr(b, "action", None)
        if key is not None:
            actions[key] = action
    assert actions.get("p") == "agent_pause"
    assert actions.get("x") == "agent_abort"
    assert actions.get("r") == "slot_reset"
    assert actions.get("d") == "slot_disable"
    assert actions.get("e") == "slot_enable"
    # the letters must not clash with any pre-existing binding key
    keys = [getattr(b, "key", None) for b in CentralHud.BINDINGS]
    assert len(keys) == len(set(keys)), "duplicate binding keys"


# -- agent pause -------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_pause_active_posts():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("agents")
        app._agent_rows = [{"agent_id": "agent-7", "status": "active", "role": "x"}]
        app.action_agent_pause()
        assert ("/central/agents/agent-7/pause", {}) in c.posts


@pytest.mark.asyncio
async def test_agent_pause_non_active_no_post():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("agents")
        app._agent_rows = [{"agent_id": "agent-7", "status": "idle", "role": "x"}]
        app.action_agent_pause()
        assert not any("/pause" in p for p in _paths(c))


# -- agent abort (dangerous confirm) -----------------------------------------
@pytest.mark.asyncio
async def test_agent_abort_requires_confirm_then_posts():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("agents")
        app._agent_rows = [{"agent_id": "agent-9", "status": "active"}]
        app.action_agent_abort()
        # armed a pending confirm, NO post yet
        assert app._pending_write is not None
        assert not any("/cancel" in p for p in _paths(c))
        # confirm -> posts to cancel
        app.action_confirm_yes()
        assert ("/central/agents/agent-9/cancel", {}) in c.posts
        assert app._pending_write is None


@pytest.mark.asyncio
async def test_agent_abort_confirm_no_does_not_post():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("agents")
        app._agent_rows = [{"agent_id": "agent-9", "status": "active"}]
        app.action_agent_abort()
        app.action_confirm_no()
        assert app._pending_write is None
        assert not any("/cancel" in p for p in _paths(c))


# -- balancer slot reset / disable / enable ----------------------------------
@pytest.mark.asyncio
async def test_slot_reset_posts():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("balancer")
        app._balancer_rows = [{"slot_id": "deepseek::default::home",
                               "status": "healthy", "raw": {}}]
        app.action_slot_reset()
        assert ("/mc/cheap-balancer/slot/deepseek::default::home/reset", {}) in c.posts


@pytest.mark.asyncio
async def test_slot_enable_posts():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("balancer")
        app._balancer_rows = [{"slot_id": "kimi::account2::vpn",
                               "status": "disabled", "raw": {}}]
        app.action_slot_enable()
        assert ("/mc/cheap-balancer/slot/kimi::account2::vpn/enable", {}) in c.posts


@pytest.mark.asyncio
async def test_slot_disable_requires_confirm_then_posts():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("balancer")
        app._balancer_rows = [{"slot_id": "kimi::account2::vpn",
                               "status": "healthy", "raw": {}}]
        app.action_slot_disable()
        assert app._pending_write is not None
        assert not any("/disable" in p for p in _paths(c))
        app.action_confirm_yes()
        assert ("/mc/cheap-balancer/slot/kimi::account2::vpn/disable", {}) in c.posts
        assert app._pending_write is None


# -- tab gating --------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_pause_gated_off_wrong_tab():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("balancer")
        app._agent_rows = [{"agent_id": "agent-7", "status": "active"}]
        app.action_agent_pause()
        assert not any("/pause" in p for p in _paths(c))


@pytest.mark.asyncio
async def test_slot_reset_gated_off_wrong_tab():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("agents")
        app._balancer_rows = [{"slot_id": "x::y::z", "status": "healthy", "raw": {}}]
        app.action_slot_reset()
        assert not any("cheap-balancer" in p for p in _paths(c))


# -- check_action gating (typing not stolen) ---------------------------------
@pytest.mark.asyncio
async def test_check_action_lets_letters_type_when_cmdline_nonempty():
    from textual.widgets import Input
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("agents")
        inp = app.query_one("#hud-cmd-input", Input)
        inp.value = "reset"
        # while typing, the single-letter actions must be disabled so the
        # keystroke falls through to the command line
        assert app.check_action("agent_pause", ()) is False
        assert app.check_action("slot_reset", ()) is False
        inp.value = ""
        assert app.check_action("agent_pause", ()) is True


@pytest.mark.asyncio
async def test_check_action_gates_by_tab():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test():
        app.show_tab("agents")
        assert app.check_action("agent_pause", ()) is True
        assert app.check_action("slot_reset", ()) is False
        app.show_tab("balancer")
        assert app.check_action("slot_reset", ()) is True
        assert app.check_action("agent_pause", ()) is False
