from __future__ import annotations

import pytest

from central_cli import datasource as ds
from central_cli.hud import CentralHud, _PANEL_TABS, _TABLE_TABS


_REALTIME = {
    "status": "green", "coverage": {}, "incidents": [],
    "open_breakers": [], "clusters": [], "feed": [],
}

_AGENTS = {
    "agents": [
        {"agent_id": "a1", "role": "researcher", "status": "running",
         "tokens_burned": 1200},
        {"agent_id": "a2", "role": "critic", "status": "idle",
         "tokens_burned": 0},
        {"agent_id": "a3", "role": "planner", "status": "done",
         "tokens_burned": 5400},
    ],
    "count": 3,
}

_ROSTER = {
    "roster": [
        {"model_key": "anthropic/claude", "provider": "anthropic",
         "model": "claude", "role": "visible", "status": "active",
         "last_run_at": "2026-07-16T10:00:00+00:00",
         "tokens_in": 100, "tokens_out": 200, "cost_usd": 0.05,
         "current_activity": "svarer i chat", "tool_calls": 3},
        {"model_key": "ollama/qwen", "provider": "ollama", "model": "qwen",
         "role": "cheap", "status": "idle", "last_run_at": "",
         "tokens_in": 10, "tokens_out": 5, "cost_usd": 0.0,
         "current_activity": "", "tool_calls": 0},
        {"model_key": "groq/llama", "provider": "groq", "model": "llama",
         "role": "agent", "status": "inactive", "last_run_at": "",
         "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
         "current_activity": "", "tool_calls": 0},
    ],
}

_SELF = {
    "self": {
        "living_executive": {
            "liveness": True,
            "mode": "attentive",
            "summary": {
                "trace_count": 42,
                "recent_count": 5,
                "listener_running": True,
                "last_choice": "observe",
                "last_action": "noted a drift",
                "last_status": "ok",
            },
        },
        "self_model": {
            "liveness": True,
            "summary": {
                "layer_count": 4,
                "sections": ["identity", "capabilities", "history"],
                "built_at": "2026-07-05T14:00:00+00:00",
            },
        },
        "world_model": {
            "liveness": False,
            "summary": {"active_count": 7},
        },
    },
    "ts": 123,
}


class FakeClient:
    """Serves the two live endpoint shapes (+ realtime for HUD boot)."""

    def __init__(self, agents=None, slf=None):
        self._agents = agents if agents is not None else _AGENTS
        self._self = slf if slf is not None else _SELF

    def get_json(self, path, params=None):
        if "realtime" in path:
            return dict(_REALTIME)
        if path == "/central/agents":
            return self._agents
        if path == "/central/self":
            return self._self
        return {}

    def post_json(self, path, body):
        return {"ok": True}


# -- datasource --------------------------------------------------------------
def test_datasource_agents_returns_list():
    rows = ds.agents(FakeClient())
    assert isinstance(rows, list)
    assert len(rows) == 3
    by = {r["agent_id"]: r for r in rows}
    assert by["a1"]["role"] == "researcher"
    assert by["a1"]["status"] == "running"
    assert by["a3"]["tokens_burned"] == 5400


def test_datasource_agents_self_safe_on_error():
    class Boom:
        def get_json(self, p, params=None):
            raise RuntimeError("nej")
    assert ds.agents(Boom()) == []


def test_datasource_self_snapshot_returns_self_dict():
    slf = ds.self_snapshot(FakeClient())
    assert isinstance(slf, dict)
    assert slf["living_executive"]["mode"] == "attentive"
    assert slf["self_model"]["summary"]["layer_count"] == 4
    assert slf["world_model"]["summary"]["active_count"] == 7


def test_datasource_self_snapshot_self_safe_on_error():
    class Boom:
        def get_json(self, p, params=None):
            raise RuntimeError("nej")
    assert ds.self_snapshot(Boom()) == {}


# -- tab-set membership ------------------------------------------------------
def test_agents_is_table_tab_and_mind_is_panel_tab():
    assert "agents" in _TABLE_TABS
    assert "mind" in _PANEL_TABS


# -- HUD render --------------------------------------------------------------
@pytest.mark.asyncio
async def test_agents_tab_populates_table_rows():
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test(size=(150, 40)):
        app.show_tab("agents")
        assert app.active_tab == "agents"
        from textual.widgets import DataTable
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 3
        # selecting a row renders the agent detail in the side panel
        detail = str(app.query_one("#hud-detail").render())
        assert "researcher" in detail or "a1" in detail


