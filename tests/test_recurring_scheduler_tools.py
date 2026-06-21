"""Tests for set_recurring_channel-tool (notif-routing Phase 3)."""
import core.runtime.db as db
import core.runtime.db_core as db_core
import core.services.recurring_tasks as rt
from core.tools.recurring_scheduler_tools import _exec_set_recurring_channel


def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db(); rt._ensure_table()


def test_set_recurring_channel_tool_ok(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="brief", interval_minutes=60)
    tid = t["task_id"]
    r = _exec_set_recurring_channel({"task_id": tid, "channel": "desktop"})
    assert r["status"] == "ok" and r["channel"] == "desktop"


def test_set_recurring_channel_tool_validates(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    r = _exec_set_recurring_channel({"task_id": "x", "channel": "owl"})
    assert r["status"] == "error"
