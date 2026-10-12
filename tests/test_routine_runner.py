def test_routine_runner_public_api():
    from core.services.routine_runner import RoutineRunner

    assert callable(RoutineRunner.run_once)
    assert callable(RoutineRunner.cancel)
