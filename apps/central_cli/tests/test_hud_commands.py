from __future__ import annotations

import pytest

from central_cli import datasource
from central_cli.hud import CentralHud


class FakeClient:
    """Client med anomalier hvis sample indeholder '[...]' (markup-injektionsværn)
    og som optager alle post/get-kald (kommando-eksekvering)."""

    def __init__(self):
        self.posts = []
        self.gets = []

    def get_json(self, path, params=None):
        self.gets.append((path, params))
        if path == "/central/realtime":
            return {"status": "yellow", "coverage": {"nerves": 5, "clusters": 2},
                    "open_breakers": [], "clusters": [], "incidents": [], "feed": []}
        if path == "/central/diagnostics":
            return {"incidents": [], "root_causes": [], "degrading": [], "anomalies": [
                {"importance": "medium", "category": "log:Error", "source": "log",
                 "count": 8, "signature": "log:Error|Task <Task pending [cb=Task.wakeup()]>",
                 "sample": "Task was destroyed [cb=[Task.task_wakeup()]] running at x.py:1",
                 "location": "asyncio/base_events.py:1785",
                 "first_seen": "2026-06-30T13:00:00+00:00", "last_seen": "2026-07-05T16:00:00+00:00"},
                {"importance": "low", "category": "log:Warn", "source": "log", "count": 2,
                 "signature": "warn|something", "sample": "a warning", "location": "y.py:2",
                 "first_seen": "2026-07-01T00:00:00+00:00", "last_seen": "2026-07-05T00:00:00+00:00"},
            ]}
        return {}

    def post_json(self, path, body):
        self.posts.append((path, body))
        return {"ok": True}


# ---- datasource.anomalies -------------------------------------------------

def test_anomalies_shape_and_sort():
    rows = datasource.anomalies(FakeClient())
    assert len(rows) == 2
    # medium sorteres før low
    assert rows[0]["importance"] == "medium"
    assert rows[0]["count"] == 8
    assert set(rows[0]) >= {"importance", "category", "count", "signature", "sample",
                            "location", "first", "last", "source"}


def test_anomalies_self_safe_on_error():
    class Boom:
        def get_json(self, *a, **k):
            raise RuntimeError("nej")
    assert datasource.anomalies(Boom()) == []


# ---- HUD anomalies-fane + markup-injektionsværn ---------------------------

@pytest.mark.asyncio
async def test_anomalies_tab_renders_with_brackets_no_crash():
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test(size=(150, 40)):
        app.show_tab("anomalies")
        table = app.query_one("#nerve-table")
        assert table.row_count == 2          # brackets i sample crasher IKKE renderingen


# ---- kommandolinje --------------------------------------------------------

@pytest.mark.asyncio
async def test_command_toggle_posts_to_endpoint():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test(size=(150, 40)):
        app._run_command("toggle some_nerve off")
        assert ("/central/nerve/some_nerve/toggle", {"enabled": False}) in c.posts


@pytest.mark.asyncio
async def test_command_get_calls_client():
    c = FakeClient()
    app = CentralHud(client=c, live=False)
    async with app.run_test(size=(150, 40)):
        c.gets.clear()
        app._run_command("status")
        assert any(p == "/central/realtime" for p, _ in c.gets)


@pytest.mark.asyncio
async def test_command_mode_toggles_input_visibility():
    app = CentralHud(client=FakeClient(), live=False)
    async with app.run_test(size=(150, 40)):
        app.action_command_mode()
        assert app._cmd_mode is True
        app._exit_command_mode()
        assert app._cmd_mode is False
