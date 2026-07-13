from core.services.dispatch_status import DispatchStatus, is_terminal, is_failure


def test_status_values():
    assert DispatchStatus.COMPLETED == "completed"
    assert set(DispatchStatus.all()) == {"completed", "failed", "timeout", "blocked", "needs_context", "concerns"}


def test_failure_classification():
    assert is_failure("failed") and is_failure("timeout") and is_failure("blocked")
    assert not is_failure("completed")
    assert not is_failure("concerns")  # success-with-doubt, NOT a failure


def test_terminal():
    assert is_terminal("completed") and is_terminal("failed")
    assert is_terminal("timeout") and is_terminal("blocked")
