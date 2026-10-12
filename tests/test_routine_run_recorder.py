def test_routine_run_recorder_has_no_session_destination():
    from core.services.routine_run_recorder import RoutineRunRecorder

    assert not hasattr(RoutineRunRecorder(), "session_id")
