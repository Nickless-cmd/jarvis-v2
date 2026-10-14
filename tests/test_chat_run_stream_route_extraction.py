from apps.api.jarvis_api.app import create_app


def test_run_stream_routes_exist_once_after_extraction():
    app = create_app()
    paths = [route.path for route in app.routes]
    for expected in (
        "/chat/active-runs",
        "/chat/runs/{run_id}/subscribe",
        "/chat/sessions/{session_id}/live",
        "/chat/sessions/{session_id}/follow",
    ):
        assert paths.count(expected) == 1


def test_old_chat_module_reexports_stream_handlers():
    from apps.api.jarvis_api.routes import chat, chat_run_streams

    assert chat.chat_active_runs is chat_run_streams.chat_active_runs
    assert chat.chat_run_subscribe is chat_run_streams.chat_run_subscribe
    assert chat.chat_session_live is chat_run_streams.chat_session_live
    assert chat.chat_session_follow is chat_run_streams.chat_session_follow
