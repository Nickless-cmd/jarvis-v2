from core.services import background_attention as attention
from core.tools import daemon_alert_tools as daemon_alert


def test_daemon_watch_reports_to_inbox_even_when_push_is_disabled(monkeypatch):
    monkeypatch.setattr(
        "core.services.daemon_manager.get_all_daemon_states",
        lambda: [{
            "name": "mail", "enabled": True, "effective_cadence_minutes": 10,
            "hours_since_last_run": 2.0, "description": "mail watcher",
        }],
    )
    monkeypatch.setattr(daemon_alert, "_load_alert_state", lambda: {"last_alerted": {}})
    monkeypatch.setattr(daemon_alert, "_save_alert_state", lambda _state: None)
    reported = []
    monkeypatch.setattr(
        attention, "report_background_outcome",
        lambda **kwargs: reported.append(kwargs) or {"status": "recorded"},
    )

    result = daemon_alert._exec_daemon_health_alert({"notify": False})

    assert result["overdue_count"] == 1
    assert reported[0]["source_id"] == "mail"
    assert reported[0]["create_side_task"] is True
