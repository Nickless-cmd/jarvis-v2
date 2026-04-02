def test_mission_control_operations_route_returns_runtime_runs_approvals_and_sessions(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control

    monkeypatch.setattr(
        mission_control,
        "mc_runtime",
        lambda: {"provider_router": {}, "visible_execution": {}},
    )
    monkeypatch.setattr(
        mission_control,
        "mc_runs",
        lambda limit=20: {
            "active_run": None,
            "summary": {"recent_count": 0},
            "recent_runs": [],
        },
    )
    monkeypatch.setattr(
        mission_control,
        "mc_approvals",
        lambda limit=20: {
            "summary": {"request_count": 0},
            "requests": [],
            "recent_invocations": [],
        },
    )
    monkeypatch.setattr(
        mission_control,
        "list_chat_sessions",
        lambda: [{"id": "chat-1", "title": "Demo", "message_count": 2}],
    )

    payload = mission_control.mc_operations(limit=10)

    assert payload["runtime"] == {"provider_router": {}, "visible_execution": {}}
    assert payload["runs"]["recent_runs"] == []
    assert payload["approvals"]["requests"] == []
    assert payload["sessions"]["items"] == [
        {"id": "chat-1", "title": "Demo", "message_count": 2}
    ]
    assert payload["summary"]["session_count"] == 1
    assert payload["summary"]["approval_request_count"] == 0