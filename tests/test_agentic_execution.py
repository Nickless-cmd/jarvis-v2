def test_agentic_execution_module_has_no_session_identifier():
    import inspect
    import core.services.agentic_execution as agentic_execution

    assert "session_id" not in inspect.getsource(agentic_execution)
