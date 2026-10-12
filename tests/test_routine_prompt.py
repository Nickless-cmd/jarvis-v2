def test_routine_prompt_is_session_neutral():
    import inspect
    import core.services.routine_prompt as routine_prompt

    source = inspect.getsource(routine_prompt)
    assert "chat_session" not in source
    assert "session_id" not in source