@pytest.mark.asyncio
async def test_agents_tab_renders_model_roster_with_greyed_inactive():
    """C1: the roster renders one fixed row per model; INACTIVE rows are greyed,
    the ACTIVE row carries its ● marker + activity text."""
    from central_cli.hud_theme import DIM, FGDIM
    from rich.text import Text
    from textual.widgets import DataTable

    app = CentralHud(client=FakeClient(agents=_ROSTER), live=False)
    async with app.run_test(size=(160, 40)):
        app.show_tab("agents")
        table = app.query_one("#nerve-table", DataTable)
        assert table.row_count == 3

        labels = [str(table.get_row_at(i)[0]) for i in range(3)]
        assert any("claude" in l for l in labels)
        assert any("qwen" in l for l in labels)
        assert any("groq/llama" in l for l in labels)

        # INACTIVE row (groq/llama): model cell uses the grey style.
        inact = next(i for i in range(3)
                     if "groq" in str(table.get_row_at(i)[0]))
        cell = table.get_row_at(inact)[0]
        assert isinstance(cell, Text)
        assert cell.style in (DIM, FGDIM)
        # status cell of the inactive row is greyed too
        assert table.get_row_at(inact)[2].style in (DIM, FGDIM)

        # ACTIVE row (claude): ● marker in status + activity text present.
        act = next(i for i in range(3)
                   if "claude" in str(table.get_row_at(i)[0]))
        assert "●" in str(table.get_row_at(act)[2])
        assert "svarer" in str(table.get_row_at(act)[3])

        # detail panel for the active model shows model_key + cost fields
        app._render_agent_detail(act)
        detail = str(app.query_one("#hud-detail").render())
        assert "anthropic/claude" in detail
        assert "cost" in detail


@pytest.mark.asyncio
async def test_mind_tab_renders_self_panel():
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test(size=(150, 40)):
        app.show_tab("mind")
        assert app.active_tab == "mind"
        assert app.query_one("#hud-panel").display is True
        rendered = str(app.query_one("#hud-panel").render())
        assert "MIND & SELF" in rendered
        assert "living_executive" in rendered or "attentive" in rendered
        assert "world_model" in rendered


@pytest.mark.asyncio
async def test_mind_tab_renders_phase_c_agentur():
    """Fase C: de 4 private agentur-lag renderes i AGENTUR-undersektionen
    uden crash — light (liveness + tællere), aldrig råt indhold."""
    slf = {
        "self": {
            "living_executive": {"liveness": True, "mode": "attentive",
                                 "summary": {"trace_count": 1}},
            "self_model": {"liveness": True, "summary": {"layer_count": 2}},
            "world_model": {"liveness": False, "summary": {"active_count": 1}},
            "open_loops": {"liveness": True,
                           "summary": {"open_loops_count": 3, "count": 3}},
            "runtime_awareness": {"liveness": True,
                                  "summary": {"signals_count": 2, "score": 0.5}},
            "runtime_self_knowledge": {"liveness": False,
                                       "summary": {"facts_count": 4}},
            "counterfactual": {"liveness": True,
                               "summary": {"predictions_count": 5, "horizon": 3}},
        },
        "ts": 1,
    }
    app = CentralHud(client=FakeClient(slf=slf), live=False)
    async with app.run_test(size=(150, 40)):
        app.show_tab("mind")
        rendered = str(app.query_one("#hud-panel").render())
        assert "AGENTUR" in rendered
        for name in ("open_loops", "runtime_awareness",
                     "runtime_self_knowledge", "counterfactual"):
            assert name in rendered, f"phase-C surface {name} not rendered"


@pytest.mark.asyncio
async def test_mind_tab_no_agentur_when_absent():
    """Uden Fase C-nøgler vises AGENTUR-sektionen ikke (self-safe skip)."""
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test(size=(150, 40)):
        app.show_tab("mind")
        rendered = str(app.query_one("#hud-panel").render())
        assert "MIND & SELF" in rendered
        assert "AGENTUR" not in rendered


@pytest.mark.asyncio
async def test_agents_and_mind_markup_injection_safe():
    """A field containing '[' must not crash the render."""
    agents = {
        "agents": [{"agent_id": "a[1]", "role": "x[y]", "status": "run[ning]",
                    "tokens_burned": 3}],
        "count": 1,
    }
    slf = {
        "self": {
            "living_executive": {"liveness": True, "mode": "at[tent]ive",
                                 "summary": {"trace_count": 1,
                                             "last_choice": "ob[serve]",
                                             "last_action": "x[y]"}},
            "self_model": {"liveness": True,
                           "summary": {"layer_count": 2,
                                       "sections": ["a[b]"]}},
            "world_model": {"liveness": False, "summary": {"active_count": 1}},
        },
        "ts": 1,
    }
    app = CentralHud(client=FakeClient(agents=agents, slf=slf), live=False)
    async with app.run_test(size=(150, 40)):
        app.show_tab("agents")
        assert app.query_one("#nerve-table").row_count == 1
        app.show_tab("mind")
        rendered = str(app.query_one("#hud-panel").render())
        assert "MIND & SELF" in rendered
