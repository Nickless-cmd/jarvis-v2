"""Tests for set_recurring_channel-tool (notif-routing Phase 3)."""
import core.runtime.db as db
import core.runtime.db_core as db_core
import core.services.recurring_tasks as rt
from core.tools.recurring_scheduler_tools import (
    _exec_set_recurring_channel,
    _exec_set_recurring_weekdays,
    _exec_schedule_recurring,
)


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


# ── Ugedage ───────────────────────────────────────────────────────────────────
# Bjoern 28/9-2026: «begraens medicin-paamindelserne til hverdage».


def test_set_recurring_weekdays_tool_ok(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="medicin", interval_minutes=1440)
    tid = t["task_id"]
    r = _exec_set_recurring_weekdays({"task_id": tid, "weekdays": "man-fre"})
    assert r["status"] == "ok"
    assert r["weekdays"] == "1,2,3,4,5"
    with db.connect() as c:
        ud = c.execute(
            "SELECT weekdays FROM recurring_tasks WHERE task_id=?", (tid,)
        ).fetchone()[0]
    assert ud == "1,2,3,4,5"


def test_set_recurring_weekdays_tool_kaster_paa_tastefejl(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="medicin", interval_minutes=1440)
    r = _exec_set_recurring_weekdays(
        {"task_id": t["task_id"], "weekdays": "torsdagsagtigt"}
    )
    assert r["status"] == "error"


def test_schedule_recurring_videresender_ugedage(monkeypatch):
    """Ugedage skal hele vejen igennem VAERKTOEJET, ikke kun i servicen —
    ellers kan Jarvis ikke saette dem naar han opretter en opgave."""
    fanget: dict = {}

    def _fang(**kw):
        fanget.update(kw)
        return {
            "task_id": "rec-1", "focus": kw["focus"],
            "next_fire_at": "2026-09-29T04:15:00+00:00", "weekdays": "1,2,3,4,5",
        }

    monkeypatch.setattr(rt, "create_recurring_task", _fang)
    r = _exec_schedule_recurring({"focus": "medicin", "interval": 1, "unit": "days",
                                  "weekdays": "man-fre"})
    assert fanget.get("weekdays") == "man-fre"
    assert r["status"] == "ok"
    assert r["weekdays"] == "1,2,3,4,5"
    assert "1,2,3,4,5" in r["text"]
