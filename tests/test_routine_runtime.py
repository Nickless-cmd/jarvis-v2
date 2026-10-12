def test_routine_runtime_public_api():
    from core.services.routine_runtime import start_routine_runtime, stop_routine_runtime

    assert callable(start_routine_runtime)
    assert callable(stop_routine_runtime)
