"""Tests for heartbeat_runtime daemon wiring."""


def test_associative_recall_daemon_registered():
    """Verify associative_recall is registered in daemon_manager registry."""
    from core.services.daemon_manager import _REGISTRY

    assert "associative_recall" in _REGISTRY
    entry = _REGISTRY["associative_recall"]
    assert entry["module"] == "core.services.associative_recall"
    assert entry["default_cadence_minutes"] == 2
    assert entry["default_enabled"] is True


def test_associative_recall_tick_function_exists():
    """Verify tick_associative_recall is importable from associative_recall module."""
    from core.services.associative_recall import tick_associative_recall

    assert callable(tick_associative_recall)
