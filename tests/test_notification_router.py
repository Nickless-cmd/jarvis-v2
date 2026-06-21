"""Tests for notification_router (Phase 2): preferences, quiet hours, routing."""
import pytest

import core.runtime.db as db
import core.runtime.db_core as db_core
import core.services.notification_router as nr


def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()


# ── Pure logic ──────────────────────────────────────────────────────────────
def test_resolve_channel_priority():
    prefs = {"global": "desktop", "team_invite": "mobile", "briefing": None}
    assert nr.resolve_channel(prefs, "team_invite") == "mobile"   # type override vinder
    assert nr.resolve_channel(prefs, "briefing") == "desktop"     # falder til global
    assert nr.resolve_channel({"global": "auto"}, "reminder") == "auto"


def test_is_quiet_hours_normal_and_wrap():
    p = {"quiet_start": "23:00", "quiet_end": "07:00"}  # wrapper over midnat
    assert nr.is_quiet_hours(p, "23:30") is True
    assert nr.is_quiet_hours(p, "03:00") is True
    assert nr.is_quiet_hours(p, "12:00") is False
    p2 = {"quiet_start": "09:00", "quiet_end": "17:00"}  # samme dag
    assert nr.is_quiet_hours(p2, "12:00") is True
    assert nr.is_quiet_hours(p2, "20:00") is False
    assert nr.is_quiet_hours({"quiet_start": "08:00", "quiet_end": "08:00"}, "08:00") is False


# ── CRUD ──────────────────────────────────────────────────────────────────────
def test_preferences_roundtrip(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    assert nr.get_preferences("u1")["global"] == "auto"  # default
    nr.set_preferences("u1", **{"global": "desktop", "team_invite": "mobile", "quiet_start": "22:00"})
    p = nr.get_preferences("u1")
    assert p["global"] == "desktop"
    assert p["team_invite"] == "mobile"
    assert p["quiet_start"] == "22:00"


def test_set_preferences_rejects_invalid_channel(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        nr.set_preferences("u1", **{"global": "carrier-pigeon"})


# ── Routing ─────────────────────────────────────────────────────────────────
def test_route_queues_during_quiet_hours(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    nr.set_preferences("u1", **{"quiet_start": "00:00", "quiet_end": "23:59"})  # ~altid stille
    delivered = []
    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: delivered.append(a) or True)
    res = nr.route_proactive_notification("u1", "briefing", {"preview": "morgen"})
    assert res["channel"] == "queued"
    assert delivered == []  # IKKE leveret — sat i kø


def test_route_critical_bypasses_quiet_hours(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    nr.set_preferences("u1", **{"quiet_start": "00:00", "quiet_end": "23:59"})
    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: True)
    res = nr.route_proactive_notification("u1", "reminder", {"preview": "BRAND"}, importance="critical")
    assert res["delivered"] is True
    assert res["channel"] != "queued"


def test_route_delivers_to_resolved_channel(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    # quiet_start == quiet_end → ingen quiet hours (deterministisk, ikke ur-afhængig)
    nr.set_preferences("u1", **{"global": "desktop", "quiet_start": "00:00", "quiet_end": "00:00"})
    calls = []
    monkeypatch.setattr(nr, "_deliver_to_channel",
                        lambda uid, ch, p, t: calls.append((uid, ch)) or True)
    res = nr.route_proactive_notification("u1", "briefing", {"preview": "x"})
    assert res["delivered"] is True
    assert res["channel"] == "desktop"
    assert calls and calls[0][1] == "desktop"
