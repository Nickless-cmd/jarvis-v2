"""Kulde-start: daemons der sidst kørte FØR boot må ikke alarmere i vinduet."""
from datetime import UTC, datetime, timedelta

from core.services import background_attention as attention
from core.tools import daemon_alert_tools as daemon_alert

NOW = datetime(2026, 11, 28, 12, 57, 53, tzinfo=UTC)


class _FrozenDT(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz else NOW.replace(tzinfo=None)


def _run(monkeypatch, daemons, boot):
    monkeypatch.setattr("core.services.daemon_manager.get_all_daemon_states", lambda: daemons)
    monkeypatch.setattr(daemon_alert, "datetime", _FrozenDT)
    monkeypatch.setattr(daemon_alert, "_process_start_time", lambda: boot)
    monkeypatch.setattr(daemon_alert, "_load_alert_state", lambda: {"last_alerted": {}})
    monkeypatch.setattr(daemon_alert, "_save_alert_state", lambda _s: None)
    monkeypatch.setattr(attention, "report_background_outcome", lambda **k: {"status": "recorded"})
    return daemon_alert._exec_daemon_health_alert({"notify": False})


def _d(last_run: datetime, cadence=3):
    return [{
        "name": "event_trigger_shadow", "enabled": True,
        "effective_cadence_minutes": cadence,
        "last_run_at": last_run.isoformat(),
        "hours_since_last_run": (NOW - last_run).total_seconds() / 3600,
    }]


def test_last_run_before_boot_does_not_alert_in_window(monkeypatch):
    boot = NOW - timedelta(seconds=32)
    r = _run(monkeypatch, _d(NOW - timedelta(minutes=12, seconds=53)), boot)
    assert r["overdue_count"] == 0


def test_dead_after_window_still_alerts(monkeypatch):
    # boot 10 min ago (> 2x3 min window); last run before boot -> truly dead
    boot = NOW - timedelta(minutes=10)
    r = _run(monkeypatch, _d(NOW - timedelta(minutes=22)), boot)
    assert r["overdue_count"] == 1


def test_stale_run_after_boot_still_alerts_inside_window(monkeypatch):
    # ran after boot, then stalled: last_run_at >= boot -> never suppressed
    boot = NOW - timedelta(minutes=5)
    r = _run(monkeypatch, _d(NOW - timedelta(minutes=4)), boot)
    assert r["overdue_count"] == 0  # 4 min < 7.5 threshold, sanity
    r = _run(monkeypatch, _d(NOW - timedelta(minutes=8)), NOW - timedelta(minutes=9))
    assert r["overdue_count"] == 1


def test_unknown_boot_time_fails_towards_alerting(monkeypatch):
    r = _run(monkeypatch, _d(NOW - timedelta(minutes=30)), None)
    assert r["overdue_count"] == 1


def test_real_process_start_time_is_tz_aware_and_past():
    boot = daemon_alert._process_start_time()
    assert boot is not None and boot.tzinfo is not None
    assert boot <= datetime.now(UTC)
