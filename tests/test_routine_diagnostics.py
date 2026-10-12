def test_routine_diagnostic_render_has_no_exception_message():
    from core.services.routine_diagnostics import project_failure, render_projection

    projection = project_failure(RuntimeError("private message"), {})
    assert "private message" not in render_projection(projection)
