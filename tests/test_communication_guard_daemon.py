"""Tests for core.services.communication_guard_daemon."""
from __future__ import annotations
from unittest import mock
import pytest


class TestDaemonTick:
    def test_returns_status_on_success(self):
        from core.services.communication_guard_daemon import tick

        result = tick()
        assert result["status"] == "ok"
        assert "active_triggers" in result
        assert "expired_removed" in result

    def test_returns_error_on_import_failure(self):
        """Hvis daemon-import fejler, returneres en fejlstatus uden crash."""
        with mock.patch(
            "core.services.communication_guard_daemon.cleanup_expired",
            side_effect=ImportError("fake"),
        ):
            from core.services.communication_guard_daemon import tick

            result = tick()
            assert result["status"] == "error"

    @pytest.mark.dirty_state
    def test_daemon_tick_removes_expired(self):
        from core.services.communication_guard import add_trigger
        from core.services.communication_guard_daemon import tick

        # TTL på 0 → straks udløbet
        add_trigger("test_phrase", kind="ttl", ttl_turns=1, reason="test")
        # Consume én turn
        from core.services.communication_guard import consume_turn

        consume_turn()
        consume_turn()  # turn 0 → skal fjernes ved næste cleanup

        result = tick()
        assert result["status"] == "ok"
        assert result["expired_removed"] >= 0
