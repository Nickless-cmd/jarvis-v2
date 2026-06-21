"""Tests for recurring_tasks channel-felt (notif-routing Phase 3)."""
import pytest
import core.runtime.db as db
import core.runtime.db_core as db_core
import core.services.recurring_tasks as rt


def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()
    rt._ensure_table()


def test_channel_column_defaults_auto_and_set_channel(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="morgenbriefing", interval_minutes=1440)
    tid = t["task_id"]
    # default-kanal
    with db.connect() as c:
        ch = c.execute("SELECT channel FROM recurring_tasks WHERE task_id=?", (tid,)).fetchone()[0]
    assert ch == "auto"
    # sæt eksplicit kanal
    assert rt.set_channel(tid, "mobile") is True
    with db.connect() as c:
        ch = c.execute("SELECT channel FROM recurring_tasks WHERE task_id=?", (tid,)).fetchone()[0]
    assert ch == "mobile"


def test_set_channel_rejects_invalid(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        rt.set_channel("whatever", "smoke-signal")
