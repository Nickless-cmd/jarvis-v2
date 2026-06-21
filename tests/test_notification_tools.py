"""Tests for notification preference-tools (notif-routing Phase 4)."""
import core.runtime.db as db
import core.runtime.db_core as db_core
import core.tools.notification_tools as nt


def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()


def test_set_then_get_preferences_tool(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    r = nt.exec_set_notification_preferences({"_user_id": "bjorn", "global": "desktop", "briefing": "mobile"})
    assert r["status"] == "ok"
    g = nt.exec_get_notification_preferences({"_user_id": "bjorn"})
    assert g["status"] == "ok"
    assert g["preferences"]["global"] == "desktop"
    assert g["preferences"]["briefing"] == "mobile"


def test_set_rejects_invalid_channel(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    r = nt.exec_set_notification_preferences({"_user_id": "bjorn", "global": "pigeon"})
    assert r["status"] == "error"


def test_no_user_context_errors(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    assert nt.exec_get_notification_preferences({})["status"] == "error"
