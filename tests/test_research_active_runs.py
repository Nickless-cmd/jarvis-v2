from apps.api.jarvis_api.routes import chat


def test_active_runs_adds_research_snapshot(monkeypatch):
    class Settings:
        server_authoritative_runs = True

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: Settings())
    monkeypatch.setattr("core.services.run_event_log.live_run_ids", lambda: ["visible-1"])
    monkeypatch.setattr("core.services.run_event_log.session_for_run", lambda rid: "session-1")
    monkeypatch.setattr(
        "core.services.research_store.active_for_session",
        lambda sid: {"id": "research-1", "status": "researching", "tier": "orchestrated"},
    )
    result = chat.chat_active_runs()
    assert result["sessions"][0] == {
        "session_id": "session-1", "run_id": "visible-1", "status": "working",
        "research_run_id": "research-1", "research_status": "researching",
        "research_tier": "orchestrated",
    }
