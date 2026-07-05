from __future__ import annotations
import pytest
from central_cli.hud import CentralHud


class FakeClient:
    def __init__(self): self.posts = []
    def get_json(self, path, params=None):
        if path == "/central/realtime":
            return {"status": "green", "coverage": {"nerves": 1, "clusters": 1}, "open_breakers": [], "incidents": [], "feed": [], "clusters": []}
        if path == "/central/timeseries": return {"series": {}}
        if path == "/central/governance":
            return {"flags": [{"key": "self_prompt", "label": "self", "kind": "bool", "dangerous": False, "value": True, "options": None},
                              {"key": "generative_autonomy", "label": "gen", "kind": "bool", "dangerous": True, "value": False, "options": None}]}
        if path == "/central/healers":
            return {"registry_enabled": True, "healers": [{"kind": "central.daemon_dead", "mode": "SHADOW-FIRST", "destructive": True, "live_flag_on": False}]}
        return {}
    def post_json(self, path, body):
        self.posts.append((path, body))
        if not body.get("confirm") and ("generative" in str(body.get("key")) or "daemon" in str(body.get("name"))):
            return {"ok": False, "needs_confirm": True}
        return {"ok": True}


@pytest.mark.asyncio
async def test_governance_and_healing_render_and_write():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test() as pilot:
        app.show_tab("governance"); app.refresh_data()
        app.show_tab("healing"); app.refresh_data()
        assert app.active_tab == "healing"
        # non-dangerous governance write goes straight through
        app._set_governance("self_prompt", False)
        assert ("/central/governance/set", {"key": "self_prompt", "value": False, "confirm": False}) in c.posts
        # dangerous write needs confirm, then confirms
        app._set_governance("generative_autonomy", True)
        assert app._pending_write is not None
        app.action_confirm_yes()
        assert any(p == "/central/governance/set" and b.get("confirm") is True for p, b in c.posts)
        assert app._pending_write is None
